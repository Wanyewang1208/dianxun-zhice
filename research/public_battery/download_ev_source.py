"""Download the fixed public EV source revision without executing source code."""
import argparse,hashlib,json,subprocess
from pathlib import Path

URL='https://github.com/shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles'
REVISION='904a336bc4a8de05acdec2598708fd787bbdb8e3'

def main():
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    if not a.verify_only:
        if a.destination.exists():raise SystemExit('Destination exists; use --verify-only or select a new external directory')
        subprocess.run(['git','clone','--no-checkout',URL,str(a.destination)],check=True)
        subprocess.run(['git','-C',str(a.destination),'checkout',REVISION],check=True)
    manifest=json.loads(Path('research/public_battery/data/v3/source_manifest.json').read_text())
    for i,record in enumerate(manifest['raw_hashes'],1):
        path=a.destination/f'#{i}.rar'
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['archive_sha256']:raise SystemExit(f'Archive checksum mismatch: {i}')
    print('Verified all 20 source archives. Extract with a RAR-capable tar into a separate external CSV directory; source is read only.')

if __name__=='__main__':main()
