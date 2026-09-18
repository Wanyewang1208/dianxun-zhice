"""Reproducible exploratory proxy-capacity experiment; no measured SOH claims."""
import argparse
import hashlib
import json
import subprocess
import platform
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

COLS = ['unused', 'record_time', 'soc', 'voltage', 'current', 'vmax', 'vmin', 'tmax', 'tmin', 'energy', 'available_capacity']
FEATURES = ['soc_start', 'voltage_start', 'voltage_60', 'voltage_300', 'voltage_600', 'current_mean', 'tmax_mean', 'temperature_rise', 'cell_gap_mean', 'cell_gap_max']

def split_for(vehicle):
    return 'train' if vehicle <= 14 else 'validation' if vehicle <= 16 else 'test'

def capacity_proxy(seconds, current, soc):
    return float(-np.trapezoid(current, seconds) / 3600 * 100 / (soc[-1] - soc[0]))

def session_features(g):
    seconds = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
    prefix = g.loc[seconds <= 600]
    gap = prefix.vmax - prefix.vmin
    # Interpolation is restricted to prefix observations, never future rows.
    x = (prefix.time - prefix.time.iloc[0]).dt.total_seconds().to_numpy()
    return dict(zip(FEATURES, [prefix.soc.iloc[0], prefix.voltage.iloc[0],
        *np.interp([60, 300, 600], x, prefix.voltage), prefix.current.mean(),
        prefix.tmax.mean(), prefix.tmax.iloc[-1] - prefix.tmax.iloc[0], gap.mean(), gap.max()]))

def segment_ids(times):
    delta = times.diff().dt.total_seconds()
    return ((delta <= 0) | (delta > 10) | delta.isna()).cumsum()

def extract_sessions(frame, vehicle):
    d = frame.copy()
    d['time'] = pd.to_datetime(d.record_time.astype(str), format='%Y%m%d%H%M%S', errors='coerce')
    numeric = ['soc', 'voltage', 'current', 'vmax', 'vmin', 'tmax', 'tmin']
    for c in numeric:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    bad = d.time.isna() | d.time.duplicated(keep=False) | ~np.isfinite(d[numeric]).all(axis=1)
    bad |= ~d.soc.between(0, 100) | (d.voltage <= 0) | (d.vmax < d.vmin) | (d.tmax < d.tmin)
    # Invalid rows break sessions; never bridge a removed observation.
    d['invalid_barrier'] = bad.astype(int).cumsum()
    d = d.sort_values(['invalid_barrier', 'time'], kind='stable')
    d['segment'] = list(zip(segment_ids(d.time), d.invalid_barrier))
    counts = {'raw_rows': len(d), 'invalid_or_duplicate_rows': int(bad.sum()), 'candidate_segments': 0,
              'short_or_low_soc_gain': 0, 'non_monotonic_or_noncharging': 0, 'implausible_proxy': 0}
    records = []
    for _, g in d.loc[~bad.reindex(d.index)].groupby('segment', sort=False):
        counts['candidate_segments'] += 1
        sec = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
        if sec[-1] < 1200 or g.soc.iloc[-1] - g.soc.iloc[0] < 20:
            counts['short_or_low_soc_gain'] += 1
            continue
        if (g.soc.diff().dropna() < 0).any() or (g.current >= 0).any():
            counts['non_monotonic_or_noncharging'] += 1
            continue
        q = capacity_proxy(sec, g.current.to_numpy(), g.soc.to_numpy())
        if not 0 < q <= 250:
            counts['implausible_proxy'] += 1
            continue
        records.append({'vehicle': vehicle, 'split': split_for(vehicle), 'start_local_unspecified': str(g.time.iloc[0]),
                        'proxy_capacity_ah': q, **session_features(g)})
    counts['retained_sessions'] = len(records)
    return records, counts

