"""Read-only raw-data audit and anonymized V3 feature preparation."""
import argparse
import hashlib
import json
import subprocess
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from research.public_battery.ev_experiment import COLS, FEATURES, extract_sessions, split_for

# Broad screening bounds only: not OEM limits, safety thresholds, or anomaly labels.
BROAD_RANGES = {'soc': (0, 100), 'voltage': (0, 1000), 'current': (-1000, 1000),
                'vmax': (0, 6), 'vmin': (0, 6), 'tmax': (-50, 100), 'tmin': (-50, 100),
                'energy': (0, 1000), 'available_capacity': (0, 1000)}


def quality(frame):
    cols = {}
    for name in COLS:
        if name == 'record_time':
            continue
        x = pd.to_numeric(frame[name], errors='coerce')
        finite = np.isfinite(x)
        good = x[finite]
        lo, hi = BROAD_RANGES.get(name, (-float('inf'), float('inf')))
        cols[name] = {'missing_or_non_numeric': int(x.isna().sum()),
                      'missing_rate': float(x.isna().mean()), 'infinite': int((~finite & x.notna()).sum()),
                      'min': float(good.min()) if len(good) else None,
                      'max': float(good.max()) if len(good) else None,
                      'outside_broad_range': int((finite & ((x < lo) | (x > hi))).sum())}
    t = pd.to_datetime(frame.record_time.astype(str), format='%Y%m%d%H%M%S', errors='coerce')
    dt = t.diff().dt.total_seconds()
    positive = dt[dt > 0]
    return {'rows': len(frame), 'columns': cols,
            'time': {'invalid_rows': int(t.isna().sum()), 'missing_rate': float(t.isna().mean()),
                     'duplicate_rows': int((t.notna() & t.duplicated(keep=False)).sum()),
                     'backward_steps': int((dt < 0).sum()), 'zero_intervals': int((dt == 0).sum()),
                     'gaps_gt_10s': int((dt > 10).sum()), 'gaps_gt_1h': int((dt > 3600).sum()),
                     'positive_interval_min_seconds': float(positive.min()) if len(positive) else None,
                     'positive_interval_median_seconds': float(positive.median()) if len(positive) else None,
                     'positive_interval_max_seconds': float(positive.max()) if len(positive) else None,
                     'observed_span_days': float((t.max() - t.min()).total_seconds() / 86400) if t.notna().any() else None},
            'order_violations': {'vmax_lt_vmin': int((pd.to_numeric(frame.vmax, errors='coerce') < pd.to_numeric(frame.vmin, errors='coerce')).sum()),
                                 'tmax_lt_tmin': int((pd.to_numeric(frame.tmax, errors='coerce') < pd.to_numeric(frame.tmin, errors='coerce')).sum())}}


def anonymize(frame):
    out = frame.drop(columns=['start_local_unspecified']).copy()
    out['session_index'] = out.groupby('vehicle', sort=False).cumcount() + 1
    out['vehicle'] = out.vehicle.map(lambda x: f'vehicle_{int(x):03d}')
    out['segment_id'] = [f'{v}_session_{int(i):05d}' for v, i in zip(out.vehicle, out.session_index)]
    return out[['segment_id', 'vehicle', 'session_index'] + [c for c in out if c not in ('segment_id', 'vehicle', 'session_index')]]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def verify_derivatives(root):
    folder = root / 'research/public_battery/data/v3'
    public = pd.read_csv(folder / 'session_features.csv')
    private = pd.read_csv(root.parent / 'v3-private/session_features.csv')
    old = pd.read_csv(root / 'research/public_battery/results/ev/session_features.csv')
    numbers = ['proxy_capacity_ah', *FEATURES]
    expected = anonymize(private)
    shards = pd.concat([pd.read_csv(p) for p in sorted((folder / 'shards').glob('*.csv'))], ignore_index=True)
    report = {'rows': len(public), 'segment_ids_unique': bool(public.segment_id.is_unique),
              'no_raw_timestamp_columns': not any('time' in c or 'start_local' in c for c in public.columns),
              'metadata_order_preserved': bool(public[['segment_id', 'vehicle', 'session_index', 'split']].equals(expected[['segment_id', 'vehicle', 'session_index', 'split']])),
              'private_v2_source_row_order_same': bool(private[['vehicle', 'split', 'start_local_unspecified']].equals(old[['vehicle', 'split', 'start_local_unspecified']])),
              'public_numeric_allclose_private': bool(np.allclose(public[numbers], private[numbers], atol=1e-9, rtol=1e-10)),
              'all_shards_match_combined_file': bool(shards.equals(public)),
              'split_counts': public['split'].value_counts().to_dict(),
              'license_snapshot_included': (folder / 'LICENSE.txt').read_bytes() == (root / 'research/public_battery/EV_SOURCE_LICENSE.txt').read_bytes()}
    for key, value in report.items():
        if isinstance(value, bool) and not value:
            raise AssertionError(f'Derivative verification failed: {key}')
    write_json(root / 'outputs/challenge_cup_v3/01_data_audit/derivative_verification.json', report)
    return report


