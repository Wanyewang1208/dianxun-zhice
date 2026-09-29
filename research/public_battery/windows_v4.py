"""Read-only matched-cohort early-window extraction for retrospective V4 research.

Every window uses the same V3 retained sessions and full-session proxy label.
Quality variables and the direct-prefix formula are explicitly not model features.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .ev_experiment import COLS, FEATURES, capacity_proxy, segment_ids, split_for

WINDOWS = (120, 300, 600)
QUALITY_COLUMNS = ['prefix_soc_gain_pct', 'prefix_ah', 'prefix_duration_s',
                   'prefix_n', 'max_gap_s', 'formula_capacity_ah']


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def window_features(group, window_s):
    """Only observations at or before window_s enter any returned value."""
    if window_s not in WINDOWS:
        raise ValueError('Supported windows are 120, 300, 600 seconds')
    elapsed = (group.time - group.time.iloc[0]).dt.total_seconds().to_numpy()
    prefix = group.loc[elapsed <= window_s]
    seconds = (prefix.time - prefix.time.iloc[0]).dt.total_seconds().to_numpy()
    if len(prefix) < 2 or seconds[-1] <= 0 or (np.diff(seconds) <= 0).any():
        raise ValueError('Prefix needs at least two strictly increasing observations')
    gap = prefix.vmax - prefix.vmin
    voltage_points = np.interp([.1 * window_s, .5 * window_s, window_s],
                               seconds, prefix.voltage)
    values = [prefix.soc.iloc[0], prefix.voltage.iloc[0], *voltage_points,
              prefix.current.mean(), prefix.tmax.mean(),
              prefix.tmax.iloc[-1] - prefix.tmax.iloc[0], gap.mean(), gap.max()]
    delta_soc = float(prefix.soc.iloc[-1] - prefix.soc.iloc[0])
    amp_hours = float(-np.trapezoid(prefix.current.to_numpy(), seconds) / 3600)
    result = dict(zip(FEATURES, values))
    result.update(prefix_soc_gain_pct=delta_soc, prefix_ah=amp_hours,
                  prefix_duration_s=float(seconds[-1]), prefix_n=len(prefix),
                  max_gap_s=float(np.diff(seconds).max()),
                  formula_capacity_ah=amp_hours * 100 / delta_soc if delta_soc > 0 else np.nan)
    return result


def retained_sessions(frame):
    """Mirror the frozen V3/V2 eligibility rules without changing their code.

    Eligibility uses the full record; it describes a retrospective labeled cohort,
    not an online decision that is already available at the short-window cutoff.
    """
    data = frame.copy()
    data['time'] = pd.to_datetime(data.record_time.astype(str), format='%Y%m%d%H%M%S', errors='coerce')
    numeric = ['soc', 'voltage', 'current', 'vmax', 'vmin', 'tmax', 'tmin']
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors='coerce')
    bad = data.time.isna() | data.time.duplicated(keep=False) | ~np.isfinite(data[numeric]).all(axis=1)
    bad |= ~data.soc.between(0, 100) | (data.voltage <= 0) | (data.vmax < data.vmin) | (data.tmax < data.tmin)
    data['invalid_barrier'] = bad.astype(int).cumsum()
    data = data.sort_values(['invalid_barrier', 'time'], kind='stable')
    data['segment'] = list(zip(segment_ids(data.time), data.invalid_barrier))
    for _, group in data.loc[~bad.reindex(data.index)].groupby('segment', sort=False):
        seconds = (group.time - group.time.iloc[0]).dt.total_seconds().to_numpy()
        if seconds[-1] < 1200 or group.soc.iloc[-1] - group.soc.iloc[0] < 20:
            continue
        if (group.soc.diff().dropna() < 0).any() or (group.current >= 0).any():
            continue
        target = capacity_proxy(seconds, group.current.to_numpy(), group.soc.to_numpy())
        if not 0 < target <= 250:
            continue
        yield group, target


def extract_vehicle(frame, vehicle):
    records = []
    for index, (group, target) in enumerate(retained_sessions(frame), 1):
        for window_s in WINDOWS:
            records.append({'segment_id': f'vehicle_{vehicle:03d}_session_{index:05d}',
                            'vehicle': f'vehicle_{vehicle:03d}', 'session_index': index,
                            'split': split_for(vehicle), 'window_s': window_s,
                            'proxy_capacity_ah': target, **window_features(group, window_s)})
    return pd.DataFrame(records)


def dependency_table():
    rows = []
    for name in FEATURES:
        detail = ('pack voltage at 0.1 * window_s, prefix-only interpolation' if name == 'voltage_60' else
                  'pack voltage at 0.5 * window_s, prefix-only interpolation' if name == 'voltage_300' else
                  'pack voltage at window_s, last observed value if endpoint absent' if name == 'voltage_600' else
                  'same V3 definition restricted to observations <= window_s')
        rows.append(dict(field=name, role='model_feature', availability='prefix only',
                         uses_after_window=False, used_as_model_feature=True, definition=detail))
    descriptions = {
        'prefix_soc_gain_pct': 'last prefix SOC minus first prefix SOC, percentage points',
        'prefix_ah': 'negative trapezoidal current integral through last prefix observation / 3600',
        'prefix_duration_s': 'last observed elapsed time within requested window',
        'prefix_n': 'number of observed prefix rows',
        'max_gap_s': 'maximum gap between consecutive prefix observations',
        'formula_capacity_ah': '100 * prefix_ah / prefix_soc_gain_pct; missing when gain <= 0; no clipping'}
    for name in QUALITY_COLUMNS:
        rows.append(dict(field=name, role='quality_or_formula_baseline', availability='prefix only',
                         uses_after_window=False, used_as_model_feature=False, definition=descriptions[name]))
    rows.append(dict(field='proxy_capacity_ah', role='target', availability='full retained session',
                     uses_after_window=True, used_as_model_feature=False,
                     definition='frozen V3 full-session integral/SOC proxy, not measured SOH'))
    rows.append(dict(field='cohort_eligibility', role='retrospective_selection', availability='full retained session',
                     uses_after_window=True, used_as_model_feature=False,
                     definition='frozen V3 filtering including full duration >= 1200 s and SOC gain >= 20 pp'))
    return pd.DataFrame(rows)


def run(csv_dir, reference, source_manifest, output):
    reference = Path(reference)
    reference_hash = sha256(reference)
    base = pd.read_csv(reference)
    if len(base) != 29697 or base.vehicle.nunique() != 20 or not base.segment_id.is_unique:
        raise ValueError('Expected unique V3 cohort: 29,697 sessions / 20 vehicles')
    manifest = json.loads(Path(source_manifest).read_text(encoding='utf-8'))
    expected = {int(row['vehicle'].removeprefix('vehicle_')): row for row in manifest['raw_hashes']}
    pieces, hashes, counts = [], [], []
    for vehicle in range(1, 21):
        path = Path(csv_dir) / f'#{vehicle}.csv'
        actual_hash = sha256(path)
        if actual_hash != expected[vehicle]['csv_sha256'] or path.stat().st_size != expected[vehicle]['csv_bytes']:
            raise ValueError(f'Original CSV changed for vehicle {vehicle}')
        frame = pd.read_csv(path, low_memory=False)
        if frame.shape[1] != len(COLS):
            raise ValueError('Raw column count changed')
        frame.columns = COLS
        part = extract_vehicle(frame, vehicle)
        part600 = part[part.window_s == 600]
        prior = base[base.vehicle == f'vehicle_{vehicle:03d}']
        np.testing.assert_array_equal(part600.segment_id.to_numpy(), prior.segment_id.to_numpy())
        np.testing.assert_array_equal(part600.split.to_numpy(), prior.split.to_numpy())
        np.testing.assert_allclose(part600[['proxy_capacity_ah', *FEATURES]], prior[['proxy_capacity_ah', *FEATURES]], atol=1e-9, rtol=1e-10)
        for window_s in WINDOWS:
            subset = part[part.window_s == window_s]
            np.testing.assert_array_equal(subset.segment_id, prior.segment_id)
            np.testing.assert_allclose(subset.proxy_capacity_ah, prior.proxy_capacity_ah, atol=1e-9, rtol=1e-10)
        pieces.append(part)
        hashes.append(dict(vehicle=f'vehicle_{vehicle:03d}', csv_sha256=actual_hash, csv_bytes=path.stat().st_size, matches_v3=True))
        counts.append(dict(vehicle=f'vehicle_{vehicle:03d}', raw_rows=len(frame), retained_sessions=len(prior)))
        print(f'vehicle_{vehicle:03d}: {len(frame):,} raw rows; {len(prior):,} matched sessions x 3 windows', flush=True)
    data = pd.concat(pieces, ignore_index=True)
    if data.duplicated(['segment_id', 'window_s']).any() or len(data) != 3 * len(base):
        raise ValueError('Duplicate or missing matched window records')
    if sha256(reference) != reference_hash:
        raise ValueError('Reference changed during extraction')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    table_path = output / 'window_features.csv.gz'
    data.to_csv(table_path, index=False, compression={'method': 'gzip', 'mtime': 0})
    dependency_table().to_csv(output / 'feature_dependency.csv', index=False, encoding='utf-8-sig')
    audit = {'raw_csv_re_read': True, 'raw_rows': sum(c['raw_rows'] for c in counts),
             'vehicles': 20, 'sessions_each_window': len(base), 'window_records': len(data),
             'windows_seconds': list(WINDOWS), 'source_reference_sha256': reference_hash,
             'reference_unchanged': True, 'raw_hashes': hashes, 'per_vehicle': counts,
             'all_session_ids_and_splits_match_v3': True, 'all_window_targets_match_v3': True,
             'all_600_second_features_match_v3': True,
             'numeric_atol': 1e-9, 'numeric_rtol': 1e-10,
             'model_feature_columns': FEATURES, 'extra_columns_not_model_features': QUALITY_COLUMNS,
             'output_sha256': sha256(table_path),
             'formula_missing_counts': {str(w): int(data.loc[data.window_s == w, 'formula_capacity_ah'].isna().sum()) for w in WINDOWS},
             'voltage_aliases': {'voltage_60': '0.1 * window_s', 'voltage_300': '0.5 * window_s', 'voltage_600': 'window_s'},
             'limitations': ['Retrospective analysis of the frozen V3 eligible long-charge cohort; not online coverage.',
                             'Cohort eligibility and label require full-session observations.',
                             'Model inputs and prefix quality/formula variables only use available prefix observations.',
                             'The direct formula uses prefix end SOC as well as current; it is not present in the 10 model features.',
                             'Derived target shares electrical signals with predictors and formula; not independent measured SOH.']}
    (output / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'sessions_each_window': len(base), 'window_records': len(data), 'raw_rows': audit['raw_rows'], 'formula_missing_counts': audit['formula_missing_counts']}, ensure_ascii=False), flush=True)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv-dir', type=Path, required=True)
    parser.add_argument('--reference', type=Path, default=Path('research/public_battery/data/v3/session_features.csv'))
    parser.add_argument('--source-manifest', type=Path, default=Path('research/public_battery/data/v3/source_manifest.json'))
    parser.add_argument('--output', type=Path, default=Path('outputs/challenge_cup_v4/01_data'))
    args = parser.parse_args()
    run(args.csv_dir, args.reference, args.source_manifest, args.output)
