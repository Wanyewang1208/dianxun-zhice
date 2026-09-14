"""Local-only V1 adapter and unchanged V0.3 success contracts."""
import argparse
import json
import os
import logging
import uuid
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from backend.config import ROOT,MAX_BODY_BYTES,load_env
from backend.routes.api import dispatch,POST_PATHS
from backend.services.assessment import NOTICES

def make_server(root=ROOT,host='127.0.0.1',port=8013,allowed_origin=None):
    # Readiness proves actual model loading/inference, not merely file presence.
    try:
        from model.inference import soh,rul
        soh(root,{'battery_id':'B0018','cycle':66});rul(root,{'battery_id':'B0018','cycle':66})
        ready=True
    except Exception:
        logging.exception('Model readiness failed');ready=False
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def cors(self):
            if allowed_origin and self.headers.get('Origin')==allowed_origin:
                self.send_header('Access-Control-Allow-Origin',allowed_origin);self.send_header('Vary','Origin')
        def reply(self,status,data=None,error=None,legacy=False):
            body=data if legacy and error is None else ({'error':error} if legacy else {
                'success':error is None,'code':'OK' if error is None else error['code'],
                'message':'ok' if error is None else error['message'],'data':data if error is None else None,
                'error':error,'request_id':uuid.uuid4().hex,'schema_version':'1.0','warnings':NOTICES})
            encoded=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(encoded)));self.cors();self.end_headers();self.wfile.write(encoded)
        def fail(self,status,code,message):
            return self.reply(status,error={'code':code,'message':message},legacy=self.path.startswith('/v0.3/'))
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/health':return self.reply(200,{'status':'ok','schema_version':'0.3','mode':'local_research_demo'},legacy=True)
            if path in {'/api/v1/health','/api/v1/status'}:
                if not ready:return self.fail(503,'MODEL_UNAVAILABLE','Model readiness failed; inspect server log')
                return self.reply(200,{'status':'ok','mode':'local_research_demo','models_ready':ready,'real_vehicle_validated':False})
            return self.fail(404,'NOT_FOUND','Unknown endpoint')
        def do_OPTIONS(self):
            self.send_response(204);self.cors();self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers','Content-Type');self.end_headers()
        def do_POST(self):
            path=urlsplit(self.path).path
            if path not in POST_PATHS:return self.fail(404,'NOT_FOUND','Unknown endpoint')
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size>MAX_BODY_BYTES:
                    # Drain a bounded near-limit body before closing: unread data can
                    # otherwise reset the connection on Windows, hiding the 413 JSON.
                    self.connection.settimeout(2)
                    remaining=min(size,MAX_BODY_BYTES+65536)
                    try:
                        while remaining:
                            chunk=self.rfile.read(min(65536,remaining))
                            if not chunk:break
                            remaining-=len(chunk)
                    except OSError:pass
                    return self.fail(413,'PAYLOAD_TOO_LARGE','Body exceeds 2 MiB')
                if size<=0:raise ValueError('Nonempty request body required')
                self.connection.settimeout(30)
                raw=self.rfile.read(size)
                if len(raw)!=size:raise ValueError('Incomplete request body')
                content_type=self.headers.get('Content-Type','')
                media=content_type.split(';')[0].strip().lower()
                if media=='application/json':
                    def reject(value):raise ValueError('Non-finite JSON number: '+value)
                    payload=json.loads(raw.decode('utf-8-sig'),parse_constant=reject)
                elif media=='multipart/form-data' and path=='/api/v1/bms/validate':
                    msg=BytesParser(policy=default).parsebytes(('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
                    if not msg.is_multipart():raise ValueError('Invalid multipart boundary')
                    payload={}
                    for part in msg.iter_parts():
                        name=part.get_param('name',header='content-disposition')
                        if name not in {'telemetry','metadata','max_gap_s'} or name in payload:raise ValueError('Unexpected or duplicate multipart field')
                        value=part.get_payload(decode=True).decode('utf-8-sig')
                        key=name+'_csv' if name in {'telemetry','metadata'} else name
                        if key in payload:raise ValueError('Duplicate multipart field')
                        payload[key]=float(value) if key=='max_gap_s' else value
                else:return self.fail(415,'UNSUPPORTED_MEDIA_TYPE','Use application/json; BMS also accepts multipart/form-data')
                result=dispatch(root,path,payload)
                return self.reply(200,result,legacy=path.startswith('/v0.3/'))
            except (ValueError,TypeError,KeyError,UnicodeError) as e:
                return self.fail(400,'INVALID_REQUEST',str(e))
            except FileNotFoundError:
                return self.fail(503,'RESOURCE_UNAVAILABLE','Required bundled data or model file missing')
            except Exception:
                logging.exception('Request failed')
                return self.fail(500,'PROCESSING_FAILED','Inspect server log for dependency or configuration error')
    return ThreadingHTTPServer((host,port),Handler)

def main():
    load_env()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=int(os.getenv('DIANXUN_PORT','8013')))
    p.add_argument('--allowed-origin',default=os.getenv('DIANXUN_ALLOWED_ORIGIN','http://localhost:5173'))
    a=p.parse_args();server=make_server(port=a.port,allowed_origin=a.allowed_origin)
    print(f'DianXun local API: http://127.0.0.1:{a.port}/api/v1/health',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
