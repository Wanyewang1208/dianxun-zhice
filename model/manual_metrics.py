"""Capacity-ratio arithmetic for user-declared inputs, not a trained vehicle model."""

def capacity_soh(inputs):
    rated=inputs['rated_capacity_kwh'];available=inputs.get('current_available_capacity_kwh')
    calculated=available/rated*100 if available is not None else None
    measured=inputs.get('measured_soh')
    return {'status':'calculated' if calculated is not None else 'not_available',
            'calculated_soh':calculated,'measured_soh':measured,
            'difference_pp':calculated-measured if calculated is not None and measured is not None else None,
            'unit':'%','method':'current_available_capacity_kwh / rated_capacity_kwh * 100',
            'evidence_kind':'user_declared_capacity_ratio','predicted_soh_pct':None,
            'measurement_notice':'Compare capacities measured on the same usable-energy, temperature and discharge basis; professional SOH is retained separately',
            'reason':None if calculated is not None else 'current_available_capacity_kwh_missing'}

def manual_rul(inputs,assumptions):
    life=assumptions.get('reference_cycle_life');cycles=inputs.get('cycle_count')
    if life is None or cycles is None:
        return {'status':'not_available','predicted_rul_cycles':None,'reason':'No validated vehicle RUL model for manual form; measured capacity history and compatible validated model required',
                'unit':'cycles','method':None}
    return {'status':'prototype_assumption','predicted_rul_cycles':max(0,life-cycles),
            'reference_cycle_life':life,'unit':'assumed_equivalent_cycles',
            'method':'max(0, explicitly_assumed_reference_cycle_life - cycle_count)',
            'reason':'Demo arithmetic only, not NASA inference or a vehicle life prediction',
            'operating_condition_caution':'No conversion to days or kilometres; cycle definition and conditions are not validated'}
