"""Manual form orchestration with separate declared, checked and assumed evidence."""
import copy
from backend.schemas.manual import validate_manual
from model.manual_metrics import capacity_soh,manual_rul
from model.residual_value import estimate

CONDITION={'max_cell_voltage_v','min_cell_voltage_v','cell_voltage_delta_mv','current_temperature_c',
 'historical_max_temperature_c','internal_resistance_mohm','fault_code_present','thermal_event_history',
 'pack_voltage','pack_current','charge_throughput_kwh','discharge_throughput_kwh'}
BMS_MAP={'cell_voltage_max':'max_cell_voltage_v','cell_voltage_min':'min_cell_voltage_v',
 'temperature_max':'current_temperature_c','pack_voltage':'pack_voltage','pack_current':'pack_current'}

def safety_screen(inputs,kind,assumptions):
    # Conservative prototype review triggers, not certified chemistry-specific limits.
    abnormal=[]
    for key in ['current_temperature_c','historical_max_temperature_c']:
        if inputs.get(key) is not None and (inputs[key]<0 or inputs[key]>60):abnormal.append(key+'_prototype_review_trigger')
    if inputs.get('cell_voltage_delta_mv') is not None and inputs['cell_voltage_delta_mv']>200:
        abnormal.append('cell_voltage_delta_prototype_review_trigger')
    if abnormal:return {'status':'hold_for_professional_review','reason_codes':abnormal,'certified':False}
    if inputs.get('thermal_event_history') is True:
        return {'status':'hold_for_professional_review','reason_codes':['reported_thermal_event'],
                'certified':False,'action':'Professional inspection and safe handling review; no automatic route release'}
    if inputs.get('fault_code_present') is True:
        return {'status':'reported_issue','reason_codes':['reported_battery_fault_code'],'certified':False}
    if kind=='demo' and assumptions.get('safety_factor')==0:
        return {'status':'hold_for_professional_review','reason_codes':['demo_safety_factor_zero'],'certified':False}
    if any(inputs.get(k) is None for k in ['thermal_event_history','fault_code_present']):
        return {'status':'unknown','reason_codes':['safety_history_incomplete'],'certified':False}
    if kind=='demo' and assumptions.get('safety_factor') is not None and assumptions['safety_factor']>0:
        return {'status':'prototype_assumption','reason_codes':['explicit_demo_safety_factor_not_inspection'],'certified':False}
    return {'status':'unknown','reason_codes':['self_report_is_not_professional_safety_clearance'],'certified':False}

