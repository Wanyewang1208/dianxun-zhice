"""Independent V0.3 attribution and scenario arithmetic acceptance checks."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

def verify(root):
    checks=[]
    def check(ok,name):
        if not bool(ok):raise AssertionError(name)
        checks.append(name)
    shap=pd.read_csv(root/'data/demo/results/shap/shap_values.csv')
    meta=json.loads((root/'data/demo/results/shap/method.json').read_text())
    cols=['shap__'+f for f in meta['features']]
    check(len(shap)==132 and not shap.duplicated(['battery_id','cycle']).any(),'132 distinct held-out SHAP samples')
    check(np.allclose(shap[cols].sum(axis=1)+shap.base_value_soh_pct,shap.predicted_soh_pct,atol=1e-4,rtol=0),'SHAP additive reconstruction from exported CSV')
    check(hashlib.sha256((root/'model/xgboost.joblib').read_bytes()).hexdigest()==meta['model_sha256'],'Explained model SHA256')
    old=pd.read_csv(root/'data/demo/results/soh/holdout_predictions.csv');old=old[old.model=='xgboost']
    joined=shap.merge(old,on=['battery_id','cycle'],suffixes=('_shap','_old'),validate='one_to_one')
    check(len(joined)==132 and np.allclose(joined.predicted_soh_pct_shap,joined.predicted_soh_pct_old,atol=1e-4,rtol=0),'No model prediction change during explanation')
    imp=pd.read_csv(root/'data/demo/results/shap/global_importance.csv').set_index('feature')
    check(all(np.isclose(shap['shap__'+f].abs().mean(),imp.loc[f,'mean_abs_shap_pp'],atol=1e-5) for f in meta['features']),'Global SHAP ranking reproduced')
    for cycle in [30,66,100]:
        case=json.loads((root/f'data/demo/results/shap/B0018_cycle_{cycle}.json').read_text())
        check(abs(case['base_value_soh_pct']+sum(r['shap_soh_pp'] for r in case['contributions'])-case['predicted_soh_pct'])<1e-4,f'Local explanation {cycle} reconstructed')
    config=json.loads((root/'data/demo/decision/config.json').read_text(encoding='utf-8'))
    routes=pd.read_csv(root/'data/demo/decision/routes.csv').set_index('route_id')
    materials=pd.read_csv(root/'data/demo/decision/materials.csv')
    factors=pd.read_csv(root/'data/demo/decision/carbon_factors.csv').set_index('factor_id').value
    main=json.loads((root/'data/demo/results/decision/DEMO_ALL_EVIDENCE.json').read_text(encoding='utf-8'))
    for row in main['routes']:
        r=routes.loc[row['route_id']];missing=config['service_target_kwh']-r.service_kwh
        expected_carbon=(r.process_kwh+r.loss_kwh+missing*config['replacement_loss_kwh_per_service_kwh'])*factors.CN_ELECTRICITY_CFP_2024+r.transport_t_km*factors.DEMO_ROAD_FREIGHT+missing*factors.DEMO_REPLACEMENT_SERVICE
        check(np.isclose(expected_carbon,row['carbon_kgco2e']),f'Independent carbon functional-unit arithmetic {r.name}')
        mass=config['pack_mass_kg']*materials.mass_fraction*materials.recovery_yield*r.recovery_fraction
        check(np.isclose(mass.sum(),row['recovered_kg']),f'Resource mass balance {r.name}')
        check(np.isclose((mass*materials.price_cny_per_kg).sum(),row['resources']['material_value_cny']),f'Resource value {r.name}')
        initial=-r.upfront_cost_cny-r.process_kwh*config['electricity_price_cny_per_kwh']-r.transport_t_km*config['transport_price_cny_per_t_km']
        annual=(r.service_kwh*config['service_margin_cny_per_kwh']-r.loss_kwh*config['electricity_price_cny_per_kwh']-missing*config['replacement_service_cost_cny_per_kwh'])/config['horizon_years']
        expected_npv=initial+sum(annual/(1+config['discount_rate'])**year for year in range(1,config['horizon_years']+1))
        expected_npv+=(mass*materials.price_cny_per_kg).sum() if r.revenue_mode=='materials' else r.residual_sale_cny/(1+config['discount_rate'])**config['horizon_years']
        check(np.isclose(expected_npv,row['npv_cny']),f'Independent cashflow NPV {r.name}')
        check(np.isclose(r.service_kwh+row['replacement_service_kwh'],config['service_target_kwh']),f'Equal delivered service {r.name}')
    check(main['recommended_route']=='repair_then_use','Balanced illustrative scenario outcome')
    check(not next(r for r in main['routes'] if r['route_id']=='second_life')['pareto_optimal'],'Dominated route excluded from Pareto set')
    for name in ['DEMO_MISSING_EVIDENCE','DEMO_CRITICAL_HOLD']:
        case=json.loads((root/f'data/demo/results/decision/{name}.json').read_text(encoding='utf-8'))
        check(case['recommended_route'] is None and not case['feasible_routes'],f'Global hold outcome {name}')
        check(all(r['weighted_score'] is None for r in case['routes']),f'No score for excluded routes {name}')
    pending=json.loads((root/'data/demo/results/decision/DEMO_REPAIR_PENDING.json').read_text(encoding='utf-8'))
    check('repair_then_use' not in pending['feasible_routes'],'Missing repair evidence cannot be bypassed by high score')
    low=json.loads((root/'data/demo/results/decision/DEMO_LOW_RUL.json').read_text(encoding='utf-8'))
    check(low['feasible_routes']==['recycle'],'Low RUL blocks infeasible claimed service')
    sensitivity=pd.read_csv(root/'data/demo/results/decision/preference_sensitivity.csv').set_index('preference')
    check(sensitivity.loc['resource_priority','recommended_route']=='recycle','Resource preference changes recommendation')
    report=json.loads((root/'data/demo/results/integration/example_report.json').read_text(encoding='utf-8'))
    check(report['automatic_model_to_pack_transfer'] is False,'No automatic laboratory-to-pack transfer')
    check(report['scenario_decision']['policy_status']=='illustrative_not_validated','Simulation policy status preserved in integration output')
    summary={'checks_passed':len(checks),'checks':checks,'scope':'Attribution, unchanged prediction, equal functional service, independent cashflow/material/carbon arithmetic, gate outcomes and API evidence labels'}
    (root/'data/demo/results/verification_v03.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(f'{len(checks)} V0.3 acceptance checks passed')

if __name__=='__main__':verify(Path(__file__).resolve().parents[2])
