"""Illustrative disposition engine. Feasibility first; no real-vehicle automatic release."""
import json
import math
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from .carbon import calculate

ROUTES=['continue_use','repair_then_use','second_life','recycle']
OBJECTIVES={'carbon':('carbon_kgco2e',-1),'economic':('npv_cny',1),'resource':('recovered_kg',1),'technical':('technical_score',1)}
FLAGS=['critical_event','electrical_pass','thermal_pass','mechanical_pass','post_repair_pass',
       'second_life_approved','recycler_approved','transport_approved']

def finite(x,name,low=None,high=None):
    if isinstance(x,bool) or not isinstance(x,(int,float,np.integer,np.floating)) or not math.isfinite(x):
        raise ValueError(f'{name} must be a finite number')
    if low is not None and x<low or high is not None and x>high:raise ValueError(f'{name} outside permitted range')
    return float(x)

def weights_checked(weights):
    if set(weights)!=set(OBJECTIVES):raise ValueError('Four objective weights are required')
    w={k:finite(v,k,0) for k,v in weights.items()};total=sum(w.values())
    if total<=0:raise ValueError('Weight sum must be positive')
    return {k:v/total for k,v in w.items()}

def safety_gate(scenario,policy):
    if not isinstance(scenario,dict):raise ValueError('scenario must be an object')
    s=scenario.get('safety',{})
    if not isinstance(s,dict):raise ValueError('safety must be an object')
    for key in FLAGS:
        if s.get(key) is not None and type(s[key]) is not bool:raise ValueError(f'{key} must be true, false or null')
    reasons=[]
    if scenario.get('data_kind')!='illustrative':reasons.append('unvalidated_real_data_no_automatic_decision')
    if s.get('critical_event') is True:reasons.append('critical_event_professional_hold')
    elif s.get('critical_event') is None:reasons.append('critical_event_status_unknown')
    try:
        now=datetime.fromisoformat(scenario['assessed_at'].replace('Z','+00:00'))
        inspected=datetime.fromisoformat(scenario['inspection_at'].replace('Z','+00:00'))
        if now.tzinfo is None or inspected.tzinfo is None:raise ValueError('timezone required')
        days=(now-inspected).total_seconds()/86400
        if not 0<=days<=policy['inspection_valid_days']:reasons.append('inspection_expired_or_future')
    except (KeyError,ValueError,TypeError,AttributeError):reasons.append('inspection_time_missing_or_invalid')
    health=scenario.get('health',{})
    if not isinstance(health,dict):raise ValueError('health must be an object')
    soh=health.get('soh_pct');rul=health.get('rul_cycles')
    if soh is not None:finite(soh,'soh_pct',0,120)
    if rul is not None:finite(rul,'rul_cycles',0)
    result={}
    for route in ROUTES:
        rs=list(reasons)
        needed={'continue_use':['electrical_pass','thermal_pass','mechanical_pass'],
            'repair_then_use':['post_repair_pass'],
            'second_life':['electrical_pass','thermal_pass','mechanical_pass','second_life_approved'],
            'recycle':['recycler_approved','transport_approved']}[route]
        for key in needed:
            if s.get(key) is not True:rs.append(key+('_unknown' if s.get(key) is None else '_failed'))
        if route in ('continue_use','repair_then_use'):
            # No assumed SOH recovery from repair: current observed/declared health is used conservatively.
            if soh is None or soh<policy['continue_soh_min']:rs.append('soh_below_demo_service_threshold_or_missing')
            if rul is None or rul<policy['continue_rul_min']:rs.append('rul_below_demo_service_threshold_or_missing')
        if route=='second_life' and (soh is None or soh<policy['second_life_soh_min']):rs.append('soh_below_demo_second_life_threshold_or_missing')
        result[route]={'eligible':not rs,'reason_codes':rs,'gate_scope':'illustrative_policy_not_regulatory_certification'}
    return result

def resource_value(pack_mass_kg,materials,recovery_fraction):
    mass=finite(pack_mass_kg,'pack_mass_kg',0);share=finite(recovery_fraction,'recovery_fraction',0,1)
    ids=[m['material_id'] for m in materials]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate material ID')
    total_fraction=sum(finite(m['mass_fraction'],'mass_fraction',0,1) for m in materials)
    if total_fraction>1+1e-12:raise ValueError('Material fractions exceed pack mass')
    detail=[]
    for m in materials:
        y=finite(m['recovery_yield'],'recovery_yield',0,1);price=finite(m['price_cny_per_kg'],'price',0)
        kg=mass*m['mass_fraction']*y*share
        detail.append({'material_id':m['material_id'],'recovered_kg':kg,'value_cny':kg*price})
    return {'recovered_kg':sum(r['recovered_kg'] for r in detail),'material_value_cny':sum(r['value_cny'] for r in detail),'details':detail}

