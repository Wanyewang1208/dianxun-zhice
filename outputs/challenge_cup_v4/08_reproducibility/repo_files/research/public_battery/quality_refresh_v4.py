"""Numerically stable threshold audit; no retraining or test-based rule change."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .upgrade_v4 import METHODS, THRESHOLDS, error_metrics, choose_quality_gate, write_json
from .validation_v3 import sha256


def run(out=Path('outputs/challenge_cup_v4')):
    data = pd.read_csv(out/'01_data/window_features.csv.gz')
    predictions = pd.read_csv(out/'03_predictions/all_predictions.csv.gz')
    mdir, vdir = out/'02_metrics', out/'06_verification'
    names = ['formula_coverage.csv', 'matched_formula_comparison.csv', 'quality_coverage.csv']
    before = {}
    for name in names:
        path = mdir/name
        snapshot = vdir/('before_threshold_tolerance_'+name)
        if not snapshot.exists(): snapshot.write_bytes(path.read_bytes())
        before[name] = sha256(snapshot)
    coverage, fair, quality, decisions = [], [], [], []
    for w in [120,300,600]:
        for split in ['validation','test']:
            part = data[(data.window_s==w)&(data.split==split)].copy().set_index('segment_id')
            preds = {}
            for name in METHODS:
                p = predictions[(predictions.group=='primary')&(predictions.window_s==w)&(predictions.split==split)&(predictions.experiment==name)].set_index('segment_id')
                preds[name] = p.loc[part.index,'predicted_ah'].to_numpy()
            preds['prefix_formula'] = part.formula_capacity_ah.to_numpy()
            for threshold in THRESHOLDS:
                enough = part.prefix_soc_gain_pct.to_numpy() >= threshold-1e-9
                mask = enough & np.isfinite(preds['prefix_formula'])
                selected = part[mask]
                coverage.append(dict(window_s=w,split=split,threshold=threshold,n_total=len(part),n_formula=len(selected),coverage=float(mask.mean())))
                if len(selected):
                    for method in METHODS+['prefix_formula']:
                        fair.append(dict(window_s=w,split=split,threshold=threshold,experiment=method,n_total=len(part),coverage=float(mask.mean()),**error_metrics(selected.proxy_capacity_ah,preds[method][mask],selected.vehicle)))
                if w==600 and enough.any():
                    per_cov = part.assign(keep=enough).groupby('vehicle').keep.mean()
                    quality.append(dict(split=split,threshold=threshold,coverage=float(enough.mean()),minimum_vehicle_coverage=float(per_cov.min()),n_total=len(part),n_rejected=int((~enough).sum()),**error_metrics(part.loc[enough,'proxy_capacity_ah'],preds['random_forest'][enough],part.loc[enough,'vehicle'])))
    q = pd.DataFrame(quality)
    threshold = choose_quality_gate(q[q.split=='validation'])
    q['selected_on_validation'] = q.threshold==threshold
    for split in ['validation','test']:
        part = data[(data.window_s==600)&(data.split==split)].copy().set_index('segment_id')
        p = predictions[(predictions.group=='primary')&(predictions.window_s==600)&(predictions.split==split)&(predictions.experiment=='random_forest')].set_index('segment_id').loc[part.index,'predicted_ah']
        keep = part.prefix_soc_gain_pct>=threshold-1e-9
        for status, mask in [('retained',keep),('rejected',~keep)]:
            for vehicle, g in part[mask].groupby('vehicle'):
                if len(g)>=2:
                    decisions.append(dict(split=split,vehicle=vehicle,status=status,threshold=threshold,**error_metrics(g.proxy_capacity_ah,p.loc[g.index],g.vehicle)))
    pd.DataFrame(coverage).to_csv(mdir/names[0],index=False)
    pd.DataFrame(fair).to_csv(mdir/names[1],index=False)
    q.to_csv(mdir/names[2],index=False)
    pd.DataFrame(decisions).to_csv(mdir/'quality_selected_per_vehicle.csv',index=False)
    write_json(vdir/'quality_rule.json',dict(selection_split='validation',threshold_soc_gain_pct=threshold,coverage_constraint=.8,minimum_vehicle_coverage_constraint=.6,comparison_tolerance=1e-9,statement='empirical screen in retrospectively selected long-charging cohort; no deployment, safety or coverage guarantee'))
    write_json(vdir/'analysis_refresh.json',dict(reason='SOC floating point boundary tolerance only; fixed thresholds unchanged; all alternatives retained',tolerance=1e-9,training_rerun=False,code_sha256=sha256(__file__),source_sha256=sha256(out/'01_data/window_features.csv.gz'),before_analysis_sha256=before,after_analysis_sha256={name:sha256(mdir/name) for name in names}))


if __name__=='__main__': run()
