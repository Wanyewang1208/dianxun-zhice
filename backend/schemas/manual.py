"""Manual form validation. Null means unknown; no values are filled from placeholders."""
import math
from datetime import datetime, timezone
from backend.schemas.requests import object_fields

TEXT_FIELDS={'vehicle_brand','vehicle_model','battery_brand','region'}
ENUMS={'battery_type':{'LFP','NMC','Other'},'primary_charging_method':{'home_ac','public_ac','dc_fast'}}
BOOL_FIELDS={'fault_code_present','thermal_event_history'}
NUMBERS={
 'rated_capacity_kwh':(0,None),'current_available_capacity_kwh':(0,None),
 'mileage_km':(0,None),'cycle_count':(0,None),'new_battery_reference_price':(0,None),
 'measured_soh':(0,120),'max_cell_voltage_v':(0,10),'min_cell_voltage_v':(0,10),
 'cell_voltage_delta_mv':(0,10000),'current_temperature_c':(-60,150),
 'historical_max_temperature_c':(-60,150),'internal_resistance_mohm':(0,None),
 'fast_charge_ratio':(0,100),'average_daily_mileage_km':(0,None),'annual_mileage_km':(0,None),
 'usual_charge_upper_soc':(0,100),'usual_discharge_lower_soc':(0,100),
 'average_environment_temperature_c':(-60,150),'pack_voltage':(0,2000),
 'pack_current':(-10000,10000),'charge_throughput_kwh':(0,None),'discharge_throughput_kwh':(0,None),
 'registration_year':(1886,None)}
FIELDS=TEXT_FIELDS|set(ENUMS)|BOOL_FIELDS|set(NUMBERS)
TOP={'input_mode','data_kind','battery_id','manual_input','bms','carbon','prototype_assumptions','decision_scenario','weights'}

def number(value,name,low=None,high=None):
    try:
        valid=type(value) in (int,float) and math.isfinite(value)
    except OverflowError:
        valid=False
    if not valid:raise ValueError(name+': finite number required')
    if low is not None and value<low or high is not None and value>high:raise ValueError(name+': please verify this value (outside range)')
    return value

def validate_manual(payload):
    object_fields(payload,TOP,{'input_mode','data_kind','manual_input'})
    if payload['input_mode']!='manual':raise ValueError('input_mode must be manual')
    if payload['data_kind'] not in ('user_declared','demo'):raise ValueError('data_kind must be user_declared or demo')
    if payload.get('battery_id') is not None and (not isinstance(payload['battery_id'],str) or not payload['battery_id'].strip()):
        raise ValueError('battery_id must be a nonempty string or null')
    raw=object_fields(payload['manual_input'],FIELDS,{'rated_capacity_kwh'})
    if raw['rated_capacity_kwh'] is None:raise ValueError('rated_capacity_kwh is required')
    for key,value in raw.items():
        if value is None:continue
        if key in NUMBERS:number(value,key,*NUMBERS[key])
        if key in TEXT_FIELDS and (not isinstance(value,str) or len(value)>200):raise ValueError(key+': text up to 200 characters required')
        if key in ENUMS and (not isinstance(value,str) or value not in ENUMS[key]):raise ValueError(key+': unknown option')
        if key in BOOL_FIELDS and type(value) is not bool:raise ValueError(key+': true, false or null required')
    if raw['rated_capacity_kwh']<=0:raise ValueError('rated_capacity_kwh must be greater than zero')
    if raw.get('cycle_count') is not None and type(raw['cycle_count']) is not int:raise ValueError('cycle_count must be integer')
    if raw.get('registration_year') is not None:
        if type(raw['registration_year']) is not int or raw['registration_year']>datetime.now(timezone.utc).year:
            raise ValueError('registration_year must be integer and not in the future')
    if raw.get('current_available_capacity_kwh') is not None and raw['current_available_capacity_kwh']>raw['rated_capacity_kwh']*1.05:
        raise ValueError('current_available_capacity_kwh exceeds 105% of rated capacity; please verify measurement basis')
    for lower,upper in [('min_cell_voltage_v','max_cell_voltage_v'),('usual_discharge_lower_soc','usual_charge_upper_soc')]:
        if raw.get(lower) is not None and raw.get(upper) is not None and raw[lower]>raw[upper]:raise ValueError(lower+' exceeds '+upper)
    assumptions=payload.get('prototype_assumptions',{})
    object_fields(assumptions,{'reference_cycle_life','safety_factor','consistency_factor'})
    if ('prototype_assumptions' in payload or 'decision_scenario' in payload) and payload['data_kind']!='demo':
        raise ValueError('Prototype assumptions and decision_scenario require data_kind=demo')
    for key,value in assumptions.items():
        if value is None:continue
        number(value,key,0,None if key=='reference_cycle_life' else 1)
        if key=='reference_cycle_life' and value<=0:raise ValueError('reference_cycle_life must be positive')
    if 'weights' in payload and 'decision_scenario' not in payload:raise ValueError('weights requires decision_scenario')
    # Return every supported field so optional unknown values remain explicit in report snapshots.
    return {key:raw.get(key) for key in sorted(FIELDS)},assumptions
