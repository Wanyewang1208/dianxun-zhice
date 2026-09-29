"""V3 rerun of the frozen V2 capacity-proxy protocol; V2 files remain immutable."""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .ev_experiment import FEATURES, split_for


def validate_data(data):
    required = FEATURES + ['vehicle', 'split', 'start_local_unspecified', 'proxy_capacity_ah']
    if not set(required) <= set(data):
        raise ValueError('Missing required columns')
    if data.empty or data[required].isna().any().any():
        raise ValueError('Empty data or missing values')
    if set(data.vehicle) != set(range(1, 21)):
        raise ValueError('Expected vehicles 1..20')
    if not np.isfinite(data[FEATURES + ['proxy_capacity_ah']]).all().all():
        raise ValueError('Nonfinite input')
    if not data.proxy_capacity_ah.between(0, 250, inclusive='right').all():
        raise ValueError('Proxy outside original inclusion bounds')
    if data.duplicated(['vehicle', 'start_local_unspecified']).any():
        raise ValueError('Duplicate vehicle/session')
    if not data.split.eq(data.vehicle.map(split_for)).all():
        raise ValueError('Vehicle split mismatch')


def training_folds(data):
    train = data.loc[data.split == 'train']
    for fit, holdout in GroupKFold(n_splits=5).split(train, groups=train.vehicle):
        yield train.iloc[fit], train.iloc[holdout]


def scores(y, pred, vehicles):
    y, pred = np.asarray(y), np.asarray(pred)
    per_vehicle = pd.Series(np.abs(y - pred)).groupby(np.asarray(vehicles)).mean()
    return {'n': len(y), 'vehicles': len(per_vehicle),
            'mae_ah': float(mean_absolute_error(y, pred)),
            'rmse_ah': float(np.sqrt(mean_squared_error(y, pred))),
            'r2': float(r2_score(y, pred)),
            'vehicle_macro_mae_ah': float(per_vehicle.mean())}


def cluster_interval(vehicle_values):
    values = np.asarray(vehicle_values, dtype=float)
    draws = np.random.default_rng(2026).choice(values, (2000, len(values)), replace=True).mean(axis=1)
    return tuple(float(x) for x in np.quantile(draws, [.025, .975]))


def stress_input(train, inputs, kind, level):
    result = inputs.copy()
    rng = np.random.default_rng(2026)
    if kind == 'noise':
        result += rng.normal(size=result.shape) * train.std(ddof=0).to_numpy() * level
    elif kind == 'missing':
        result = result.mask(rng.random(result.shape) < level).fillna(train.median())
    else:
        raise ValueError('Unknown stress type')
    return result


