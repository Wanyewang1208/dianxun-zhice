import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 10000

def load_env(root=ROOT):
    path=root/'backend/.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1)
                if k.strip() in {'DIANXUN_PORT','DIANXUN_ALLOWED_ORIGIN'}:
                    os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

