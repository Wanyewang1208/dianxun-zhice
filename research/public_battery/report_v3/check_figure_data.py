"""Independent numeric and artifact checks for all ten figure source files."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--result', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--verification', type=Path, required=True)
    p.add_argument('--record', action='store_true')
    a = p.parse_args()
    root = a.output / '07_figure_source_data'
    files = sorted(root.glob('*.csv'))
    assert len(files) == 10
    frames = {int(f.name[:2]): pd.read_csv(f) for f in files}
    pred = pd.read_csv(a.result / 'predictions.csv.gz')
    cv = pd.read_csv(a.result / 'group_cv_predictions.csv.gz')
    features = pd.read_csv(a.source)
    verified = []

    def close(actual, expected):
        np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=0)

    def metric_rows(frame):
        for _, row in frame.iterrows():
            group = pred[(pred.experiment == row.experiment) & (pred.seed == row.seed) & (pred.split == row.split)]
            error = group.predicted_ah - group.proxy_capacity_ah
            close(row.mae_ah, abs(error).mean())
            close(row.rmse_ah, np.sqrt(np.mean(error ** 2)))
            close(row.r2, 1 - np.sum(error ** 2) / np.sum((group.proxy_capacity_ah - group.proxy_capacity_ah.mean()) ** 2))
            assert row.n == len(group)

    for _, row in frames[1].iterrows():
        group = features[features.split == row.split]
        assert row.sessions == len(group) and row.vehicles == group.vehicle.nunique()
    verified.append('01: three split vehicle/session counts independently counted from features')
    for number in [2, 5, 7, 8]:
        metric_rows(frames[number])
        verified.append(f'{number:02}: every MAE/RMSE/R2 independently recalculated from matching predictions')
    scatter = frames[3]
    expected = pred[(pred.experiment == 'random_forest') & (pred.split == 'test') & (pred.seed == 42)]
    pd.testing.assert_frame_equal(scatter.reset_index(drop=True), expected.reset_index(drop=True), check_dtype=False, check_exact=False, atol=1e-10, rtol=0)
    verified.append('03: complete RF test scatter data equals prediction records')
    for _, row in frames[4].iterrows():
        group = expected[expected.vehicle == row.vehicle]
        close(row.mae_ah, abs(group.predicted_ah - group.proxy_capacity_ah).mean())
        assert row.sessions == len(group)
    verified.append('04: per-vehicle MAE and session counts recalculated from predictions')
    seeds = frames[5]
    assert sorted(seeds.seed) == [17, 42, 2026]
    close(seeds.mean_mae_ah, seeds.mae_ah.mean())
    close(seeds.sample_sd_mae_ah, seeds.mae_ah.std(ddof=1))
    verified.append('05: three-seed mean and sample SD independently recalculated')
    for _, row in frames[6].iterrows():
        group = cv[(cv.model == row.model) & (cv.fold == row.fold)]
        close(row.mae_ah, abs(group.predicted_ah - group.proxy_capacity_ah).mean())
        folds = frames[6][frames[6].model == row.model]
        assert sorted(folds.fold) == [1, 2, 3, 4, 5]
        close(row.fold_mean_mae_ah, folds.mae_ah.mean())
        close(row.fold_sample_sd_mae_ah, folds.mae_ah.std(ddof=1))
    verified.append('06: all 15 CV fold MAEs and model mean/sample SD recalculated')
    dist = frames[9]
    expected_dist = pred[(pred.split == 'test') & pred.experiment.isin(['train_mean','ridge','random_forest']) & (pred.seed == 42)].copy()
    expected_dist['absolute_error_ah'] = abs(expected_dist.predicted_ah - expected_dist.proxy_capacity_ah)
    pd.testing.assert_frame_equal(dist.reset_index(drop=True), expected_dist.reset_index(drop=True), check_dtype=False, check_exact=False, atol=1e-10, rtol=0)
    verified.append('09: all absolute errors and distribution observations recalculated, no subsampling')
    verification = json.loads(a.verification.read_text(encoding='utf-8'))
    lookup = {v['id']: v for v in verification['checks']}
    for _, row in frames[10].iterrows():
        assert row.passed == (lookup.get(row.check, {}).get('passed') is True)
    verified.append('10: all quality statuses match current external verification records')
    for file in files:
        image = Image.open(a.output / '05_figures_png' / (file.stem + '.png'))
        assert image.size == (1920, 1080)
        close(np.array(image.info['dpi']), np.array([299.9994, 299.9994]))
        svg = (a.output / '06_figures_svg' / (file.stem + '.svg')).read_text(encoding='utf-8')
        assert '<svg' in svg and '<!ENTITY' not in svg
    verified.append('all 10 PNG dimensions/dpi and 10 SVG files checked')
    report = {'passed': True, 'checks': verified, 'figures': 10, 'numeric_tolerance': 1e-10}
    (a.output / '09_reports' / 'figure_numeric_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if a.record:
        verification['checks'] = [c for c in verification['checks'] if c['id'] != 'figures']
        verification['checks'].append({'id':'figures','label':'图表与源数据','passed':True,
            'detail':'独立从逐条预测复算图源 MAE/RMSE/R²、逐车误差、三种子与五折均值/样本SD；核对划分计数、完整散点/ECDF及10组PNG/SVG/CSV'})
        verification['figures_pending'] = False
        a.verification.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__': main()
