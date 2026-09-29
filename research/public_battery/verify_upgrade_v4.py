"""Independent V4 artifact verification; never calls experiment scoring helpers."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

FEATURES = ['soc_start', 'voltage_start', 'voltage_60', 'voltage_300', 'voltage_600',
            'current_mean', 'tmax_mean', 'temperature_rise', 'cell_gap_mean', 'cell_gap_max']
METHODS = ['train_mean', 'train_median', 'ridge', 'random_forest', 'hist_gradient_boosting']
WINDOWS = [120, 300, 600]
SEEDS = [17, 42, 2026]
THRESHOLDS = [0, 1, 2, 3, 5, 10]
SIZES = [4, 6, 8, 10, 12, 14]
ABLATIONS = ['without_soc', 'without_current', 'without_soc_current', 'without_voltage',
             'without_temperature', 'without_cell_gap']
STRESS = ['noise_1pct', 'noise_5pct', 'missing_10pct']


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verified_input_hashes(out):
    """Bind downstream materials to the exact inputs that this verifier checks."""
    out = Path(out)
    relative = ['01_data/window_features.csv.gz']
    relative += ['02_metrics/' + name + '.csv' for name in [
        'all_metrics', 'group_cv', 'learning_curve', 'matched_formula_comparison',
        'formula_coverage', 'quality_coverage', 'quality_selected_per_vehicle',
        'condition_strata', 'condition_strata_per_vehicle', 'per_vehicle']]
    relative += ['03_predictions/' + name + '.csv.gz' for name in ['all_predictions', 'group_cv', 'learning_curve']]
    relative += ['06_verification/' + name for name in [
        'run_manifest.json', 'analysis_refresh.json', 'folds.json', 'learning_vehicle_sets.json',
        'quality_rule.json', 'condition_bin_edges.json', 'v3_reproduction.csv',
        'before_threshold_tolerance_formula_coverage.csv',
        'before_threshold_tolerance_matched_formula_comparison.csv',
        'before_threshold_tolerance_quality_coverage.csv']]
    return {name: file_hash(out / name) for name in relative}


def legacy_compatibility_boundary(out, sklearn_version):
    """Summarize the separate repository-suite warning without exposing paths."""
    log = Path(out) / '06_tests_run.log'
    result = {'legacy_production_models_verified': False, 'website_deployment_verified': False,
              'v4_training_and_reload_sklearn': sklearn_version,
              'statement': 'The V4 reload checks certify only the 15 newly trained research artifacts in their recorded environment. Passing repository tests does not certify compatibility of older production models or the running website.'}
    if log.exists():
        raw = log.read_bytes()
        text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8', errors='replace')
        warnings = re.findall(r'InconsistentVersionWarning: Trying to unpickle estimator (\w+) from version ([\d.]+) when using version ([\d.]+)', text)
        versions = sorted(set((old.rstrip('.'), current.rstrip('.')) for _, old, current in warnings))
        count = re.search(r'Ran (\d+) tests', text)
        result.update(repository_test_log_sha256=file_hash(log),
                      repository_test_count=int(count.group(1)) if count else None,
                      repository_tests_reported_ok=bool(re.search(r'^OK\s*$', text, re.M)),
                      observed_version_warning_count=len(warnings),
                      warning_estimator_types=sorted({name for name, _, _ in warnings}),
                      warning_version_pairs=[{'artifact_version': old, 'runtime_version': current} for old, current in versions])
    return result


def independently_score(y, p, vehicles):
    y, p, vehicles = np.asarray(y, float), np.asarray(p, float), np.asarray(vehicles)
    assert len(y) and len(y) == len(p) == len(vehicles)
    assert np.isfinite(y).all() and np.isfinite(p).all()
    error = p - y
    absolute = np.abs(error)
    ss_total = float(np.dot(y - y.mean(), y - y.mean()))
    ss_error = float(np.dot(error, error))
    r2 = 1 - ss_error / ss_total if ss_total else (1. if ss_error == 0 else 0.)
    unique = np.unique(vehicles)
    return dict(n=len(y), vehicles=len(unique), mae_ah=float(absolute.mean()),
                rmse_ah=float(np.sqrt(np.dot(error, error) / len(error))), r2=r2,
                vehicle_macro_mae_ah=float(np.mean([absolute[vehicles == v].mean() for v in unique])),
                bias_ah=float(error.mean()), median_ae_ah=float(np.median(absolute)),
                p90_ae_ah=float(np.quantile(absolute, .9)), p95_ae_ah=float(np.quantile(absolute, .95)),
                max_ae_ah=float(absolute.max()))


def assert_group_keys(table, keys, expected):
    assert not table.duplicated(keys).any(), f'Duplicate rows: {keys}'
    actual = set(table[keys].itertuples(index=False, name=None))
    assert actual == set(expected), f'Group mismatch {keys}: missing={set(expected)-actual}; extra={actual-set(expected)}'


def assert_prediction_groups(table, keys, expected):
    actual = set(table[keys].itertuples(index=False, name=None))
    assert actual == set(expected), f'Prediction group mismatch: {keys}'
    assert not table.duplicated([*keys, 'segment_id']).any(), f'Duplicate prediction IDs: {keys}'


def align_predictions(predictions, expected):
    assert predictions.segment_id.is_unique
    assert set(predictions.segment_id) == set(expected.segment_id), 'Missing or unexpected prediction sample IDs'
    aligned = predictions.set_index('segment_id').loc[expected.segment_id]
    np.testing.assert_array_equal(aligned.vehicle.to_numpy(), expected.vehicle.to_numpy())
    np.testing.assert_allclose(aligned.proxy_capacity_ah, expected.proxy_capacity_ah, rtol=0, atol=1e-10)
    if 'split' in aligned:
        np.testing.assert_array_equal(aligned.split.to_numpy(), expected.split.to_numpy())
    return aligned.predicted_ah.to_numpy()


def run(out, threshold_tolerance=1e-9):
    out = Path(out)
    metric_dir, pred_dir, verification = out / '02_metrics', out / '03_predictions', out / '06_verification'
    manifest_path = verification / 'run_manifest.json'
    if not manifest_path.exists():
        raise RuntimeError('Experiments have not completed: run_manifest.json is absent')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    refresh_path = verification / 'analysis_refresh.json'
    if not refresh_path.exists():
        raise RuntimeError('Threshold refresh has not completed: analysis_refresh.json is absent')
    refresh = json.loads(refresh_path.read_text(encoding='utf-8'))
    assert refresh['tolerance'] == threshold_tolerance == 1e-9
    assert refresh['training_rerun'] is False
    assert refresh['code_sha256'] == file_hash(Path(__file__).with_name('quality_refresh_v4.py'))
    for name, digest in refresh['before_analysis_sha256'].items():
        assert file_hash(verification / ('before_threshold_tolerance_' + name)) == digest
    for name, digest in refresh['after_analysis_sha256'].items():
        assert file_hash(metric_dir / name) == digest
    data_path = out / '01_data/window_features.csv.gz'
    assert file_hash(data_path) == manifest['source_sha256']
    assert file_hash(data_path) == refresh['source_sha256']
    assert manifest['historical_test_previously_seen'] is True
    assert manifest['test_used_for_selection'] is False
    assert manifest['target_is_independent_measured_soh'] is False
    assert manifest['methods'] == METHODS and manifest['windows'] == WINDOWS
    data = pd.read_csv(data_path)
    assert len(data) == 89091 and data.segment_id.nunique() == 29697
    assert not data.duplicated(['window_s', 'segment_id']).any()
    assert set(data.window_s) == set(WINDOWS)
    assert np.isfinite(data[FEATURES + ['proxy_capacity_ah']]).all().all()
    assert (data.prefix_duration_s <= data.window_s).all()
    v3_data = pd.read_csv('research/public_battery/data/v3/session_features.csv').set_index('segment_id').sort_index()
    six_data = data[data.window_s == 600].set_index('segment_id').sort_index()
    np.testing.assert_array_equal(six_data.index, v3_data.index)
    np.testing.assert_array_equal(six_data.vehicle, v3_data.vehicle)
    np.testing.assert_array_equal(six_data.split, v3_data.split)
    np.testing.assert_allclose(six_data[['proxy_capacity_ah', *FEATURES]], v3_data[['proxy_capacity_ah', *FEATURES]], atol=1e-9, rtol=1e-10)
    parts = {(w, s): data[(data.window_s == w) & (data.split == s)].copy()
             for w in WINDOWS for s in ['train', 'validation', 'test']}
    train_ids = [f'vehicle_{v:03d}' for v in range(1, 15)]
    for w in WINDOWS:
        for split, vehicles, n in [('train', train_ids, 20851), ('validation', ['vehicle_015', 'vehicle_016'], 2864),
                                    ('test', [f'vehicle_{v:03d}' for v in range(17, 21)], 5982)]:
            part = parts[w, split]
            assert len(part) == n and set(part.vehicle) == set(vehicles)
        matching = data[data.window_s == w].set_index('segment_id').sort_index()
        baseline = data[data.window_s == 600].set_index('segment_id').sort_index()
        np.testing.assert_array_equal(matching.index, baseline.index)
        np.testing.assert_array_equal(matching.vehicle, baseline.vehicle)
        np.testing.assert_array_equal(matching.split, baseline.split)
        np.testing.assert_allclose(matching.proxy_capacity_ah, baseline.proxy_capacity_ah, atol=1e-10, rtol=0)
    formula_valid = data.prefix_soc_gain_pct > 0
    assert data.loc[~formula_valid, 'formula_capacity_ah'].isna().all()
    np.testing.assert_allclose(data.loc[formula_valid, 'formula_capacity_ah'],
                               100 * data.loc[formula_valid, 'prefix_ah'] / data.loc[formula_valid, 'prefix_soc_gain_pct'], atol=1e-8, rtol=1e-12)
    records = []
    table_counts = {}

    def verify_row(row, part, predictions, scope, **meta):
        values = independently_score(part.proxy_capacity_ah, predictions, part.vehicle)
        for key, value in values.items():
            assert key in row, f'Missing metric {scope}/{key}'
            np.testing.assert_allclose(float(row[key]), value, atol=1e-9, rtol=1e-12,
                                       err_msg=f'{scope} {meta} {key}')
        records.append(dict(scope=scope, **meta, **values))

    all_metrics = pd.read_csv(metric_dir / 'all_metrics.csv')
    all_predictions = pd.read_csv(pred_dir / 'all_predictions.csv.gz')
    keys = ['group', 'experiment', 'window_s', 'seed', 'split']
    expected = []
    for w in WINDOWS:
        for split in ['validation', 'test']:
            expected += [('primary', method, w, 42, split) for method in METHODS]
            expected.append(('formula', 'prefix_formula', w, 42, split))
    for seed in SEEDS:
        for split in ['validation', 'test']:
            expected.append(('seed', 'random_forest', 600, seed, split))
            expected += [('ablation', name, 600, seed, split) for name in ABLATIONS]
    expected += [('stress', name, 600, 42, split) for name in STRESS for split in ['validation', 'test']]
    assert len(expected) == 84
    assert_group_keys(all_metrics, keys, expected)
    assert_prediction_groups(all_predictions, keys, expected)
    groups = all_predictions.groupby(keys, sort=False)
    primary = {}
    for _, row in all_metrics.iterrows():
        key = tuple(row[k] for k in keys)
        part = parts[int(row.window_s), row['split']]
        if row['group'] == 'formula':
            part = part[np.isfinite(part.formula_capacity_ah)]
        predictions = align_predictions(groups.get_group(key), part)
        verify_row(row, part, predictions, 'all_metrics', **dict(zip(keys, key)))
        if row['group'] == 'formula':
            np.testing.assert_allclose(predictions, part.formula_capacity_ah, atol=1e-10, rtol=0)
        if row['group'] == 'primary':
            primary[int(row.window_s), row['split'], row.experiment] = pd.Series(predictions, index=part.segment_id)
    table_counts['all_metrics'] = len(all_metrics)
    print('verified 84 main metric groups and complete prediction IDs', flush=True)

    reload_count = 0
    expected_files = {f'{m}_{w}s.joblib' for w in WINDOWS for m in METHODS}
    assert set(manifest['models']) == expected_files
    for w in WINDOWS:
        train = parts[w, 'train']
        for method in METHODS:
            name = f'{method}_{w}s.joblib'
            path = out / '04_models' / name
            assert file_hash(path) == manifest['models'][name]
            bundle = joblib.load(path)
            assert bundle['features'] == FEATURES and bundle['window_s'] == w
            assert bundle['training_vehicles'] == train_ids
            model = bundle['model']
            if method == 'ridge':
                scaler = model.steps[0][1]
                np.testing.assert_allclose(scaler.mean_, train[FEATURES].mean().to_numpy(), atol=1e-10, rtol=1e-12)
                np.testing.assert_allclose(scaler.var_, train[FEATURES].var(ddof=0).to_numpy(), atol=1e-10, rtol=1e-12)
                assert scaler.n_samples_seen_ == len(train)
            for split in ['validation', 'test']:
                part = parts[w, split]
                predictions = model.predict(part[FEATURES])
                np.testing.assert_allclose(predictions, primary[w, split, method].loc[part.segment_id], atol=1e-9, rtol=0)
                if method in ['train_mean', 'train_median']:
                    constant = train.proxy_capacity_ah.mean() if method == 'train_mean' else train.proxy_capacity_ah.median()
                    np.testing.assert_allclose(predictions, constant, atol=1e-10, rtol=0)
                reload_count += 1
    print('verified 15 saved models over every validation and test sample', flush=True)

    cv_metrics = pd.read_csv(metric_dir / 'group_cv.csv')
    cv_predictions = pd.read_csv(pred_dir / 'group_cv.csv.gz')
    fold_table = pd.DataFrame(json.loads((verification / 'folds.json').read_text(encoding='utf-8')))
    assert_group_keys(fold_table, ['window_s', 'fold'], [(w, f) for w in WINDOWS for f in range(1, 6)])
    for w in WINDOWS:
        seen = []
        for _, fold in fold_table[fold_table.window_s == w].iterrows():
            fit, holdout = set(fold.fit_vehicles), set(fold.holdout_vehicles)
            assert fit and holdout and not fit & holdout and fit | holdout == set(train_ids)
            seen.extend(fold.holdout_vehicles)
        assert sorted(seen) == train_ids
    cv_keys = ['window_s', 'fold', 'experiment']
    cv_expected = [(w, f, m) for w in WINDOWS for f in range(1, 6) for m in METHODS]
    assert_group_keys(cv_metrics, cv_keys, cv_expected)
    assert_prediction_groups(cv_predictions, cv_keys, cv_expected)
    cv_groups = cv_predictions.groupby(cv_keys, sort=False)
    for _, row in cv_metrics.iterrows():
        w, fold = int(row.window_s), int(row.fold)
        definition = fold_table[(fold_table.window_s == w) & (fold_table.fold == fold)].iloc[0]
        part = parts[w, 'train']
        part = part[part.vehicle.isin(definition.holdout_vehicles)]
        prediction = align_predictions(cv_groups.get_group((w, fold, row.experiment)), part)
        verify_row(row, part, prediction, 'group_cv', window_s=w, fold=fold, experiment=row.experiment)
    table_counts['group_cv'] = len(cv_metrics)

    learning = pd.read_csv(metric_dir / 'learning_curve.csv')
    lp = pd.read_csv(pred_dir / 'learning_curve.csv.gz')
    selections = pd.DataFrame(json.loads((verification / 'learning_vehicle_sets.json').read_text(encoding='utf-8')))
    learning_keys = ['repeat_seed', 'training_vehicle_count']
    learning_expected = [(seed, n) for seed in SEEDS for n in SIZES]
    assert_group_keys(learning, learning_keys, learning_expected)
    assert_group_keys(selections, learning_keys, learning_expected)
    assert_prediction_groups(lp, learning_keys, learning_expected)
    lpgroups = lp.groupby(learning_keys, sort=False)
    cache = {tuple(train_ids)}
    for seed in SEEDS:
        permutation = np.random.default_rng(seed).permutation(train_ids).tolist()
        previous = set()
        for n in SIZES:
            selection = selections[(selections.repeat_seed == seed) & (selections.training_vehicle_count == n)].iloc[0]
            vehicles = selection.vehicles
            assert vehicles == sorted(permutation[:n]) and len(vehicles) == n
            assert previous <= set(vehicles) <= set(train_ids)
            previous = set(vehicles)
            row = learning[(learning.repeat_seed == seed) & (learning.training_vehicle_count == n)].iloc[0]
            assert int(row.training_sessions) == int(parts[600, 'train'].vehicle.isin(vehicles).sum())
            assert bool(row.reused_fit) == (tuple(vehicles) in cache)
            cache.add(tuple(vehicles))
            part = parts[600, 'validation']
            prediction = align_predictions(lpgroups.get_group((seed, n)), part)
            verify_row(row, part, prediction, 'learning_curve', repeat_seed=seed, training_vehicle_count=n)
            if n == 14:
                np.testing.assert_allclose(prediction, primary[600, 'validation', 'random_forest'].loc[part.segment_id], atol=1e-9, rtol=0)
    table_counts['learning_curve'] = len(learning)
    print('verified 75 grouped-CV and 18 nested learning-curve rows', flush=True)

    fair = pd.read_csv(metric_dir / 'matched_formula_comparison.csv')
    coverage = pd.read_csv(metric_dir / 'formula_coverage.csv')
    fair_expected, coverage_expected = [], []
    fair_index = fair.set_index(['window_s', 'split', 'threshold', 'experiment'])
    coverage_index = coverage.set_index(['window_s', 'split', 'threshold'])
    for w in WINDOWS:
        for split in ['validation', 'test']:
            part = parts[w, split]
            for threshold in THRESHOLDS:
                coverage_expected.append((w, split, threshold))
                keep = (part.prefix_soc_gain_pct >= threshold - threshold_tolerance) & np.isfinite(part.formula_capacity_ah)
                selected = part[keep]
                crow = coverage_index.loc[(w, split, threshold)]
                assert int(crow.n_total) == len(part) and int(crow.n_formula) == len(selected)
                np.testing.assert_allclose(crow.coverage, len(selected) / len(part), atol=1e-12, rtol=0)
                if selected.empty:
                    continue
                for method in [*METHODS, 'prefix_formula']:
                    key = (w, split, threshold, method)
                    fair_expected.append(key)
                    row = fair_index.loc[key]
                    assert int(row.n_total) == len(part)
                    np.testing.assert_allclose(row.coverage, len(selected) / len(part), atol=1e-12, rtol=0)
                    predictions = selected.formula_capacity_ah if method == 'prefix_formula' else primary[w, split, method].loc[selected.segment_id]
                    verify_row(row, selected, predictions, 'matched_formula', window_s=w, split=split, threshold=threshold, experiment=method)
    assert_group_keys(fair, ['window_s', 'split', 'threshold', 'experiment'], fair_expected)
    assert_group_keys(coverage, ['window_s', 'split', 'threshold'], coverage_expected)
    table_counts['matched_formula_comparison'] = len(fair)
    table_counts['formula_coverage'] = len(coverage)

    quality = pd.read_csv(metric_dir / 'quality_coverage.csv')
    rule = json.loads((verification / 'quality_rule.json').read_text(encoding='utf-8'))
    assert rule['selection_split'] == 'validation'
    assert rule['coverage_constraint'] == .8 and rule['minimum_vehicle_coverage_constraint'] == .6
    assert rule['comparison_tolerance'] == threshold_tolerance
    gate_expected, recomputed_gate_rows = [], []
    for split in ['validation', 'test']:
        part = parts[600, split]
        for threshold in THRESHOLDS:
            keep = part.prefix_soc_gain_pct >= threshold - threshold_tolerance
            selected = part[keep]
            if selected.empty:
                continue
            gate_expected.append((split, threshold))
            row = quality[(quality['split'] == split) & (quality.threshold == threshold)].iloc[0]
            coverage_ratio = len(selected) / len(part)
            min_vehicle_coverage = float(part.assign(kept=keep).groupby('vehicle').kept.mean().min())
            assert int(row.n_total) == len(part) and int(row.n_rejected) == len(part) - len(selected)
            np.testing.assert_allclose([row.coverage, row.minimum_vehicle_coverage], [coverage_ratio, min_vehicle_coverage], atol=1e-12, rtol=0)
            prediction = primary[600, split, 'random_forest'].loc[selected.segment_id]
            verify_row(row, selected, prediction, 'quality_coverage', split=split, threshold=threshold)
            metrics = independently_score(selected.proxy_capacity_ah, prediction, selected.vehicle)
            recomputed_gate_rows.append(dict(split=split, threshold=threshold, coverage=coverage_ratio,
                                            minimum_vehicle_coverage=min_vehicle_coverage, **metrics))
    assert_group_keys(quality, ['split', 'threshold'], gate_expected)
    eligible = [r for r in recomputed_gate_rows if r['split'] == 'validation' and r['coverage'] >= .8 and r['minimum_vehicle_coverage'] >= .6]
    chosen = sorted(eligible, key=lambda r: (r['vehicle_macro_mae_ah'], r['threshold']))[0]['threshold'] if eligible else 0
    assert int(rule['threshold_soc_gain_pct']) == chosen
    assert (quality.selected_on_validation == quality.threshold.eq(chosen)).all()
    table_counts['quality_coverage'] = len(quality)
    selected_vehicle = pd.read_csv(metric_dir / 'quality_selected_per_vehicle.csv')
    selected_keys = ['split', 'vehicle', 'status']
    selected_index = selected_vehicle.set_index(selected_keys)
    selected_expected = []
    for split in ['validation', 'test']:
        part = parts[600, split]
        keep = part.prefix_soc_gain_pct >= chosen - threshold_tolerance
        for status, mask in [('retained', keep), ('rejected', ~keep)]:
            for vehicle, selected in part[mask].groupby('vehicle'):
                if len(selected) < 2:
                    continue
                key = (split, vehicle, status)
                selected_expected.append(key)
                row = selected_index.loc[key]
                assert int(row.threshold) == chosen
                verify_row(row, selected, primary[600, split, 'random_forest'].loc[selected.segment_id],
                           'quality_selected_per_vehicle', **dict(zip(selected_keys, key)), threshold=chosen)
    assert_group_keys(selected_vehicle, selected_keys, selected_expected)
    table_counts['quality_selected_per_vehicle'] = len(selected_vehicle)
    print('verified formula common subsets and validation-only quality-rule selection', flush=True)

    strata = pd.read_csv(metric_dir / 'condition_strata.csv')
    per_strata = pd.read_csv(metric_dir / 'condition_strata_per_vehicle.csv')
    edges_info = json.loads((verification / 'condition_bin_edges.json').read_text(encoding='utf-8'))
    conditions = ['soc_start', 'tmax_mean', 'current_abs', 'prefix_soc_gain_pct']
    strata_keys = ['window_s', 'split', 'feature', 'bin', 'experiment']
    expected_strata, expected_per_strata = [], []
    strata_index = strata.set_index(strata_keys)
    per_strata_index = per_strata.set_index([*strata_keys, 'vehicle'])
    assert set(edges_info) == {f'{w}_{c}' for w in WINDOWS for c in conditions}
    for w in WINDOWS:
        train = parts[w, 'train'].assign(current_abs=lambda d: abs(d.current_mean))
        for column in conditions:
            quantiles = np.unique(np.quantile(train[column], [1/3, 2/3]))
            stored = edges_info[f'{w}_{column}']
            assert stored[0] is None and stored[-1] is None
            np.testing.assert_allclose(stored[1:-1], quantiles, atol=1e-12, rtol=0)
            for split in ['validation', 'test']:
                part = parts[w, split].assign(current_abs=lambda d: abs(d.current_mean))
                part['condition_bin'] = np.searchsorted(quantiles, part[column], side='left')
                for method in METHODS:
                    for bn, selected in part.groupby('condition_bin'):
                        if len(selected) < 2:
                            continue
                        key = (w, split, column, int(bn), method)
                        expected_strata.append(key)
                        prediction = primary[w, split, method].loc[selected.segment_id]
                        verify_row(strata_index.loc[key], selected, prediction, 'condition_strata', **dict(zip(strata_keys, key)))
                        for vehicle, selected_vehicle in selected.groupby('vehicle'):
                            if len(selected_vehicle) < 2:
                                continue
                            vehicle_key = (*key, vehicle)
                            expected_per_strata.append(vehicle_key)
                            prediction = primary[w, split, method].loc[selected_vehicle.segment_id]
                            verify_row(per_strata_index.loc[vehicle_key], selected_vehicle, prediction, 'condition_strata_per_vehicle',
                                       **dict(zip([*strata_keys, 'vehicle'], vehicle_key)))
    assert_group_keys(strata, strata_keys, expected_strata)
    assert_group_keys(per_strata, [*strata_keys, 'vehicle'], expected_per_strata)
    table_counts['condition_strata'] = len(strata)
    table_counts['condition_strata_per_vehicle'] = len(per_strata)
    per_vehicle = pd.read_csv(metric_dir / 'per_vehicle.csv')
    vehicle_keys = ['window_s', 'split', 'experiment', 'vehicle']
    expected_vehicle = []
    vehicle_index = per_vehicle.set_index(vehicle_keys)
    for w in WINDOWS:
        for split in ['validation', 'test']:
            for vehicle, part in parts[w, split].groupby('vehicle'):
                for method in METHODS:
                    key = (w, split, method, vehicle)
                    expected_vehicle.append(key)
                    verify_row(vehicle_index.loc[key], part, primary[w, split, method].loc[part.segment_id], 'per_vehicle', **dict(zip(vehicle_keys, key)))
    assert_group_keys(per_vehicle, vehicle_keys, expected_vehicle)
    table_counts['per_vehicle'] = len(per_vehicle)

    v3 = pd.read_csv('outputs/challenge_cup_v3/02_metrics/model_comparison.csv')
    reproduction = pd.read_csv(verification / 'v3_reproduction.csv')
    comparison_expected = [(method, metric) for method in ['train_mean', 'ridge', 'random_forest'] for metric in ['mae_ah', 'rmse_ah', 'r2']]
    assert_group_keys(reproduction, ['experiment', 'metric'], comparison_expected)
    for _, row in reproduction.iterrows():
        old = float(v3[v3.experiment == row.experiment].iloc[0][row.metric])
        fresh = float(all_metrics[(all_metrics['group'] == 'primary') & (all_metrics.window_s == 600) & (all_metrics['split'] == 'test') & (all_metrics.experiment == row.experiment)].iloc[0][row.metric])
        np.testing.assert_allclose([row.v3, row.v4, row.absolute_difference], [old, fresh, abs(old - fresh)], atol=1e-12, rtol=0)
        assert bool(row.passed) and abs(old - fresh) <= 1e-4
    table_counts['v3_reproduction'] = len(reproduction)

    boundary = []
    for w in WINDOWS:
        for split in ['train', 'validation', 'test']:
            part = parts[w, split]
            for threshold in THRESHOLDS:
                strict = part.prefix_soc_gain_pct >= threshold
                tolerant = part.prefix_soc_gain_pct >= threshold - 1e-9
                difference = int((strict != tolerant).sum())
                if difference:
                    boundary.append(dict(window_s=w, split=split, threshold=threshold, changed_samples=difference))
    code_path = Path(__file__).with_name('upgrade_v4.py')
    protocol_path = Path(__file__).with_name('V4_PROTOCOL.md')
    code_match = manifest['code_sha256'] == file_hash(code_path)
    protocol_match = manifest['protocol_sha256'] == file_hash(protocol_path)
    assert code_match and protocol_match, 'Training code/protocol changed after recorded run'
    warnings = []
    if boundary and not threshold_tolerance:
        warnings.append('SOC quantization has floating-point boundary effects; strict >= comparisons are internally reproduced but tolerance-based refresh is recommended.')
    if not code_match or not protocol_match:
        warnings.append('Current experiment code/protocol differs from the training manifest; preserve original hashes and record a separate analysis-refresh provenance chain.')
    numeric = pd.DataFrame(records)
    numeric.to_csv(verification / 'independent_metrics.csv', index=False)
    report = {'passed': True, 'method': 'Independent NumPy calculations from saved per-sample predictions; no experiment scoring helper imports.',
              'window_rows': len(data), 'independent_sessions': data.segment_id.nunique(),
              'metric_rows_by_table': table_counts, 'independently_recomputed_metric_rows': len(numeric),
              'models_reloaded': 15, 'full_split_reload_checks': reload_count,
              'all_prediction_ids_unique_and_complete': True, 'cv_training_vehicles_only': True,
              'learning_sets_nested_training_only': True, 'same_14_vehicle_endpoint_reused': True,
              'strata_edges_fit_on_train_only': True, 'quality_selection_split': 'validation',
              'selected_soc_gain_threshold': chosen, 'threshold_comparison_tolerance': threshold_tolerance,
              'same_subset_formula_comparison_verified': True,
              'training_manifest_code_matches_current': code_match, 'training_manifest_protocol_matches_current': protocol_match,
              'floating_boundary_changes_with_1e_9_tolerance': boundary, 'warnings': warnings,
              'verifier_sha256': file_hash(__file__), 'run_manifest_sha256': file_hash(manifest_path),
              'analysis_refresh_sha256': file_hash(refresh_path), 'analysis_refresh_provenance_verified': True,
              'verified_inputs_sha256': verified_input_hashes(out),
              'legacy_production_compatibility': legacy_compatibility_boundary(out, manifest['sklearn']),
              'independent_metrics_sha256': file_hash(verification / 'independent_metrics.csv'),
              'limits': ['Historical test results were previously inspected; retrospective supplementary analysis.',
                         'Same-source capacity proxy, not independent measured SOH.',
                         'Coverage is conditional on frozen long-charging-session eligibility, not online population coverage.']}
    (verification / 'independent_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'metric_rows_by_table': table_counts, 'models_reloaded': 15, 'warnings': warnings}, ensure_ascii=False), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('outputs/challenge_cup_v4'))
    parser.add_argument('--threshold-tolerance', type=float, default=1e-9)
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.output, args.threshold_tolerance)
