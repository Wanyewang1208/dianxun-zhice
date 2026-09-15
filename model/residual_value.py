"""Transparent partial-evidence value reference. Missing factors are never imputed."""
from .valuation_config import WEIGHTS,BANDS,DISCLAIMER

def estimate(inputs,soh,rul,safety,assumptions,bms_used=False):
    health=soh['calculated_soh']
    # Do not silently replace the capacity-ratio result with the separately declared professional value.
    health=min(100,max(0,health)) if health is not None else None
    ref=rul.get('reference_cycle_life')
    life=rul['predicted_rul_cycles']/ref*100 if ref else None
    safe=assumptions.get('safety_factor') if safety['status']=='prototype_assumption' else None
    consistent=assumptions.get('consistency_factor')
    scores={'health':health,'life':life,'safety':safe*100 if safe is not None else None,
            'consistency':consistent*100 if consistent is not None else None}
    missing=[k for k,v in scores.items() if v is None]
    lower=sum(WEIGHTS[k]*v for k,v in scores.items() if v is not None)
    upper=lower+sum(WEIGHTS[k]*100 for k in missing)
    blocked=safety['status'] in {'hold_for_professional_review','reported_issue'}
    index=lower if not missing and not blocked else None
    price=inputs.get('new_battery_reference_price');value_range=None
    band=BANDS['validated_bms_core_schema' if bms_used else 'manual_only']
    if price is not None and index is not None:
        midpoint=price
        for v in scores.values():midpoint*=v/100
        value_range={'lower':max(0,midpoint*(1-band)),'upper':min(price,midpoint*(1+band)),
                     'midpoint':midpoint,'band_fraction':band,'unit':'CNY',
                     'kind':'heuristic_sensitivity_band_not_confidence_interval'}
    return {'status':'blocked' if blocked else 'prototype_estimate' if index is not None else 'insufficient_evidence',
            'index':index,'index_bounds':None if blocked else {'lower':lower,'upper':upper,'kind':'mathematical_bounds_for_missing_scores_not_confidence_interval'},
            'missing_components':missing,'component_scores':scores,'weights':WEIGHTS,
            'weighted_contributions':{k:None if v is None else v*WEIGHTS[k] for k,v in scores.items()},
            'estimated_value_range_cny':value_range,'new_battery_reference_price_cny':price,
            'index_formula':'0.35*Health + 0.30*Life + 0.20*Safety + 0.15*Consistency',
            'price_formula':'P_new * (Health/100) * (Life/100) * (Safety/100) * (Consistency/100)',
            'parameter_status':'Prototype Weighting; life/safety/consistency factors explicitly declared Demo assumptions',
            'value_basis':'current_vehicle_use_technical_reference_not_recycling_value',
            'band_basis':'8% with matched schema-valid BMS, otherwise 12%; heuristic only, no calibrated price uncertainty',
            'disclaimer':DISCLAIMER}