def package_data(root):
    folder = root / 'research/public_battery/data/v3'
    output = root / 'outputs/challenge_cup_v3/01_data_audit'
    schema = json.loads((folder / 'schema.json').read_text(encoding='utf-8'))
    source = json.loads((folder / 'source_manifest.json').read_text(encoding='utf-8'))
    (folder / 'data_summary.csv').write_bytes((output / 'data_summary.csv').read_bytes())
    counts = pd.read_csv(output / 'vehicle_sample_counts.csv')
    counts[['vehicle', 'split', 'retained_sessions']].rename(columns={'retained_sessions': 'sample_count'}).to_csv(folder / 'vehicle_split.csv', index=False)
    descriptions = {
        'soc_start': 'SOC at first observation', 'voltage_start': 'Pack voltage at first observation',
        'voltage_60': 'Pack voltage at 60 s by numpy.interp using prefix observations',
        'voltage_300': 'Pack voltage at 300 s by numpy.interp using prefix observations',
        'voltage_600': 'Pack voltage at 600 s by numpy.interp; last prefix value held if 600 s not observed',
        'current_mean': 'Arithmetic sample mean of current in prefix; charging negative',
        'tmax_mean': 'Arithmetic sample mean of maximum sensor temperature in prefix',
        'temperature_rise': 'Last minus first maximum sensor temperature in prefix',
        'cell_gap_mean': 'Arithmetic sample mean of max minus min cell voltage in prefix',
        'cell_gap_max': 'Maximum observed max minus min cell voltage in prefix'}
    rows = [{'name': f['name'], 'role': 'feature', 'unit': f['unit'], 'definition': descriptions[f['name']],
             'availability': 'observations at elapsed time <= 600 s', 'used_as_predictor': True} for f in schema['features']]
    rows += [{'name': 'proxy_capacity_ah', 'role': 'target', 'unit': 'Ah',
              'definition': schema['target']['formula'], 'availability': 'after full retained session', 'used_as_predictor': False}]
    rows += [{'name': name, 'role': 'metadata', 'unit': '', 'definition': description,
              'availability': 'dataset organization', 'used_as_predictor': False} for name, description in schema['metadata'].items()]
    pd.DataFrame(rows).to_csv(folder / 'feature_dictionary.csv', index=False)
    (folder / 'README.md').write_text('''# V3 公开实车充电衍生数据

20辆车、29,697个充电片段、10个首600秒特征。标签是充电积分/SOC变化计算的容量代理值，不是独立实测SOH。数据处理仅使用真实公开充电观测，不合成缺失工况或失效标签。

## 文件

- `session_features.csv`：完整匿名特征/标签表；`shards/`：20个按车辆分片CSV，可直接合并；不需要Parquet依赖。
- `sample_manifest.csv`：稳定segment_id、匿名vehicle、session_index、固定split。
- `vehicle_split.csv`：逐车划分与样本数；train=001–014、validation=015–016、test=017–020。不得随机按行重新划分。
- `feature_dictionary.csv`、`schema.json`：字段/单位/计算和可用性；metadata和标签不作为输入特征。
- `data_summary.csv`：原始20CSV逐字段完整审计；`source_manifest.json`：来源、原始文件/分片哈希。
- `DATA_AVAILABILITY.md`：真实数据可支持与不能支持的结论；`LICENSE_OR_SOURCE.md`、`LICENSE.txt`：来源引用与许可快照。
- `SHA256SUMS.txt`：本目录其余所有文件的SHA-256（不包含该清单自身）。

公开衍生表移除了原始日期/时刻，只保留每车保留片段的稳定序号。ID稳定性依赖相同源文件哈希、提取器和顺序；不声称不可逆匿名化。原始CSV/RAR不在本目录或Git交付包内。

从仓库根目录重新核验并提取：`python -m research.public_battery.audit_v3 --raw-dir <archives-directory> --csv-dir <csv-directory>`。会读取仓库外原始文件并生成新的V3产物，不修改V2。`--self-test`执行质量/匿名化自检；`--verify-derived`在已完成原始提取的环境中核对私有提取/公开总表/分片/V2顺序。公开表可直接用于V3训练复现，无需原始时间。

前600秒采样均值不是时间加权均值。电压插值仅使用已在前600秒内观测到的点，600秒处无采样时使用最后一个前缀值，不访问未来点。完整片段目标值仅用于监督标签；不得作为在线已知实测容量。
''', encoding='utf-8')
    (folder / 'DATA_AVAILABILITY.md').write_text('''# 数据可用性与事实边界

已获得：20辆公开匿名车辆的真实充电数据、SOC、总电压、电流、最高/最低单体电压、最高/最低温度，以及可重复计算的充电片段容量代理标签。车辆实体隔离划分，原始数据哈希与V2一致。

未获得：独立实测完整容量/SOH真值、失效时间/RUL标签、EIS、放电工况、热失控/故障标签、用户身份、VIN、地点以及已确认的原始时区。不能据此宣称验证真实SOH、RUL、全工况BMS诊断或安全预测。

source available_capacity与available_energy是原始列，不直接认定为独立完整容量真值或可靠标签。当前10个特征不含这两列，不含车辆ID、日期、完整片段持续时间或积分电量。

代理容量受SOC估计、电流传感器误差、分段和充电工况影响。原始质量检查的广范围不是OEM安全阈值；长时间间隔可能反映正常的充电间隔。具体筛选计数和时间问题见 outputs/challenge_cup_v3/01_data_audit/。
''', encoding='utf-8')
    (folder / 'LICENSE_OR_SOURCE.md').write_text(f'''# 来源、许可与引用

下载源：{source['source_url']}

源版本：`{source['source_commit']}`。原作者维护说明：{source['primary_author_url']}。Iontech仅为发现入口，不是此数据的原创发布方。

源下载仓库附MIT许可，本目录保留原文 `LICENSE.txt`（Copyright (c) 2023 Michael Teng）。本说明记录取得时的来源许可，不扩大上游许可范围或提供法律结论。衍生文件附来源、引用及原始哈希；原始压缩包和CSV不重新提交。

论文引用：{source['citation']}

原作者要求使用数据开展研究时引用该论文。车型/规格来自所存官方README快照；模型结果仅适用于本公开充电数据集的代理容量任务。原始哈希、处理器哈希、分片哈希见 `source_manifest.json`，逐文件交付哈希见 `SHA256SUMS.txt`。
''', encoding='utf-8')
    paths = sorted(p for p in folder.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    (folder / 'SHA256SUMS.txt').write_text(''.join(f'{sha256(p)}  {p.relative_to(folder).as_posix()}\n' for p in paths), encoding='utf-8')


def run(raw_dir, csv_dir, root):
    data_dir = root / 'research/public_battery/data/v3'
    output = root / 'outputs/challenge_cup_v3/01_data_audit'
    data_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    (data_dir / 'LICENSE.txt').write_bytes((root / 'research/public_battery/EV_SOURCE_LICENSE.txt').read_bytes())
    old_dir = root / 'research/public_battery/results/ev'
    expected = {x['vehicle']: x for x in json.loads((old_dir / 'raw_manifest.json').read_text(encoding='utf-8'))}
    reference = pd.read_csv(old_dir / 'session_features.csv')
    reference_before = sha256(old_dir / 'session_features.csv')
    audits, raw_manifest, counts, records, summaries = [], [], [], [], []
    for vehicle in range(1, 21):
        csv = csv_dir / f'#{vehicle}.csv'
        archive = raw_dir / f'#{vehicle}.rar'
        hs = {'csv_sha256': sha256(csv), 'archive_sha256': sha256(archive)}
        if any(hs[k] != expected[vehicle][k] for k in hs):
            raise ValueError(f'Raw hash mismatch: vehicle_{vehicle:03d}')
        frame = pd.read_csv(csv, low_memory=False)
        if frame.shape[1] != len(COLS):
            raise ValueError('Source schema changed')
        frame.columns = COLS
        q = quality(frame)
        q['vehicle'] = f'vehicle_{vehicle:03d}'
        audits.append(q)
        found, stats = extract_sessions(frame, vehicle)
        records.extend(found)
        counts.append({'vehicle': q['vehicle'], 'split': split_for(vehicle), **stats})
        raw_manifest.append({'vehicle': q['vehicle'], **hs, 'csv_bytes': csv.stat().st_size,
                             'v2_manifest_match': True})
        for c, v in q['columns'].items():
            summaries.append({'vehicle': q['vehicle'], 'field': c, 'raw_rows': len(frame), **v})
        summaries.append({'vehicle': q['vehicle'], 'field': 'record_time', 'raw_rows': len(frame),
                          'missing_or_non_numeric': q['time']['invalid_rows'], 'missing_rate': q['time']['missing_rate']})
        print(f'{q["vehicle"]}: {len(frame)} raw rows, {len(found)} retained', flush=True)
    fresh = pd.DataFrame(records)
    keys = ['vehicle', 'start_local_unspecified']
    if fresh.duplicated(keys).any() or reference.duplicated(keys).any():
        raise ValueError('Nonunique session key')
    merged = fresh.merge(reference, on=keys, how='outer', suffixes=('_new', '_v2'), indicator=True, validate='one_to_one')
    numeric = ['proxy_capacity_ah', *FEATURES]
    differences = {c: float((merged[c + '_new'] - merged[c + '_v2']).abs().max()) for c in numeric}
    comparison = {'expected_rows': 29697, 'fresh_rows': len(fresh), 'v2_rows': len(reference),
                  'vehicle_count': int(fresh.vehicle.nunique()), 'features': FEATURES,
                  'absolute_tolerance': 1e-9, 'relative_tolerance': 1e-10,
                  'all_keys_match': bool((merged['_merge'] == 'both').all()),
                  'all_splits_match': bool((merged.split_new == merged.split_v2).all()),
                  'numeric_max_abs_difference': differences,
                  'numeric_allclose': all(np.allclose(merged[c + '_new'], merged[c + '_v2'], atol=1e-9, rtol=1e-10) for c in numeric),
                  'v2_cache_sha256': reference_before,
                  'v2_cache_unchanged': sha256(old_dir / 'session_features.csv') == reference_before}
    write_json(output / 'v2_reextraction_comparison.json', comparison)
    if not (len(fresh) == len(reference) == 29697 and fresh.vehicle.nunique() == 20 and
            comparison['all_keys_match'] and comparison['all_splits_match'] and comparison['numeric_allclose'] and comparison['v2_cache_unchanged']):
        raise ValueError('V3/V2 extraction difference; see comparison JSON')
    private = root.parent / 'v3-private'
    private.mkdir(exist_ok=True)
    fresh.to_csv(private / 'session_features.csv', index=False)
    safe = anonymize(fresh)
    safe.to_csv(data_dir / 'session_features.csv', index=False)
    shard_dir = data_dir / 'shards'
    shard_dir.mkdir(exist_ok=True)
    shards = []
    for vehicle, part in safe.groupby('vehicle', sort=True):
        dest = shard_dir / f'{vehicle}.csv'
        part.to_csv(dest, index=False)
        shards.append({'vehicle': vehicle, 'file': f'shards/{vehicle}.csv', 'rows': len(part), 'sha256': sha256(dest)})
    safe[['segment_id', 'vehicle', 'session_index', 'split']].to_csv(data_dir / 'sample_manifest.csv', index=False)
    count_df = pd.DataFrame(counts)
    summary_df = pd.DataFrame(summaries)
    # Search only implementation/dependency manifests, excluding this auditing script itself.
    search = subprocess.run(['rg', '-n', '-i', 'sqlalchemy|sqlite|psycopg|pymysql|mongodb|create table|postgres',
        '--glob', '*.py', '--glob', '*requirements*', '--glob', 'package.json', '--glob', '!audit_v3.py', '.'],
        cwd=root, text=True, capture_output=True)
    if search.returncode not in (0, 1):
        raise RuntimeError('Database dependency scan failed')
    infrastructure = {'method': 'rg source/dependency inspection', 'matches': search.stdout.splitlines(),
                      'scope': '*.py, *requirements*, package.json; excludes audit_v3.py',
                      'conclusion': 'Dataset and file-based processing pipeline; no SQL/database evidence in inspected scope' if search.returncode == 1 else 'Matches require interpretation; not evidence of a deployed database'}
    quality_data = {'scope': 'All 20 CSV files, all parsed rows; raw ordering retained for time checks',
                    'raw_rows_total': int(count_df.raw_rows.sum()), 'retained_sessions': len(safe),
                    'broad_ranges': BROAD_RANGES, 'range_warning': 'Engineering screening bounds only; not safety thresholds or verified anomaly labels. Gap counts can reflect separate charging sessions.',
                    'vehicles': audits, 'infrastructure': infrastructure}
    source = {'source_url': 'https://github.com/shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles',
              'source_commit': '904a336bc4a8de05acdec2598708fd787bbdb8e3',
              'primary_author_url': 'https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles',
              'license': 'MIT; snapshot in research/public_battery/EV_SOURCE_LICENSE.txt',
              'citation': 'Deng Z et al. Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles. Applied Energy 339 (2023), 120954.',
              'origin': 'Real on-road vehicle charging telemetry; target is a derived capacity proxy, not independently measured SOH.',
              'raw_files_committed': False, 'public_vehicle_ids': 'vehicle_001..vehicle_020; source already uses numbered vehicles; no VIN/location available',
              'timestamp_privacy': 'Raw timestamps are excluded from all V3 derivatives. Per-vehicle retained-session ordinal only. No guaranteed irreversible anonymization claimed.',
              'raw_hashes': raw_manifest, 'derived_shards': shards,
              'session_features_sha256': sha256(data_dir / 'session_features.csv'),
              'extractor_sha256': sha256(root / 'research/public_battery/ev_experiment.py')}
    units = ['%', 'V', 'V', 'V', 'V', 'A', 'degC', 'degC', 'V', 'V']
    schema = {'format': 'CSV UTF-8', 'raw_column_mapping': dict(zip(COLS, ['row index', 'YYYYmmddHHMMSS timezone unspecified', 'SOC %', 'pack voltage V', 'charging current A (negative)', 'maximum cell V', 'minimum cell V', 'maximum temperature degC', 'minimum temperature degC', 'available energy source header kw; dimensional meaning unverified', 'available capacity Ah source field; not ground-truth full capacity'])),
              'features': [{'name': c, 'unit': u, 'window': 'first 600 seconds of retained session; interpolation never uses later rows'} for c, u in zip(FEATURES, units)],
              'target': {'name': 'proxy_capacity_ah', 'unit': 'Ah', 'formula': '-trapezoid(current,time_seconds)/3600*100/(SOC_end-SOC_start)', 'interpretation': 'full retained charging-session proxy; unavailable as independent measured SOH ground truth'},
              'metadata': {'segment_id': 'vehicle_###_session_#####; deterministic ordinal under unchanged CSV hashes and extractor', 'vehicle': 'anonymous vehicle ID, not an input feature', 'session_index': '1-based retained-session order per vehicle; not an input feature', 'split': 'fixed vehicle-held-out train/validation/test; not an input feature'},
              'excluded': ['raw timestamps', 'unused', 'energy', 'available_capacity', 'vehicle/session identifiers as predictors', 'full-session duration or integrated charge as predictors'],
              'availability': {'real_vehicle_charging': True, 'measured_SOH': False, 'RUL_or_failure_labels': False, 'EIS': False, 'discharge_telemetry': False, 'thermal_runaway_labels': False, 'source_timezone': 'undocumented'},
              'split': {'train': [f'vehicle_{i:03d}' for i in range(1, 15)], 'validation': ['vehicle_015', 'vehicle_016'], 'test': [f'vehicle_{i:03d}' for i in range(17, 21)]}}
    write_json(data_dir / 'schema.json', schema)
    write_json(data_dir / 'source_manifest.json', source)
    write_json(data_dir / 'split.json', schema['split'])
    write_json(data_dir / 'data_availability.json', schema['availability'])
    write_json(output / 'raw_hash_verification.json', raw_manifest)
    write_json(output / 'environment.json', {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__})
    for dest in (output.parent, output):
        write_json(dest / 'data_quality.json', quality_data)
        count_df.to_csv(dest / 'vehicle_sample_counts.csv', index=False)
        summary_df.to_csv(dest / 'data_summary.csv', index=False)
    totals = {k: int(sum(q['time'][k] for q in audits)) for k in ['invalid_rows', 'duplicate_rows', 'backward_steps', 'zero_intervals', 'gaps_gt_10s']}
    report = f'''# V3 原始数据核验

完整读取 20 辆匿名车辆的 {quality_data['raw_rows_total']:,} 行公开充电 CSV。原始压缩包及 CSV 的 SHA-256 均与 V2 清单一致。数据来源、MIT 许可快照、论文引用和全部哈希保存在 `research/public_battery/data/v3/source_manifest.json`。

本项目是数据集与文件处理流水线。对 Python 源码和依赖清单进行 SQL/数据库依赖只读检索，结果：{infrastructure['conclusion']}。此结论仅覆盖所列检索范围，不宣称已建设数据库。

复用原有 `extract_sessions` 从原始 CSV 重新提取，保留 {len(safe):,} 个充电片段、20 辆车、10 个首 600 秒特征。与 V2 缓存逐车辆/片段匹配，split 一致，标签与全部特征在 atol=1e-9、rtol=1e-10 内一致；最大绝对差 {max(differences.values()):.3g}。V2 缓存未改动。划分固定为 vehicle_001–014 训练、015–016 验证、017–020 测试。

## 质量证据

逐字段缺失率、有限数值范围、无穷值与广范围异常数见 `data_summary.csv`；逐车时间与顺序统计见 `data_quality.json`。时间无效行 {totals['invalid_rows']}，涉及重复时间的行 {totals['duplicate_rows']}，原顺序倒退 {totals['backward_steps']}，相邻零间隔 {totals['zero_intervals']}，大于 10 秒间隔 {totals['gaps_gt_10s']}。时间间隔异常可能是两次充电之间的正常停顿，不直接表示故障。

广范围仅用于数据质量筛查，不是车辆安全阈值、OEM 标定或已标注故障。筛选原样沿用 V2：无效/重复观测形成屏障；间隔大于10秒分段；片段至少1200秒、SOC增量至少20个百分点；SOC不下降且电流均为负；代理容量在(0,250] Ah。详细筛选计数见 `vehicle_sample_counts.csv`。不把原始 available_capacity 列当作独立实测完整容量。

## 可发布衍生数据

`research/public_battery/data/v3/session_features.csv` 和20份 `shards/vehicle_###.csv` 仅含匿名车辆ID、稳定片段ID、片段序号、固定划分、10特征及代理容量。`sample_manifest.csv` 可逐片段追溯到固定源文件哈希和提取器版本，但不发布原始日期/时刻。ID 在相同输入哈希和提取器下稳定；并非不可逆匿名化保证。原始 CSV/RAR 不入 Git，报告不包含本机路径。

标签是完整充电片段电流积分/SOC变化推算的容量代理值，不是独立测得的 SOH；特征仅使用前600秒。没有 RUL、EIS、失效/热失控标签、放电工况或已确认时区。字段、单位、可用性边界和split见 `schema.json`、`data_availability.json` 与 `split.json`。这些缺项不能以合成结果替代。

复现：`python -m research.public_battery.audit_v3 --raw-dir ../ev-data --csv-dir ../ev-csv`。单元自检：`python -m research.public_battery.audit_v3 --self-test`。
'''
    (output.parent / 'data_audit.md').write_text(report, encoding='utf-8')
    (output / 'data_audit.md').write_text(report, encoding='utf-8')
    verify_derivatives(root)
    package_data(root)
    print(json.dumps({'raw_rows': quality_data['raw_rows_total'], 'retained': len(safe), 'time': totals, 'comparison': comparison}, ensure_ascii=False), flush=True)


def self_test():
    f = pd.DataFrame({c: [0, 0, 0, 0] for c in COLS})
    f['record_time'] = ['20200101000010', '20200101000010', '20200101000000', 'invalid']
    f['soc'] = [10, 101, np.nan, 20]
    f['voltage'] = [300, 300, 300, 300]
    q = quality(f)
    assert q['time']['duplicate_rows'] == 2
    assert q['time']['backward_steps'] == 1
    assert q['time']['invalid_rows'] == 1
    assert q['columns']['soc']['missing_or_non_numeric'] == 1
    assert q['columns']['soc']['outside_broad_range'] == 1
    source = pd.DataFrame({'vehicle': [1, 1, 20], 'split': ['train', 'train', 'test'],
                           'start_local_unspecified': ['secret_a', 'secret_b', 'secret_c'],
                           'proxy_capacity_ah': [1., 2., 3.]})
    a = anonymize(source)
    assert a.vehicle.tolist() == ['vehicle_001', 'vehicle_001', 'vehicle_020']
    assert a.session_index.tolist() == [1, 2, 1]
    assert a.segment_id.is_unique
    assert 'start_local_unspecified' not in a
    assert a.equals(anonymize(source))
    all_missing = f.copy()
    all_missing['record_time'] = 'invalid'
    all_missing['current'] = [np.inf, -np.inf, np.nan, 0]
    missing_q = quality(all_missing)
    assert missing_q['time']['duplicate_rows'] == 0
    assert missing_q['time']['positive_interval_max_seconds'] is None
    assert missing_q['columns']['current']['infinite'] == 2
    assert missing_q['columns']['current']['min'] == 0
    assert source.start_local_unspecified.tolist() == ['secret_a', 'secret_b', 'secret_c']
    print('V3 audit self-tests passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path)
    parser.add_argument('--csv-dir', type=Path)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--verify-derived', action='store_true')
    parser.add_argument('--package-data', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.verify_derived:
        print(json.dumps(verify_derivatives(Path(__file__).resolve().parents[2]), indent=2))
    elif args.package_data:
        package_data(Path(__file__).resolve().parents[2])
    else:
        if args.raw_dir is None or args.csv_dir is None:
            parser.error('--raw-dir and --csv-dir are required')
        run(args.raw_dir, args.csv_dir, Path(__file__).resolve().parents[2])
