from backend.schemas.requests import model_case
from backend.services import assessment as services
from backend.v03.integration import handle_request
from model.inference import soh,rul
from model.explain_soh import explain_sample

POST_PATHS={'/api/v1/bms/validate','/api/v1/soh','/api/v1/rul','/api/v1/explain','/api/v1/carbon','/api/v1/decision','/api/v1/assessment',
 '/v0.3/explain','/v0.3/decision','/v0.3/report'}

def dispatch(root,path,payload):
    if path.startswith('/v0.3/'):return handle_request(path.rsplit('/',1)[1],payload,root)
    if path=='/api/v1/bms/validate':return services.bms(payload)
    if path=='/api/v1/soh':return soh(root,model_case(payload))
    if path=='/api/v1/rul':return rul(root,model_case(payload))
    if path=='/api/v1/explain':return {'status':'available',**explain_sample(root,**model_case(payload))}
    if path=='/api/v1/carbon':return services.carbon(payload)
    if path=='/api/v1/decision':return services.decision(root,payload)
    if path=='/api/v1/assessment':return services.assessment(root,payload)
    raise KeyError('Unknown endpoint')
