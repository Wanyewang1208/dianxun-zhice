"""Fixed V4 retrospective extensions; all V3 evidence remains read-only."""
import argparse
import json
import platform
import subprocess
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits
from .ev_experiment import FEATURES
from .validation_v3 import model_for, scores, stress_input, sha256

METHODS = ['train_mean', 'train_median', 'ridge', 'random_forest', 'hist_gradient_boosting']
THRESHOLDS = [0, 1, 2, 3, 5, 10]
SEEDS = [17, 42, 2026]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def error_metrics(y, p, vehicles):
    y, p = np.asarray(y, float), np.asarray(p, float)
    if not len(y) or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('Metrics require finite nonempty pairs')
    result = scores(y, p, vehicles)
    e = p - y
    result.update(bias_ah=float(e.mean()), median_ae_ah=float(np.median(abs(e))),
                  p90_ae_ah=float(np.quantile(abs(e), .9)), p95_ae_ah=float(np.quantile(abs(e), .95)),
                  max_ae_ah=float(abs(e).max()))
    return result


def bin_edges(train_values):
    values = np.unique(np.quantile(np.asarray(train_values), [1/3, 2/3]))
    return [-np.inf, *values.tolist(), np.inf]


def assign_bins(values, edges):
    return pd.cut(values, edges, labels=False, include_lowest=True)


def nested_vehicle_sets(vehicles, sizes, seeds):
    result = []
    for seed in seeds:
        ordered = np.random.default_rng(seed).permutation(sorted(vehicles)).tolist()
        for n in sizes:
            result.append({'repeat_seed': seed, 'training_vehicle_count': n, 'vehicles': sorted(ordered[:n])})
    return result


def choose_quality_gate(validation_table):
    if set(validation_table['split']) != {'validation'}:
        raise ValueError('Gate selection must use validation only')
    eligible = validation_table[(validation_table.coverage >= .8) & (validation_table.minimum_vehicle_coverage >= .6)]
    if eligible.empty:
        return 0
    return int(eligible.sort_values(['vehicle_macro_mae_ah', 'threshold']).iloc[0].threshold)


def check_windows(data):
    if set(data.window_s) != {120, 300, 600} or data.duplicated(['window_s', 'segment_id']).any():
        raise ValueError('Invalid window or duplicate record')
    ref = data[data.window_s == 600].set_index('segment_id').proxy_capacity_ah.sort_index()
    for _, g in data.groupby('window_s'):
        other = g.set_index('segment_id').proxy_capacity_ah.sort_index()
        if not ref.index.equals(other.index) or not np.allclose(ref, other, atol=1e-9, rtol=0):
            raise ValueError('Window cohorts/targets differ')


def estimator(name, seed=42):
    if name == 'train_median':
        return DummyRegressor(strategy='median')
    if name == 'hist_gradient_boosting':
        return HistGradientBoostingRegressor(max_iter=200, learning_rate=.05, max_leaf_nodes=15,
            min_samples_leaf=20, l2_regularization=1., early_stopping=False, random_state=seed)
    return model_for(name, seed)