def npv(cashflows,discount_rate):
    d=finite(discount_rate,'discount_rate',0,1)
    return sum(finite(r['cash_cny'],'cash_cny')/(1+d)**finite(r['year'],'year',0) for r in cashflows)

def pareto_ids(rows):
    if not rows:return []
    vectors=np.array([[finite(r[col],col)*direction for col,direction in OBJECTIVES.values()] for r in rows])
    return [r['route_id'] for i,r in enumerate(rows) if not any(
        np.all(vectors[j]>=vectors[i]-1e-10) and np.any(vectors[j]>vectors[i]+1e-10)
        for j in range(len(rows)) if j!=i)]

def evaluate_routes(config,routes,materials,factors):
    target=finite(config['service_target_kwh'],'service_target_kwh',0)
    horizon=finite(config['horizon_years'],'horizon_years',1)
    if not horizon.is_integer():raise ValueError('horizon_years must be an integer')
    years=int(horizon);out=[]
    if len(routes)!=4 or set(r['route_id'] for r in routes)!=set(ROUTES):raise ValueError('Exactly four unique routes required')
    for r in routes:
        delivered=finite(r['service_kwh'],'service_kwh',0,target)
        uncovered=target-delivered
        for key in ['process_kwh','transport_t_km','loss_kwh','upfront_cost_cny','residual_sale_cny']:
            finite(r[key],key,0)
        finite(r['technical_score'],'technical_score',0,100)
        resources=resource_value(config['pack_mass_kg'],materials,r['recovery_fraction'])
        # Whole-pack quote and recovered-material sale are mutually exclusive revenues.
        if r['revenue_mode'] not in ('whole_pack','materials'):raise ValueError('Invalid revenue_mode')
        if r['revenue_mode']=='whole_pack' and r['recovery_fraction']>0:raise ValueError('Whole-pack sale plus own recovered-material revenue double counts value')
        if r['revenue_mode']=='materials' and r['residual_sale_cny']!=0:raise ValueError('Materials and whole-pack resale cannot both be credited')
        activities=pd.DataFrame([
            {'activity_id':'processing','stage':'end_of_life' if r['route_id']=='recycle' else 'maintenance_transport','quantity':r['process_kwh'],'activity_unit':'kWh','factor_id':'CN_ELECTRICITY_CFP_2024','data_status':'illustrative'},
            {'activity_id':'transport','stage':'maintenance_transport','quantity':r['transport_t_km'],'activity_unit':'t_km','factor_id':'DEMO_ROAD_FREIGHT','data_status':'illustrative'},
            {'activity_id':'battery_losses','stage':'use','quantity':r['loss_kwh'],'activity_unit':'kWh','factor_id':'CN_ELECTRICITY_CFP_2024','data_status':'illustrative'},
            {'activity_id':'replacement_losses','stage':'use','quantity':uncovered*finite(config['replacement_loss_kwh_per_service_kwh'],'replacement losses',0),'activity_unit':'kWh','factor_id':'CN_ELECTRICITY_CFP_2024','data_status':'illustrative'},
            {'activity_id':'replacement_service','stage':'manufacturing','quantity':uncovered,'activity_unit':'kWh_service','factor_id':'DEMO_REPLACEMENT_SERVICE','data_status':'illustrative'}])
        carbon_detail,carbon_summary=calculate(activities,factors,allow_demo=True)
        # Counterfactual service burden fills the same functional service target for every route.
        finite(config['electricity_price_cny_per_kwh'],'electricity price',0)
        finite(config['transport_price_cny_per_t_km'],'transport price',0)
        finite(config['replacement_service_cost_cny_per_kwh'],'replacement cost',0)
        cashflows=[{'year':0,'cash_cny':-r['upfront_cost_cny']-r['process_kwh']*config['electricity_price_cny_per_kwh']-r['transport_t_km']*config['transport_price_cny_per_t_km']}]
        annual=(delivered*finite(config['service_margin_cny_per_kwh'],'service margin',0)-r['loss_kwh']*config['electricity_price_cny_per_kwh']-uncovered*config['replacement_service_cost_cny_per_kwh'])/years
        cashflows.extend({'year':y,'cash_cny':annual} for y in range(1,years+1))
        if r['revenue_mode']=='materials':cashflows.append({'year':0,'cash_cny':resources['material_value_cny']})
        else:cashflows.append({'year':years,'cash_cny':r['residual_sale_cny']})
        out.append({'route_id':r['route_id'],'route_name':r['route_name'],'carbon_kgco2e':carbon_summary['total_kgCO2e'],
            'npv_cny':npv(cashflows,config['discount_rate']),'recovered_kg':resources['recovered_kg'],
            'technical_score':float(r['technical_score']),'service_kwh':delivered,'replacement_service_kwh':uncovered,
            'cashflows':cashflows,'resources':resources,'carbon_detail':carbon_detail.to_dict(orient='records')})
    return out

