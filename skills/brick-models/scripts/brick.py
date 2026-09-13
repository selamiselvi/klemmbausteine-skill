#!/usr/bin/env python3
"""Local brick-model pipeline. No network calls or publishing credentials."""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from bricklib import CATALOG, ROOT, VERSION, VIEWS, dumps, ldraw, output_names, parts_csv, read_json, sha, validate

def blender_path(explicit=None):
    choices=[explicit,os.environ.get('BLENDER_BIN'),shutil.which('blender'),'/Applications/Blender.app/Contents/MacOS/Blender']
    for p in choices:
        if p and Path(p).is_file():return str(Path(p).resolve())
    raise ValueError('Blender not found. Install Blender and pass --blender PATH or set BLENDER_BIN.')

def doctor():
    modules={name:importlib.util.find_spec(name) is not None for name in ('reportlab','jsonschema','PIL')}
    try:b=blender_path()
    except ValueError:b=None
    print(dumps({'python':sys.version.split()[0],'dependencies':modules,'blender':b,'ready':all(modules.values()) and bool(b)}))
    return 0 if all(modules.values()) and b else 1

def checked_model(path):
    m=read_json(path);r=validate(m)
    if not r['passed']:raise ValueError('Invalid model:\n'+'\n'.join(r['errors']))
    return m,r

def write_manifest(stage,m,quality):
    files={name:{'bytes':(stage/name).stat().st_size,'sha256':sha(stage/name)} for name in sorted(output_names(m))}
    (stage/'manifest.json').write_text(dumps({'schema_version':'1.0','generator_version':VERSION,'model_id':m['id'],
              'title':m['title'],'author':m['author'],'license':m['license'],'quality':quality,'files':files}))

def finish_images(stage):
    # Composite our freshly rendered transparent studio scene onto the required white canvas.
    from PIL import Image
    for p in stage.rglob('*.png'):
        with Image.open(p) as source:
            rgba=source.convert('RGBA');white=Image.new('RGBA',rgba.size,'white')
            Image.alpha_composite(white,rgba).convert('RGB').save(p)

def inspect_bundle(folder):
    folder=Path(folder).resolve()
    if not folder.is_dir():raise ValueError('Bundle directory missing')
    for p in folder.rglob('*'):
        if p.is_symlink():raise ValueError(f'Symlinks are not allowed: {p.name}')
    m,r=checked_model(folder/'model.json');expected=output_names(m)
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != expected|{'manifest.json'}:raise ValueError(f'Bundle file inventory mismatch: {sorted(actual.symmetric_difference(expected|{"manifest.json"}))}')
    manifest=read_json(folder/'manifest.json')
    if manifest.get('schema_version')!='1.0' or manifest.get('model_id')!=m['id']:raise ValueError('Manifest identity/version mismatch')
    for key in ('title','author','license'):
        if manifest.get(key)!=m[key]:raise ValueError(f'Manifest {key} differs from model')
    if manifest.get('quality') not in ('standard','draft'):raise ValueError('Unknown render quality')
    files=manifest.get('files',{})
    if set(files)!=expected:raise ValueError('Manifest inventory mismatch')
    for name in sorted(expected):
        p=folder/name
        if files[name] != {'bytes':p.stat().st_size,'sha256':sha(p)}:raise ValueError(f'File changed or truncated: {name}')
    if read_json(folder/'catalog.json')!=CATALOG:raise ValueError('Catalog version/content mismatch')
    if (folder/'parts.csv').read_text()!=parts_csv(m):raise ValueError('Parts CSV differs from model')
    if (folder/'model.ldr').read_text()!=ldraw(m):raise ValueError('LDraw differs from model')
    if read_json(folder/'validation.json')!=r:raise ValueError('Validation report differs from independent checks')
    steps=read_json(folder/'instructions/steps.json')
    if steps.get('model_id')!=m['id'] or len(steps.get('steps',[]))!=len(m['steps']):raise ValueError('Step data differs from model')
    from bricklib import inventory
    from guide import placements
    by={p['id']:p for p in m['parts']};view='front-right'
    for n,(s,actual_step) in enumerate(zip(m['steps'],steps['steps']),1):
        view=s.get('view',view)
        expected_step=dict(number=n,title=s['title'],note=s.get('note',''),view=view,image=f'step-{n:03}.png',map=f'map-{n:03}.svg',
                           parts=inventory([by[id] for id in s['parts']]),placements=placements(m,s))
        if actual_step!=expected_step:raise ValueError(f'Step {n} data differs from model')
    from PIL import Image
    for view in VIEWS:
        with Image.open(folder/f'renders/{view}.png') as image:
            size=1200 if manifest['quality']=='standard' else 720
            if image.format!='PNG' or image.size!=(size,size):raise ValueError(f'Invalid render: {view}')
            image.verify()
    for n in range(1,len(m['steps'])+1):
        with Image.open(folder/f'instructions/step-{n:03}.png') as image:
            size=1000 if manifest['quality']=='standard' else 640
            if image.format!='PNG' or image.size!=(size,size):raise ValueError(f'Invalid step image: {n}')
            image.verify()
    if not (folder/'instructions.pdf').read_bytes().startswith(b'%PDF-'):raise ValueError('Invalid PDF signature')
    return manifest