def run(source, out):
    out = Path(out)
    dirs = {k: out / k for k in ['02_metrics', '03_predictions', '04_models', '06_verification']}
    for p in dirs.values(): p.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(source)
    check_windows(data)
    if data.groupby('window_s').size().tolist() != [29697] * 3:
        raise ValueError('Unexpected cohort size')
    for split, expected in [('train', set(range(1, 15))), ('validation', {15, 16}), ('test', {17, 18, 19, 20})]:
        ids = set(data.loc[data.split == split, 'vehicle'].str.removeprefix('vehicle_').astype(int))
        if ids != expected: raise ValueError('Changed vehicle split')
    if data[FEATURES].isna().any().any(): raise ValueError('Missing model features')
    metrics, predictions, cv_rows, cv_predictions, fold_log = [], [], [], [], []
    fitted, fit_log = {}, []

    def record(part, pred, group, experiment, window, seed=42, **extras):
        rec = part[['segment_id', 'vehicle', 'split', 'proxy_capacity_ah']].copy()
        rec['group'], rec['experiment'], rec['window_s'], rec['seed'] = group, experiment, window, seed
        rec['predicted_ah'] = np.asarray(pred)
        for k, v in extras.items(): rec[k] = v
        predictions.append(rec)
        metrics.append(dict(group=group, experiment=experiment, window_s=window, seed=seed,
                            split=part.split.iloc[0], **extras,
                            **error_metrics(part.proxy_capacity_ah, pred, part.vehicle)))

    # Fit all candidates and run grouped CV without any test-based selection.
    for w in [120, 300, 600]:
        subset = data[data.window_s == w]
        train = subset[subset.split == 'train']
        for name in METHODS:
            model = estimator(name).fit(train[FEATURES], train.proxy_capacity_ah)
            fitted[w, name] = model
            path = dirs['04_models'] / f'{name}_{w}s.joblib'
            joblib.dump({'model': model, 'features': FEATURES, 'window_s': w,
                         'training_vehicles': sorted(train.vehicle.unique())}, path, compress=3)
            probe = train[FEATURES].iloc[:100]
            np.testing.assert_allclose(joblib.load(path)['model'].predict(probe), model.predict(probe), atol=1e-10, rtol=0)
            print('fit', w, name, flush=True)
        for fold, (fitidx, validx) in enumerate(GroupKFold(5).split(train, groups=train.vehicle), 1):
            a, b = train.iloc[fitidx], train.iloc[validx]
            fold_log.append({'window_s': w, 'fold': fold, 'fit_vehicles': sorted(a.vehicle.unique()), 'holdout_vehicles': sorted(b.vehicle.unique())})
            for name in METHODS:
                model = estimator(name).fit(a[FEATURES], a.proxy_capacity_ah)
                pred = model.predict(b[FEATURES])
                cv_rows.append(dict(window_s=w, fold=fold, experiment=name, **error_metrics(b.proxy_capacity_ah, pred, b.vehicle)))
                r = b[['segment_id', 'vehicle', 'proxy_capacity_ah']].copy()
                r['window_s'], r['fold'], r['experiment'], r['predicted_ah'] = w, fold, name, pred
                cv_predictions.append(r)
            print('group CV', w, fold, flush=True)
    pd.DataFrame(cv_rows).to_csv(dirs['02_metrics'] / 'group_cv.csv', index=False)
    pd.concat(cv_predictions, ignore_index=True).to_csv(dirs['03_predictions'] / 'group_cv.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    write_json(dirs['06_verification'] / 'folds.json', fold_log)

    for w in [120, 300, 600]:
        subset = data[data.window_s == w]
        for split in ['validation', 'test']:
            part = subset[subset.split == split]
            for name in METHODS:
                record(part, fitted[w, name].predict(part[FEATURES]), 'primary', name, w)
            valid = part[np.isfinite(part.formula_capacity_ah)]
            record(valid, valid.formula_capacity_ah, 'formula', 'prefix_formula', w)
    six = data[data.window_s == 600]
    train, test, val = [six[six.split == s] for s in ['train', 'test', 'validation']]

    removed = {'without_soc': ['soc_start'], 'without_current': ['current_mean'],
               'without_soc_current': ['soc_start', 'current_mean'],
               'without_voltage': [x for x in FEATURES if x.startswith('voltage')],
               'without_temperature': ['tmax_mean', 'temperature_rise'],
               'without_cell_gap': ['cell_gap_mean', 'cell_gap_max']}
    for seed in SEEDS:
        full = fitted[600, 'random_forest'] if seed == 42 else estimator('random_forest', seed).fit(train[FEATURES], train.proxy_capacity_ah)
        for split, part in [('validation', val), ('test', test)]:
            record(part, full.predict(part[FEATURES]), 'seed', 'random_forest', 600, seed)
        for name, exclude in removed.items():
            cols = [c for c in FEATURES if c not in exclude]
            model = estimator('random_forest', seed).fit(train[cols], train.proxy_capacity_ah)
            for part in [val, test]: record(part, model.predict(part[cols]), 'ablation', name, 600, seed)
            print('ablation', seed, name, flush=True)

    for name, kind, level in [('noise_1pct', 'noise', .01), ('noise_5pct', 'noise', .05), ('missing_10pct', 'missing', .1)]:
        for part in [val, test]:
            x = stress_input(train[FEATURES], part[FEATURES], kind, level)
            record(part, fitted[600, 'random_forest'].predict(x), 'stress', name, 600)

    selections = nested_vehicle_sets(sorted(train.vehicle.unique()), [4, 6, 8, 10, 12, 14], SEEDS)
    learning_rows, learning_predictions = [], []
    cache = {tuple(sorted(train.vehicle.unique())): fitted[600, 'random_forest']}
    for row in selections:
        key = tuple(row['vehicles']); fit = train[train.vehicle.isin(key)]
        reused = key in cache
        if not reused: cache[key] = estimator('random_forest').fit(fit[FEATURES], fit.proxy_capacity_ah)
        pred = cache[key].predict(val[FEATURES])
        learning_rows.append({k: row[k] for k in ['repeat_seed', 'training_vehicle_count']} | {'training_sessions': len(fit), 'reused_fit': reused} | error_metrics(val.proxy_capacity_ah, pred, val.vehicle))
        r = val[['segment_id', 'vehicle', 'proxy_capacity_ah']].copy()
        r['repeat_seed'], r['training_vehicle_count'], r['predicted_ah'] = row['repeat_seed'], row['training_vehicle_count'], pred
        learning_predictions.append(r)
        print('learning', row['repeat_seed'], row['training_vehicle_count'], flush=True)
    pd.DataFrame(learning_rows).to_csv(dirs['02_metrics'] / 'learning_curve.csv', index=False)
    pd.concat(learning_predictions, ignore_index=True).to_csv(dirs['03_predictions'] / 'learning_curve.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    write_json(dirs['06_verification'] / 'learning_vehicle_sets.json', selections)
    predframe = pd.concat(predictions, ignore_index=True)
    pd.DataFrame(metrics).to_csv(dirs['02_metrics'] / 'all_metrics.csv', index=False)
    predframe.to_csv(dirs['03_predictions'] / 'all_predictions.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})

    # Same-subset comparisons and coverage; formula never clipped using its error or target.
    coverage_rows, fair_rows = [], []
    for w in [120, 300, 600]:
        for split in ['validation', 'test']:
            part = data[(data.window_s == w) & (data.split == split)]
            for threshold in THRESHOLDS:
                keep = (part.prefix_soc_gain_pct >= threshold) & np.isfinite(part.formula_capacity_ah)
                selected = part[keep]
                coverage_rows.append({'window_s': w, 'split': split, 'threshold': threshold,
                                      'n_total': len(part), 'n_formula': len(selected), 'coverage': len(selected)/len(part)})
                if selected.empty: continue
                for method in METHODS + ['prefix_formula']:
                    p = selected.formula_capacity_ah if method == 'prefix_formula' else fitted[w, method].predict(selected[FEATURES])
                    fair_rows.append(dict(window_s=w, split=split, threshold=threshold, experiment=method,
                                         n_total=len(part), coverage=len(selected)/len(part),
                                         **error_metrics(selected.proxy_capacity_ah, p, selected.vehicle)))
    pd.DataFrame(coverage_rows).to_csv(dirs['02_metrics'] / 'formula_coverage.csv', index=False)
    pd.DataFrame(fair_rows).to_csv(dirs['02_metrics'] / 'matched_formula_comparison.csv', index=False)

    gate_rows = []
    for part in [val, test]:
        allpred = fitted[600, 'random_forest'].predict(part[FEATURES])
        for threshold in THRESHOLDS:
            keep = (part.prefix_soc_gain_pct.to_numpy() >= threshold)
            kept = part.loc[keep]
            if kept.empty: continue
            per_cov = part.assign(keep=keep).groupby('vehicle').keep.mean()
            gate_rows.append(dict(split=part.split.iloc[0], threshold=threshold, coverage=float(keep.mean()),
                                 minimum_vehicle_coverage=float(per_cov.min()), n_total=len(part), n_rejected=int((~keep).sum()),
                                 **error_metrics(kept.proxy_capacity_ah, allpred[keep], kept.vehicle)))
    gates = pd.DataFrame(gate_rows)
    chosen = choose_quality_gate(gates[gates.split == 'validation'])
    gates['selected_on_validation'] = gates.threshold == chosen
    gates.to_csv(dirs['02_metrics'] / 'quality_coverage.csv', index=False)
    write_json(dirs['06_verification'] / 'quality_rule.json', {'selection_split': 'validation', 'threshold_soc_gain_pct': chosen,
        'coverage_constraint': .8, 'minimum_vehicle_coverage_constraint': .6,
        'statement': 'empirical data sufficiency screen in selected long-charging cohort; not safety, confidence guarantee or online population coverage'})

    # Train-derived operating-condition bins; no target or test quantiles define boundaries.
    strata, per_strata, edges_info, vehicle_rows = [], [], {}, []
    condition_cols = ['soc_start', 'tmax_mean', 'current_abs', 'prefix_soc_gain_pct']
    data['current_abs'] = abs(data.current_mean)
    for w in [120, 300, 600]:
        d = data[data.window_s == w]
        tr = d[d.split == 'train']
        for col in condition_cols:
            edges = bin_edges(tr[col]); edges_info[f'{w}_{col}'] = [None if not np.isfinite(v) else v for v in edges]
            for split in ['validation', 'test']:
                part = d[d.split == split].copy(); part['bin'] = assign_bins(part[col], edges)
                for method in METHODS:
                    part['pred'] = fitted[w, method].predict(part[FEATURES])
                    for bn, g in part.groupby('bin'):
                        if len(g) < 2: continue
                        meta = dict(window_s=w, split=split, feature=col, bin=int(bn), experiment=method)
                        strata.append(meta | error_metrics(g.proxy_capacity_ah, g.pred, g.vehicle))
                        for vehicle, gg in g.groupby('vehicle'):
                            if len(gg) >= 2: per_strata.append(meta | {'vehicle': vehicle} | error_metrics(gg.proxy_capacity_ah, gg.pred, gg.vehicle))
    pd.DataFrame(strata).to_csv(dirs['02_metrics'] / 'condition_strata.csv', index=False)
    pd.DataFrame(per_strata).to_csv(dirs['02_metrics'] / 'condition_strata_per_vehicle.csv', index=False)
    write_json(dirs['06_verification'] / 'condition_bin_edges.json', edges_info)
    for keys, g in predframe[predframe.group == 'primary'].groupby(['window_s', 'split', 'experiment', 'vehicle']):
        vehicle_rows.append(dict(zip(['window_s','split','experiment','vehicle'], keys)) | error_metrics(g.proxy_capacity_ah, g.predicted_ah, g.vehicle))
    pd.DataFrame(vehicle_rows).to_csv(dirs['02_metrics'] / 'per_vehicle.csv', index=False)
    current = pd.DataFrame(metrics)
    reference = pd.read_csv('outputs/challenge_cup_v3/02_metrics/model_comparison.csv')
    comparisons = []
    for name in ['train_mean', 'ridge', 'random_forest']:
        a = reference[reference.experiment == name].iloc[0]
        b = current[(current.group == 'primary') & (current.window_s == 600) & (current.split == 'test') & (current.experiment == name)].iloc[0]
        for field in ['mae_ah', 'rmse_ah', 'r2']:
            delta = abs(float(a[field])-float(b[field]))
            comparisons.append(dict(experiment=name, metric=field, v3=float(a[field]), v4=float(b[field]), absolute_difference=delta, passed=delta <= 1e-4))
    pd.DataFrame(comparisons).to_csv(dirs['06_verification'] / 'v3_reproduction.csv', index=False)
    if not all(x['passed'] for x in comparisons): raise AssertionError('V3 reproduction changed')
    write_json(dirs['06_verification'] / 'run_manifest.json', {
        'source_sha256': sha256(source), 'python': platform.python_version(), 'sklearn': sklearn.__version__,
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'protocol_sha256': sha256(Path(__file__).with_name('V4_PROTOCOL.md')),
        'code_sha256': sha256(__file__), 'methods': METHODS, 'windows': [120,300,600],
        'models': {p.name: sha256(p) for p in dirs['04_models'].glob('*.joblib')},
        'new_raw_window_extraction': True, 'all_primary_models_retrained': True,
        'test_used_for_selection': False, 'historical_test_previously_seen': True,
        'not_external_validation': True, 'target_is_independent_measured_soh': False})
    print('V4 experiments complete', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('outputs/challenge_cup_v4/01_data/window_features.csv.gz'))
    parser.add_argument('--output', type=Path, default=Path('outputs/challenge_cup_v4'))
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.source, args.output)
