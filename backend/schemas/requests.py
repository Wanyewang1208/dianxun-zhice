"""Strict envelope-level validation; domain validation stays in V0.3 modules."""
import math

def object_fields(value, allowed, required=()):
    if not isinstance(value,dict):raise ValueError('JSON object required')
    extra=set(value)-set(allowed)
    missing=set(required)-set(value)
    if extra:raise ValueError('Unexpected fields: '+', '.join(sorted(extra)))
    if missing:raise ValueError('Missing fields: '+', '.join(sorted(missing)))
    return value

def model_case(payload):
    object_fields(payload,{'battery_id','cycle'},{'battery_id','cycle'})
    if payload['battery_id'] not in {'B0005','B0006','B0007','B0018'}:
        raise ValueError('Only bundled NASA cell IDs supported; no vehicle inference')
    if type(payload['cycle']) is not int or payload['cycle']<1:raise ValueError('cycle must be a positive integer')
    return payload

def positive_number(value,name):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError(name+' must be positive and finite')
    return value

