"""One-command local bootstrap. Creates only .venv; never touches frontend."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-install',action='store_true',help='Use current Python with dependencies already installed')
    parser.add_argument('--port',type=int,default=None)
    parser.add_argument('--allowed-origin',default=None)
    args=parser.parse_args()
    python=Path(sys.executable)
    if not args.no_install:
        if sys.version_info[:2] != (3,12):
            parser.error('Use Python 3.12 for the preserved model dependency versions; e.g. py -3.12 scripts/start_backend.py')
        venv=ROOT/'.venv'
        python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if not python.exists():subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
        req=ROOT/'backend/requirements.txt'
        digest=hashlib.sha256(req.read_bytes()).hexdigest()
        stamp=venv/'dianxun-requirements.sha256'
        if not stamp.exists() or stamp.read_text()!=digest:
            subprocess.run([str(python),'-m','pip','install','-r',str(req)],check=True)
            stamp.write_text(digest)
    cmd=[str(python),'-m','backend.app']
    if args.port is not None:cmd+=['--port',str(args.port)]
    if args.allowed_origin is not None:cmd+=['--allowed-origin',args.allowed_origin]
    try:return subprocess.call(cmd,cwd=ROOT)
    except KeyboardInterrupt:return 0

if __name__=='__main__':raise SystemExit(main())