def rank(scenario,config,rows,weights=None):
    if not isinstance(scenario,dict) or not isinstance(scenario.get('scenario_id'),str) or not scenario['scenario_id'].strip():
        raise ValueError('scenario_id is required')
    w=weights_checked(config['weights'] if weights is None else weights)
    gates=safety_gate(scenario,config['policy'])
    health=scenario.get('health',{})
    capacity_limit=None
    if health.get('rul_unit')=='reference_discharge_cycles' and health.get('soh_pct') is not None and health.get('rul_cycles') is not None:
        capacity_limit=(finite(config['rated_energy_kwh'],'rated_energy_kwh',0)*finite(config['assumed_dod'],'assumed_dod',0,1)
                        *min(health['soh_pct']/100,1)*health['rul_cycles'])
    output=[]
    for row in rows:
        r=dict(row);r.update(gates[r['route_id']]);utilities={}
        r['illustrative_service_limit_kwh']=capacity_limit
        if r['route_id']!='recycle' and (capacity_limit is None or r['service_kwh']>capacity_limit):
            r['eligible']=False
            r['reason_codes']=r['reason_codes']+['declared_service_exceeds_soh_rul_envelope_or_units_missing']
        for name,(column,direction) in OBJECTIVES.items():
            low,high=config['utility_anchors'][name]
            finite(low,'anchor');finite(high,'anchor')
            if high<=low:raise ValueError('Invalid utility anchor range')
            u=float(np.clip((r[column]-low)/(high-low),0,1))
            utilities[name]=u if direction==1 else 1-u
        r['utility_components']=utilities
        r['weighted_score']=sum(w[k]*utilities[k] for k in w) if r['eligible'] else None
        output.append(r)
    feasible=[r for r in output if r['eligible']];frontier=pareto_ids(feasible)
    for r in output:r['pareto_optimal']=r['route_id'] in frontier
    candidates=sorted([r for r in output if r['pareto_optimal']],key=lambda r:(-r['weighted_score'],r['route_id']))
    return {'schema_version':'0.3','scenario_id':scenario['scenario_id'],'data_kind':scenario.get('data_kind'),
        'status':'simulation_recommendation' if candidates else 'hold_for_evidence_or_professional_review',
        'recommended_route':candidates[0]['route_id'] if candidates else None,'feasible_routes':[r['route_id'] for r in feasible],
        'pareto_routes':frontier,'weights':w,'routes':output,
        'functional_unit':config['functional_unit'],'policy_status':'illustrative_not_validated',
        'reason':'Only eligible Pareto routes ranked with declared preference weights' if candidates else 'No route passed all required evidence gates',
        'limitations':['All pathway costs, inventory and suitability assumptions are illustrative',
                       'No validated real-vehicle decision or safety certification','Model SHAP is not a causal degradation explanation']}

def load_inputs(root):
    config=json.loads((root/'data/demo/decision/config.json').read_text(encoding='utf-8'))
    routes=pd.read_csv(root/'data/demo/decision/routes.csv').to_dict(orient='records')
    materials=pd.read_csv(root/'data/demo/decision/materials.csv').to_dict(orient='records')
    factors=pd.read_csv(root/'data/demo/decision/carbon_factors.csv',keep_default_na=False)
    return config,evaluate_routes(config,routes,materials,factors)

def run(root):
    config,rows=load_inputs(root);out=root/'data/demo/results/decision';out.mkdir(parents=True,exist_ok=True)
    scenarios=json.loads((root/'data/demo/decision/scenarios.json').read_text(encoding='utf-8'))
    summary=[]
    for scenario in scenarios:
        result=rank(scenario,config,rows)
        (out/f'{scenario["scenario_id"]}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        for r in result['routes']:
            summary.append({**{k:r[k] for k in ['route_id','route_name','carbon_kgco2e','npv_cny','recovered_kg','technical_score','eligible','weighted_score','pareto_optimal']},
                            'scenario_id':scenario['scenario_id'],'reason_codes':'|'.join(r['reason_codes'])})
    pd.DataFrame(summary).to_csv(out/'route_comparison.csv',index=False,encoding='utf-8-sig')
    sensitivity=[]
    for name,w in config['weight_presets'].items():
        r=rank(scenarios[0],config,rows,w)
        sensitivity.append({'preference':name,'recommended_route':r['recommended_route'],**r['weights']})
    pd.DataFrame(sensitivity).to_csv(out/'preference_sensitivity.csv',index=False,encoding='utf-8-sig')
    print(pd.DataFrame(summary)[['scenario_id','route_id','eligible','weighted_score','pareto_optimal']].to_string(index=False))

if __name__=='__main__':run(Path(__file__).resolve().parents[2])
