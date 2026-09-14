"""Retrieve the original FY08Q4 subset from the archive linked by NASA."""
import argparse
import hashlib
import io
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime,timezone
from pathlib import Path
from .core import CELL_IDS

URL='https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip'
LANDING='https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/'
INNER='5. Battery Data Set/1. BatteryAgingARC-FY08Q4.zip'

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def acquire(root,archive=None):
    raw=root/'data/raw'; raw.mkdir(parents=True,exist_ok=True)
    downloaded=archive is None
    if downloaded:
        archive=root/'data/nasa_archive_download.zip'
        print('Downloading NASA-linked archive (about 210 MB)',flush=True)
        with urllib.request.urlopen(URL,timeout=90) as response,open(archive,'wb') as out:
            shutil.copyfileobj(response,out)
    with zipfile.ZipFile(archive) as outer:
        inner=outer.read(INNER)
    expected=[f'{b}.mat' for b in CELL_IDS]+['README.txt']
    with zipfile.ZipFile(io.BytesIO(inner)) as subset:
        for name in expected:
            (raw/name).write_bytes(subset.read(name))
    manifest={'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
              'official_landing_page':LANDING,'download_url':URL,'archive_sha256':sha256(archive),
              'archive_bytes':archive.stat().st_size,'inner_archive':INNER,
              'inner_sha256':hashlib.sha256(inner).hexdigest(),
              'citation':'B. Saha and K. Goebel (2007), Battery Data Set, NASA Ames PCoE',
              'files':[{'file':n,'bytes':(raw/n).stat().st_size,'sha256':sha256(raw/n)} for n in expected]}
    (raw/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if downloaded: archive.unlink()  # Only this explicitly downloaded temporary file.
    print('Saved four original MAT files, source README and provenance manifest',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--archive',type=Path)
    a=p.parse_args(); acquire(Path(__file__).resolve().parents[2],a.archive)
