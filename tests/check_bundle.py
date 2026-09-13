"""Integration checks against a real rendered bundle: python tests/check_bundle.py PATH."""
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/brick-models/scripts'))
from brick import inspect_bundle,pack,refresh_guide
from bricklib import dumps,sha
source=Path(sys.argv[1]).resolve();manifest=inspect_bundle(source)
with tempfile.TemporaryDirectory() as td:
    t=Path(td);copy=t/'copy';shutil.copytree(source,copy)
    for name in ('a.zip','b.zip'):pack(SimpleNamespace(folder=str(copy),zip=str(t/name)))
    assert sha(t/'a.zip')==sha(t/'b.zip'),'Packaging must be byte reproducible for identical outputs'
    with zipfile.ZipFile(t/'a.zip') as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(manifest['files'])|{'manifest.json'}
    def rejected():
        try:inspect_bundle(copy)
        except ValueError:return
        raise AssertionError('Corrupt bundle was accepted')
    csv=copy/'parts.csv';original=csv.read_bytes();csv.write_bytes(original+b'corrupt\n');rejected();csv.write_bytes(original)
    extra=copy/'unexpected.txt';extra.write_text('unlisted');rejected();extra.unlink()
    p=copy/'instructions/steps.json';old=p.read_bytes();data=json.loads(old);data['steps'][0]['placements'][0]['x']=100;p.write_text(dumps(data))
    # Even a recomputed manifest cannot authorize inconsistent structured steps.
    mf=copy/'manifest.json';saved=mf.read_bytes();edited=json.loads(saved);edited['files']['instructions/steps.json']={'bytes':p.stat().st_size,'sha256':sha(p)};mf.write_text(dumps(edited));rejected();p.write_bytes(old);mf.write_bytes(saved)
    refresh_guide(SimpleNamespace(folder=str(copy),out=str(t/'refreshed')))
    refreshed=inspect_bundle(t/'refreshed')
    for name in manifest['files']:
        if name.endswith('.png'):assert refreshed['files'][name]==manifest['files'][name],'Guide refresh must preserve renders'
print('PASS: real bundle, deterministic ZIPs, corrupt/extra files, inconsistent steps, guide refresh.')