def demo_check(frame):
    from backend.v03.bms_validate import validate
    t = frame.head(100).rename(columns=dict(zip(['voltage','current','soc','vmax','vmin','tmax','tmin'],
        ['pack_voltage','pack_current','SOC','cell_voltage_max','cell_voltage_min','temperature_max','temperature_min']))).copy()
    t['timestamp'] = pd.to_datetime(t.record_time.astype(str), format='%Y%m%d%H%M%S').astype(str)
    t['battery_id'] = 'public_EV_1'
    t['charge_status'] = 'charging'  # Source is charging-only; negative source current means charging.
    t = t[['battery_id','timestamp','pack_voltage','pack_current','SOC','cell_voltage_max','cell_voltage_min','temperature_max','temperature_min','charge_status']]
    m = pd.DataFrame([dict(battery_id='public_EV_1', battery_chemistry='NCM', rated_capacity_ah=145,
        current_sign_convention='discharge_positive',voltage_unit='V',current_unit='A',temperature_unit='degC',soc_unit='%',data_origin='public_real_vehicle_charging')])
    raw = validate(t, m)
    # Explicitly hypothetical adapter test, not a verified source timezone.
    t.timestamp = t.timestamp + '+08:00'
    assumed = validate(t, m)
    return {'source_timezone': 'undocumented; must confirm with provider', 'raw_naive_timestamps': raw['summary'],
            'raw_issue_codes': raw['issues'].code.value_counts().to_dict(),
            'conditional_assumption_only_UTC_plus_8': assumed['summary']}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--raw-repo', type=Path, required=True)
    p.add_argument('--extracted', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.extracted.mkdir(parents=True, exist_ok=True)
    a.output.mkdir(parents=True, exist_ok=True)
    rows, audit, manifest = [], [], []
    for vehicle in range(1, 21):
        archive = a.raw_repo / f'#{vehicle}.rar'
        expected = f'#{vehicle}.csv'
        members = subprocess.check_output(['tar', '-tf', str(archive)], text=True).splitlines()
        if members != [expected]:
            raise ValueError(f'Unexpected archive members: {members}')
        subprocess.run(['tar', '-xf', str(archive.resolve()), '-C', str(a.extracted.resolve())], check=True)
        csv = a.extracted / expected
        frame = pd.read_csv(csv)
        if frame.shape[1] != len(COLS):
            raise ValueError('Source schema changed')
        frame.columns = COLS
        found, stats = extract_sessions(frame, vehicle)
        rows.extend(found)
        audit.append({'vehicle': vehicle, **stats})
        manifest.append({'vehicle': vehicle, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                         'csv_sha256': hashlib.sha256(csv.read_bytes()).hexdigest(), 'csv_bytes': csv.stat().st_size})
        if vehicle == 1:
            (a.output / 'demo_compatibility.json').write_text(json.dumps(demo_check(frame), indent=2), encoding='utf-8')
        print(f'EV {vehicle}: {len(frame)} rows, {len(found)} retained sessions', flush=True)
    data = pd.DataFrame(rows)
    data.to_csv(a.output / 'session_features.csv', index=False)
    pd.DataFrame(audit).to_csv(a.output / 'audit.csv', index=False)
    (a.output / 'raw_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    train = data[data.split == 'train']
    models = {'ridge': make_pipeline(StandardScaler(), Ridge(alpha=10)),
              'random_forest': RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=42, n_jobs=2)}
    metrics, predictions = [], []
    for name in ['train_mean', *models]:
        if name in models:
            models[name].fit(train[FEATURES], train.proxy_capacity_ah)
        for split in ['validation', 'test']:
            part = data[data.split == split]
            pred = np.full(len(part), train.proxy_capacity_ah.mean()) if name == 'train_mean' else models[name].predict(part[FEATURES])
            metrics.append({'model': name, 'split': split, 'n': len(part),
                'mae_ah': mean_absolute_error(part.proxy_capacity_ah, pred),
                'rmse_ah': float(np.sqrt(mean_squared_error(part.proxy_capacity_ah, pred))), 'r2': r2_score(part.proxy_capacity_ah, pred)})
            predictions.extend({'model': name, 'vehicle': int(r.vehicle), 'split': split, 'start': r.start_local_unspecified,
                'proxy_capacity_ah': r.proxy_capacity_ah, 'predicted_ah': float(v)} for (_, r), v in zip(part.iterrows(), pred))
    pd.DataFrame(predictions).to_csv(a.output / 'predictions.csv', index=False)
    per_vehicle = []
    for (name, vehicle), g in pd.DataFrame(predictions).groupby(['model', 'vehicle']):
        per_vehicle.append({'model': name, 'vehicle': int(vehicle), 'n': len(g),
                            'mae_ah': mean_absolute_error(g.proxy_capacity_ah, g.predicted_ah)})
    pd.DataFrame(per_vehicle).to_csv(a.output / 'per_vehicle_metrics.csv', index=False)
    scaler, ridge = models['ridge'].steps[0][1], models['ridge'].steps[1][1]
    learned = {'features': FEATURES, 'train_mean_ah': float(train.proxy_capacity_ah.mean()),
        'ridge_scaler_mean': scaler.mean_.tolist(), 'ridge_scaler_scale': scaler.scale_.tolist(),
        'ridge_coefficients': ridge.coef_.tolist(), 'ridge_intercept': float(ridge.intercept_),
        'rf_feature_importances': models['random_forest'].feature_importances_.tolist()}
    (a.output / 'learned_parameters.json').write_text(json.dumps(learned, indent=2), encoding='utf-8')
    import sklearn, scipy
    environment = {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                   'scipy': scipy.__version__, 'scikit_learn': sklearn.__version__}
    (a.output / 'environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    (a.output / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2))

if __name__ == '__main__':
    main()
