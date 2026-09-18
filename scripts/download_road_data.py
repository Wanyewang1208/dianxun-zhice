"""Download the author-published 20-EV release, pinned to a commit; never execute upstream code."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '36fef4bd99f626561e2d138a40ccff3d1f3ddfc2'
REPO = 'BatICM/battery-charging-data-of-on-road-electric-vehicles'

def main():
    raw = ROOT / 'data/raw/road_ev'; raw.mkdir(parents=True, exist_ok=True)
    sources = ROOT / 'data/source_notes/road_ev'; sources.mkdir(parents=True, exist_ok=True)
    url = f'https://api.github.com/repos/{REPO}/contents?ref={COMMIT}'
    with urllib.request.urlopen(url, timeout=40) as response: listing = json.load(response)
    selected = [x for x in listing if x['name'].endswith('.rar') or x['name'] in {'README.md','LICENSE','capacity_extract.py','Supplementary materials.pdf'}]
    def download(item):
        name = item['name']; dest = raw / name
        link = item['download_url'].replace('/main/', f'/{COMMIT}/')
        if not dest.exists() or dest.stat().st_size != item['size']:
            with urllib.request.urlopen(link, timeout=90) as response, dest.with_suffix(dest.suffix+'.part').open('wb') as output:
                while block := response.read(1024*1024): output.write(block)
            dest.with_suffix(dest.suffix+'.part').replace(dest)
        assert dest.stat().st_size == item['size'], name
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        print('saved', name, dest.stat().st_size, flush=True)
        return {'file': name, 'bytes':dest.stat().st_size, 'sha256':digest, 'url':link}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: files = list(pool.map(download, selected))
    manifest = {'source_repository':f'https://github.com/{REPO}', 'discovered_via':'https://github.com/shiyunliu-battery/Iontech', 'commit':COMMIT, 'retrieved_utc':datetime.now(timezone.utc).isoformat(), 'files':files}
    (sources/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    for name in ['README.md','LICENSE']:(sources/name).write_bytes((raw/name).read_bytes())
    print('COMPLETE',len(files),flush=True)

if __name__ == '__main__': main()