def build(args):
    m,r=checked_model(args.model);blender=blender_path(args.blender)
    out=Path(args.out).expanduser().resolve()
    if out.exists():raise ValueError('Output already exists. Choose a new revision directory.')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.brick-build-',dir=out.parent) as tmp:
        stage=Path(tmp)/'bundle';stage.mkdir();(stage/'renders').mkdir();(stage/'instructions').mkdir()
        for name,value in [('model.json',m),('catalog.json',CATALOG),('validation.json',r)]:
            (stage/name).write_text(dumps(value))
        (stage/'parts.csv').write_text(parts_csv(m));(stage/'model.ldr').write_text(ldraw(m))
        from guide import export_steps,browser,pdf
        steps=export_steps(m,stage)
        print(f'Validated {len(m["parts"])} parts / {len(steps)} steps. Rendering locally with Blender…',flush=True)
        log=Path(tmp)/'render.log'
        with log.open('w') as stream:
            run=subprocess.run([blender,'--background','--python-exit-code','1','--python',str(ROOT/'scripts/render_blender.py'),'--',str(stage/'model.json'),str(stage),args.quality],stdout=stream,stderr=subprocess.STDOUT,timeout=args.timeout)
        if run.returncode:raise ValueError('Blender failed:\n'+'\n'.join(log.read_text(errors='replace').splitlines()[-25:]))
        finish_images(stage)
        browser(m,steps,stage);pdf(m,steps,r,stage)
        write_manifest(stage,m,args.quality)
        inspect_bundle(stage)
        stage.rename(out)
    print(dumps({'output':str(out),'part_count':len(m['parts']),'step_count':len(steps),'warnings':r['warnings'],'guide':str(out/'instructions/index.html')}))

def refresh_guide(args):
    source=Path(args.folder).resolve();old=inspect_bundle(source);m,r=checked_model(source/'model.json')
    out=Path(args.out).expanduser().resolve()
    if out.exists():raise ValueError('Output already exists. Choose a new revision directory.')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.brick-guide-',dir=out.parent) as tmp:
        stage=Path(tmp)/'bundle';shutil.copytree(source,stage)
        from guide import export_steps,browser,pdf
        steps=export_steps(m,stage);browser(m,steps,stage);pdf(m,steps,r,stage)
        write_manifest(stage,m,old['quality']);inspect_bundle(stage);stage.rename(out)
    print(dumps({'output':str(out),'rerendered':False}))

def pack(args):
    folder=Path(args.folder).resolve();inspect_bundle(folder);dest=Path(args.zip).expanduser().resolve()
    if dest.exists():raise ValueError('ZIP already exists; choose another name')
    if dest==folder or folder in dest.parents:raise ValueError('Write the ZIP outside the bundle directory')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='.brick-pack-',suffix='.zip',dir=dest.parent,delete=False) as f:temp=Path(f.name)
    try:
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    info=zipfile.ZipInfo(p.relative_to(folder).as_posix(),date_time=(2026,1,1,0,0,0))
                    info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
                    z.writestr(info,p.read_bytes())
        # Hardlink ensures an existing destination cannot be overwritten by a race.
        os.link(temp,dest)
    finally:temp.unlink(missing_ok=True)
    print(dumps({'zip':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),'published':False}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor');sub.add_parser('catalog')
    p=sub.add_parser('validate');p.add_argument('model')
    p=sub.add_parser('build');p.add_argument('model');p.add_argument('--out',required=True);p.add_argument('--blender');p.add_argument('--quality',choices=['draft','standard'],default='standard');p.add_argument('--timeout',type=int,default=1800)
    p=sub.add_parser('verify');p.add_argument('folder')
    p=sub.add_parser('refresh-guide');p.add_argument('folder');p.add_argument('--out',required=True)
    p=sub.add_parser('pack');p.add_argument('folder');p.add_argument('--zip',required=True)
    a=parser.parse_args()
    try:
        if a.cmd=='doctor':return doctor()
        if a.cmd=='catalog':print(dumps(CATALOG))
        elif a.cmd=='validate':
            r=validate(read_json(a.model));print(dumps(r));return 0 if r['passed'] else 1
        elif a.cmd=='build':build(a)
        elif a.cmd=='pack':pack(a)
        elif a.cmd=='refresh-guide':refresh_guide(a)
        elif a.cmd=='verify':print(dumps(inspect_bundle(a.folder)))
    except (ValueError,OSError,ImportError,subprocess.TimeoutExpired) as e:
        print(f'Error: {e}',file=sys.stderr);return 1
    return 0

if __name__=='__main__':sys.exit(main())