def model_for(name, seed=42):
    if name == 'train_mean':
        return DummyRegressor(strategy='mean')
    if name == 'ridge':
        return make_pipeline(StandardScaler(), Ridge(alpha=10))
    if name == 'random_forest':
        return RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=seed, n_jobs=2)
    raise ValueError(name)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(source, output, models_dir):
    data = pd.read_csv(source)
    if 'segment_id' in data and 'start_local_unspecified' not in data:
        # Compatibility key only: anonymous segment IDs are not timestamps.
        data['start_local_unspecified'] = data.segment_id
        data['vehicle'] = data.vehicle.str.removeprefix('vehicle_').astype(int)
    if 'segment_id' not in data:
        data['segment_id'] = ['vehicle_%03d_session_%05d' % (v, n)
            for v, n in zip(data.vehicle, data.groupby('vehicle').cumcount()+1)]
    if data.segment_id.isna().any() or data.segment_id.duplicated().any():
        raise ValueError('Missing or duplicate segment IDs')
    validate_data(data)
    output.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    train = data.loc[data.split == 'train']
    metrics, predictions, cv_metrics, fold_manifest, cv_predictions = [], [], [], [], []
    primary = {}

    def evaluate(model, name, columns, seed=42, stress=None):
        for split in ['validation', 'test']:
            part = data.loc[data.split == split]
            x = part[columns]
            if stress:
                x = stress_input(train[columns], x, *stress)
            pred = model.predict(x)
            metrics.append(dict(experiment=name, split=split, seed=seed,
                                **scores(part.proxy_capacity_ah, pred, part.vehicle)))
            records = part[['vehicle', 'split', 'segment_id', 'proxy_capacity_ah']].copy()
            records['experiment'], records['seed'], records['predicted_ah'] = name, seed, pred
            predictions.append(records)

    for name in ['train_mean', 'ridge', 'random_forest']:
        model = model_for(name)
        model.fit(train[FEATURES], train.proxy_capacity_ah)
        primary[name] = model
        evaluate(model, name, FEATURES)
        joblib.dump(model, models_dir / (name + '.joblib'), compress=3)
        # Verify serialized models reproduce the evaluated predictions.
        probe = data.loc[data.split == 'test', FEATURES]
        np.testing.assert_allclose(joblib.load(models_dir / (name + '.joblib')).predict(probe),
                                   model.predict(probe), rtol=0, atol=1e-10)
        print('baseline:', name, flush=True)

    for seed in [17, 2026]:
        model = model_for('random_forest', seed)
        model.fit(train[FEATURES], train.proxy_capacity_ah)
        evaluate(model, 'rf_seed', FEATURES, seed=seed)
        print('seed:', seed, flush=True)

    removed = {'without_soc_current': ['soc_start', 'current_mean'],
               'without_temperature': ['tmax_mean', 'temperature_rise'],
               'without_cell_gap': ['cell_gap_mean', 'cell_gap_max']}
    for name, excluded in removed.items():
        columns = [f for f in FEATURES if f not in excluded]
        model = model_for('random_forest')
        model.fit(train[columns], train.proxy_capacity_ah)
        evaluate(model, name, columns)
        print('ablation:', name, flush=True)

    for name, kind, level in [('noise_1pct', 'noise', .01), ('noise_5pct', 'noise', .05),
                              ('missing_10pct', 'missing', .1)]:
        evaluate(primary['random_forest'], name, FEATURES, stress=(kind, level))

    for fold, (fit, holdout) in enumerate(training_folds(data), 1):
        fold_manifest.append({'fold': fold, 'train_vehicles': sorted(fit.vehicle.unique().tolist()),
                              'holdout_vehicles': sorted(holdout.vehicle.unique().tolist())})
        for name in ['train_mean', 'ridge', 'random_forest']:
            model = model_for(name)
            model.fit(fit[FEATURES], fit.proxy_capacity_ah)
            pred = model.predict(holdout[FEATURES])
            cv_records = holdout[['vehicle','segment_id','proxy_capacity_ah']].copy()
            cv_records['fold'], cv_records['model'], cv_records['predicted_ah'] = fold, name, pred
            cv_predictions.append(cv_records)
            cv_metrics.append(dict(fold=fold, model=name,
                                   **scores(holdout.proxy_capacity_ah, pred, holdout.vehicle)))
        print('training-only CV fold:', fold, flush=True)

    pd.DataFrame(metrics).to_csv(output / 'metrics.csv', index=False)
    prediction_frame = pd.concat(predictions, ignore_index=True)
    prediction_frame.to_csv(output / 'predictions.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    prediction_frame['absolute_error'] = abs(prediction_frame.proxy_capacity_ah - prediction_frame.predicted_ah)
    vehicle_errors = prediction_frame.groupby(['experiment', 'seed', 'split', 'vehicle']).absolute_error.agg(['mean', 'size']).reset_index()
    vehicle_errors.rename(columns={'mean': 'mae_ah', 'size': 'sessions'}, inplace=True)
    vehicle_errors.to_csv(output / 'per_vehicle.csv', index=False)
    pd.DataFrame(cv_metrics).to_csv(output / 'group_cv.csv', index=False)
    pd.concat(cv_predictions).to_csv(output / 'group_cv_predictions.csv.gz', index=False, compression={'method':'gzip','mtime':0})
    joblib.dump(primary['ridge'].steps[0][1], models_dir / 'feature_processor.joblib', compress=3)
    intervals = []
    test = vehicle_errors.loc[(vehicle_errors.split == 'test') & (vehicle_errors.seed == 42)]
    base = test.loc[test.experiment == 'train_mean'].set_index('vehicle').mae_ah
    for name in ['train_mean', 'ridge', 'random_forest']:
        values = test.loc[test.experiment == name].set_index('vehicle').mae_ah
        low, high = cluster_interval(values)
        differences = base - values
        dlo, dhi = cluster_interval(differences)
        intervals.append(dict(model=name, vehicle_macro_mae_ah=float(values.mean()),
                              exploratory_95pct_low=low, exploratory_95pct_high=high,
                              paired_macro_improvement_ah=float(differences.mean()),
                              paired_improvement_low=dlo, paired_improvement_high=dhi))
    (output / 'cluster_intervals.json').write_text(json.dumps(intervals, indent=2), encoding='utf-8')
    (output / 'folds.json').write_text(json.dumps(fold_manifest, indent=2), encoding='utf-8')
    code_files = [Path(__file__), Path(__file__).with_name('ev_experiment.py'), Path(__file__).with_name('V3_PROTOCOL.md')]
    model_files = list(models_dir.glob('*.joblib'))
    manifest = {
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'label': 'derived capacity proxy in Ah; not independently measured SOH',
        'input_file': 're-extracted session features; public anonymous equivalents in data/v3/session_features.csv', 'input_sha256': sha256(source),
        'code_sha256': {p.name: sha256(p) for p in code_files},
        'models_sha256': {p.name: sha256(p) for p in model_files},
        'raw_extraction_rerun': True,
        'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                        'scipy': scipy.__version__, 'scikit_learn': sklearn.__version__, 'joblib': joblib.__version__},
        'random_seeds': [17, 42, 2026], 'bootstrap_seed': 2026,
        'split_sessions': data.groupby('split').size().to_dict(),
        'limitations': ['4 test vehicles only', 'single source/vehicle model', 'retrospective supplementary analysis',
                        'feature-level synthetic perturbations', 'proxy label shares electrical signals with inputs']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(pd.DataFrame(metrics).to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('research/public_battery/results/v3'))
    parser.add_argument('--models-dir', type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output, args.models_dir)