def run(root,payload):
    # Deferred import avoids a service cycle while preserving the existing endpoint helpers.
    from backend.services.assessment import bms,carbon,decision,NOTICES
    inputs,assumptions=validate_manual(payload)
    condition={k:inputs.get(k) for k in sorted(CONDITION)}
    sources={k:'manual_input' if v is not None else 'missing' for k,v in condition.items()}
    quality=bms(payload['bms']) if 'bms' in payload else {'status':'not_provided'}
    used=False;notes=[];selected_id=payload.get('battery_id')
    if quality['status']=='checked':
        accepted=quality['accepted'];ids={str(r['battery_id']) for r in accepted}
        if selected_id is None and len(ids)==1:selected_id=next(iter(ids))
        matching=[r for r in accepted if str(r['battery_id'])==selected_id]
        if quality['summary']['schema_ready'] and matching:
            row=max(matching,key=lambda r:r['timestamp'])
            for source,target in BMS_MAP.items():
                condition[target]=row[source];sources[target]='bms_latest_accepted'
            used=True
            notes.append('BMS max temperature is latest accepted snapshot maximum, not historical maximum')
        else:notes.append('BMS not used: core quality errors, ambiguous battery IDs, or selected ID mismatch')
        quality['accepted_row_fraction']=quality['summary']['accepted_rows']/quality['summary']['input_rows'] if quality['summary']['input_rows'] else 0
    if condition['max_cell_voltage_v'] is not None and condition['min_cell_voltage_v'] is not None:
        delta=(condition['max_cell_voltage_v']-condition['min_cell_voltage_v'])*1000
        if used or condition['cell_voltage_delta_mv'] is None:
            condition['cell_voltage_delta_mv']=delta;sources['cell_voltage_delta_mv']='bms_voltage_difference' if used else 'calculated_from_manual_voltages'
        elif abs(delta-condition['cell_voltage_delta_mv'])>1:
            notes.append('Declared cell voltage delta differs from max/min calculation; original values retained for review')
    soh=capacity_soh(inputs);life=manual_rul(inputs,assumptions)
    screen_condition=dict(condition)
    if condition['max_cell_voltage_v'] is not None and condition['min_cell_voltage_v'] is not None:
        screen_condition['cell_voltage_delta_mv']=max(condition['cell_voltage_delta_mv'] or 0,(condition['max_cell_voltage_v']-condition['min_cell_voltage_v'])*1000)
    safety=safety_screen(screen_condition,payload['data_kind'],assumptions)
    footprint=carbon(payload['carbon']) if 'carbon' in payload else {'status':'not_provided','reason':'Explicit activities and factors required; mileage/region do not determine lifecycle footprint'}
    paths=[{'route_id':rid,'eligible':False,'weighted_score':None,'reason_codes':['manual_data_no_validated_route_clearance']} for rid in ['continue_use','repair_then_use','second_life','recycle']]
    recommendation={'status':'hold_for_evidence_or_professional_review','route_id':None,'parameter_status':'Demo / Prototype Parameters'}
    reasons=['Manual records are insufficient for automatic whole-vehicle disposition']
    if 'decision_scenario' in payload:
        scenario=copy.deepcopy(payload['decision_scenario'])
        if not isinstance(scenario,dict):raise ValueError('decision_scenario must be an object')
        if scenario.get('data_kind')!='illustrative':raise ValueError('decision_scenario.data_kind must be illustrative')
        scenario['health']={'soh_pct':soh['calculated_soh'],'rul_cycles':life['predicted_rul_cycles'],
                            'rul_unit':'assumed_equivalent_cycles' if life['status']=='prototype_assumption' else None}
        if not isinstance(scenario.get('safety',{}),dict):raise ValueError('decision_scenario.safety must be an object')
        scenario.setdefault('safety',{})
        if safety['status'] in {'hold_for_professional_review','reported_issue'}:scenario['safety']['critical_event']=True
        elif safety['status']=='unknown':scenario['safety']['critical_event']=None
        result=decision(root,{'scenario':scenario,**({'weights':payload['weights']} if 'weights' in payload else {})})
        paths=result['routes'];reasons=[result['reason']]
        recommendation={'status':result['status'],'route_id':result['recommended_route'],'parameter_status':result['parameter_status']}
        current_path=next(r for r in paths if r['route_id']=='continue_use')
        if not current_path['eligible']:
            safety={**safety,'status':'hold_for_professional_review',
                    'reason_codes':safety['reason_codes']+['current_use_gate_not_passed']+current_path['reason_codes']}
    residual=estimate(inputs,soh,life,safety,assumptions,used)
    second_life={'status':'not_available','level':None,'reason':'No validated second-life qualification or valuation from manual inputs'}
    if any(r['route_id']=='second_life' and r['eligible'] for r in paths):
        second_life={'status':'prototype_scenario','level':'candidate','reason':'Eligible only under supplied illustrative scenario; not a market value or engineering approval'}
    return {'battery_id':selected_id,'battery_id_scope':'manual_or_matching_bms_identifier','input_mode':'manual',
            'data_kind':payload['data_kind'],'input_snapshot':inputs,'effective_condition':condition,'field_sources':sources,
            'prototype_assumptions':assumptions,'data_quality':{'manual':'schema_valid_user_declared','bms':quality,'bms_used_for_condition':used,'notes':notes},
            'soh':soh,'rul':life,'explainability':{'status':'not_available','reason':'Capacity ratio is arithmetic; NASA SHAP is not applicable to this vehicle form','formula':soh['method']},
            'carbon':footprint,'safety':safety,'residual_value':residual,'current_use_value':residual['estimated_value_range_cny'],
            'second_life_potential':second_life,'candidate_paths':paths,'recommendation':recommendation,'decision_reason':reasons,
            'automatic_model_to_pack_transfer':False,
            'field_usage':{'calculation':['rated_capacity_kwh','current_available_capacity_kwh'],
              'separate_measurement':['measured_soh'],'safety_screen':['fault_code_present','thermal_event_history','current_temperature_c','historical_max_temperature_c','cell_voltage_delta_mv'],
              'demo_calculation':['cycle_count','new_battery_reference_price'],
              'retained_only':['vehicle_brand','vehicle_model','registration_year','battery_brand','battery_type','mileage_km','region',
                 'internal_resistance_mohm','fast_charge_ratio','average_daily_mileage_km','annual_mileage_km','primary_charging_method',
                 'usual_charge_upper_soc','usual_discharge_lower_soc','average_environment_temperature_c',
                 'charge_throughput_kwh','discharge_throughput_kwh']},
            'display_notice':'Capacity SOH uses user-declared energy; optional Demo RUL/value assumptions are not trained vehicle predictions. Blank outputs mean evidence is missing.',
            'limitations':NOTICES+[residual['disclaimer']]}
