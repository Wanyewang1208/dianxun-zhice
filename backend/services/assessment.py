import io
import json
import pandas as pd
from backend.config import MAX_CSV_ROWS
from backend.schemas.requests import object_fields, model_case, positive_number
from backend.v03.bms_validate import validate
from backend.v03.integration import handle_request
from model.inference import soh, rul
from model.explain_soh import explain_sample
from carbon.calculator import calculate

NOTICES=[
 '比赛 Demo / 原型；尚未完成真实车辆验证，不能替代正式检测报告。',
 'SOH/RUL 预测模型为公开 NASA 电芯数据验证，手动容量比值另行标注；RUL 依赖实测容量和工况，不能解释为剩余天数。',
 'Demo / Prototype Parameters：退役决策权重、安全阈值、价格与路径参数均未经行业验证。',
 'SHAP 解释模型预测贡献，不证明物理衰减因果；公开电芯结果不自动用于电池包决策。',
 '碳因子受年份、地区和系统边界影响，调用方声明的来源不等于独立核验。'
]

def records(frame):
    return json.loads(frame.to_json(orient='records',date_format='iso'))

def bms(payload):
    object_fields(payload,{'telemetry_csv','metadata_csv','max_gap_s'},{'telemetry_csv','metadata_csv'})
    frames=[]
    for field in ['telemetry_csv','metadata_csv']:
        if not isinstance(payload[field],str):raise ValueError(field+' must be UTF-8 CSV text')
        try:frame=pd.read_csv(io.StringIO(payload[field].lstrip('\ufeff')),dtype={'battery_id':str},nrows=MAX_CSV_ROWS+1)
        except (pd.errors.ParserError,pd.errors.EmptyDataError) as e:raise ValueError('Invalid CSV: '+field) from e
        if len(frame)>MAX_CSV_ROWS:raise ValueError('CSV exceeds 10000 rows')
        frames.append(frame)
    gap=positive_number(payload.get('max_gap_s',30),'max_gap_s')
    result=validate(*frames,max_gap_s=gap)
    return {'status':'checked','summary':result['summary'],'detected_columns':list(frames[0].columns),
            **{k:records(result[k]) for k in ['accepted','rejected','issues','normalized_metadata']}}

def carbon(payload):
    object_fields(payload,{'activities','factors','allow_demo'},{'activities','factors'})
    for key in ['activities','factors']:
        if not isinstance(payload[key],list) or not payload[key] or len(payload[key])>10000 or not all(isinstance(x,dict) for x in payload[key]):
            raise ValueError(key+' must be a nonempty array of objects (max 10000)')
    if type(payload.get('allow_demo',False)) is not bool:raise ValueError('allow_demo must be boolean')
    detail,summary=calculate(pd.DataFrame(payload['activities']),pd.DataFrame(payload['factors']),payload.get('allow_demo',False))
    return {'status':'calculated','summary':summary,'details':records(detail),'factor_provenance':'caller_declared_not_independently_verified'}

def decision(root,payload):
    object_fields(payload,{'scenario','weights'},{'scenario'})
    result=handle_request('decision',payload,root)
    return {**result,'parameter_status':'Demo / Prototype Parameters'}

def assessment(root,payload):
    if isinstance(payload,dict) and payload.get('input_mode')=='manual':
        from backend.services.manual_assessment import run
        return run(root,payload)
    object_fields(payload,{'model_case','scenario','weights','bms','carbon'},{'model_case','scenario'})
    case=model_case(payload['model_case'])
    quality=bms(payload['bms']) if 'bms' in payload else {'status':'not_provided','reason':'No BMS CSV supplied'}
    # Quality screening never authorizes cell-to-pack transfer. Case inference uses bundled public data only.
    soh_result=soh(root,case)
    rul_result=rul(root,case)
    explanation=explain_sample(root,**case)
    footprint=carbon(payload['carbon']) if 'carbon' in payload else {'status':'not_provided','reason':'No activity/factor inventory supplied'}
    result=decision(root,{k:payload[k] for k in ['scenario','weights'] if k in payload})
    return {'battery_id':case['battery_id'],'battery_id_scope':'NASA_public_cell_case',
            'scenario_id':result['scenario_id'],'data_quality':quality,'soh':soh_result,'rul':rul_result,
            'explainability':{'status':'available','method':'exact_native_TreeSHAP',**explanation},
            'carbon':footprint,'safety':{'scope':'illustrative_policy_not_certification','gates':[
                {k:r[k] for k in ['route_id','eligible','reason_codes']} for r in result['routes']]},
            'candidate_paths':result['routes'],
            'recommendation':{'status':result['status'],'route_id':result['recommended_route'],
                'parameter_status':result['parameter_status'],'weights':result['weights']},
            'decision_reason':[result['reason']],
            'automatic_model_to_pack_transfer':False,
            'display_notice':'上传 BMS 质量、NASA 电芯推理、示例电池包决策是不同证据域，必须分别展示。',
            'limitations':NOTICES}
