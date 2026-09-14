"""Local JSON integration service. Start manually; no frontend or external publishing."""
import argparse
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from .integration import handle_request

def make_server(root,host='127.0.0.1',port=8013,allowed_origin=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,code,body):
            encoded=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
            self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(encoded)))
            if allowed_origin and self.headers.get('Origin')==allowed_origin:
                self.send_header('Access-Control-Allow-Origin',allowed_origin)
                self.send_header('Vary','Origin')
            self.end_headers();self.wfile.write(encoded)
        def do_GET(self):
            if self.path=='/health':return self.reply(200,{'status':'ok','schema_version':'0.3','mode':'local_research_demo'})
            self.reply(404,{'error':{'code':'not_found','message':'Unknown endpoint'}})
        def do_OPTIONS(self):
            self.send_response(204)
            if allowed_origin and self.headers.get('Origin')==allowed_origin:
                self.send_header('Access-Control-Allow-Origin',allowed_origin)
                self.send_header('Access-Control-Allow-Methods','POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers','Content-Type')
                self.send_header('Vary','Origin')
            self.end_headers()
        def do_POST(self):
            action={'/v0.3/explain':'explain','/v0.3/decision':'decision','/v0.3/report':'report'}.get(self.path)
            if action is None:return self.reply(404,{'error':{'code':'not_found','message':'Unknown endpoint'}})
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                return self.reply(415,{'error':{'code':'content_type','message':'application/json required'}})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1048576:raise ValueError('JSON body must be 1..1048576 bytes')
                def reject_constant(value):raise ValueError('Non-finite JSON number: '+value)
                payload=json.loads(self.rfile.read(size),parse_constant=reject_constant)
                result=handle_request(action,payload,root)
                return self.reply(200,result)
            except (ValueError,TypeError,KeyError,UnicodeError) as e:
                return self.reply(400,{'error':{'code':'invalid_request','message':str(e)}})
            except Exception:
                return self.reply(500,{'error':{'code':'processing_failed','message':'Check installed dependencies and bundled data/configuration'}})
    return ThreadingHTTPServer((host,port),Handler)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8013)
    p.add_argument('--allowed-origin',default=None,help='Exact local frontend origin, e.g. http://localhost:3000')
    a=p.parse_args();server=make_server(Path(__file__).resolve().parents[2],port=a.port,allowed_origin=a.allowed_origin)
    print(f'Local V0.3 API: http://127.0.0.1:{a.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
