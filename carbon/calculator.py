"""Auditable activity x factor calculator. No implicit unit conversions or credits."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

STAGES = ['manufacturing','use','maintenance_transport','end_of_life']

def calculate(activities, factors, allow_demo=False):
    req_a={'activity_id','stage','quantity','activity_unit','factor_id'}
    req_f={'factor_id','value','activity_unit','output_unit','status'}
    if not req_a.issubset(activities.columns) or not req_f.issubset(factors.columns):
        raise ValueError('Required activity/factor columns missing')
    if activities.empty or factors.empty: raise ValueError('Empty activity/factor table')
    for frame,key in [(activities,'activity_id'),(factors,'factor_id')]:
        if frame[key].isna().any() or frame[key].astype(str).str.strip().eq('').any() or frame[key].duplicated().any():
            raise ValueError(f'Missing/duplicate {key}')
    if not set(activities.stage).issubset(STAGES): raise ValueError('Unknown lifecycle stage')
    demo_activities=bool(activities.get('data_status',pd.Series(dtype=str)).eq('illustrative').any())
    if demo_activities and not allow_demo:
        raise ValueError('Illustrative activities require --allow-demo')
    rows=[]
    for _,a in activities.iterrows():
        matches=factors[factors.factor_id==a.factor_id]
        if len(matches)!=1: raise ValueError(f'Missing factor: {a.factor_id}')
        f=matches.iloc[0]
        if a.activity_unit!=f.activity_unit or f.output_unit!='kgCO2e':
            raise ValueError(f'Unit mismatch: {a.activity_id}')
        if f.status not in ('official','verified','illustrative'):
            raise ValueError(f'Factor unverified or missing: {a.factor_id}')
        if f.status=='illustrative' and not allow_demo:
            raise ValueError('Illustrative factors require --allow-demo')
        try: q=float(a.quantity); factor=float(f.value)
        except (TypeError,ValueError): raise ValueError('Quantity and factor must be numeric')
        if not np.isfinite(q) or not np.isfinite(factor) or q<0 or factor<0:
            raise ValueError('Quantity/factor must be finite and nonnegative; credits excluded in V0.1')
        row=a.to_dict()
        row.update(factor_value=factor,factor_status=f.status,emissions_kgCO2e=q*factor,
                   factor_source=f.get('source_url',''),factor_year=f.get('year',''))
        rows.append(row)
    detail=pd.DataFrame(rows)
    stages={s:float(detail.loc[detail.stage==s,'emissions_kgCO2e'].sum()) for s in STAGES}
    missing=[s for s in STAGES if s not in set(detail.stage)]
    summary={'total_kgCO2e':float(detail.emissions_kgCO2e.sum()),'by_stage_kgCO2e':stages,
             'included_stages':sorted(set(detail.stage)),'missing_stages':missing,
             'scope_complete':not missing,
             'contains_illustrative_factors':bool((detail.factor_status=='illustrative').any()),
             'contains_illustrative_activities':demo_activities,
             'interpretation':'Illustrative scenario; not verified product footprint' if demo_activities or (detail.factor_status=='illustrative').any()
                              else 'Activity-based calculation; factor/activity applicability still requires review',
             'allocation':'Cut-off at end-of-life; no avoided-burden or recycling credits; electricity attribution follows activity description and declared functional unit'}
    return detail,summary

def main():
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activities',type=Path,default=root/'carbon/factors/example_activities.csv')
    p.add_argument('--factors',type=Path,default=root/'carbon/factors/carbon_factors.csv')
    p.add_argument('--output',type=Path,default=root/'data/demo/results/carbon')
    p.add_argument('--allow-demo',action='store_true')
    a=p.parse_args()
    detail,summary=calculate(pd.read_csv(a.activities),pd.read_csv(a.factors),a.allow_demo)
    a.output.mkdir(parents=True,exist_ok=True)
    detail.to_csv(a.output/'carbon_detail.csv',index=False,encoding='utf-8-sig')
    (a.output/'carbon_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
