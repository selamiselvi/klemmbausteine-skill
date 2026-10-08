"""Shared contract, grid checks and deterministic data exports (no Blender dependency)."""
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'references/catalog.json').read_text())
PARTS, COLORS = CATALOG['parts'], CATALOG['colors']
VIEWS = {'front-right': (1,-1), 'back-right': (1,1), 'back-left': (-1,1), 'front-left': (-1,-1)}
VERSION = '0.2.0'

def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'

def read_json(path):
    p = Path(path)
    if p.stat().st_size > 8_000_000:
        raise ValueError('JSON exceeds 8 MB')
    def unique(pairs):
        result = {}
        for k,v in pairs:
            if k in result:
                raise ValueError(f'Duplicate JSON key: {k}')
            result[k] = v
        return result
    return json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=unique)

def shape(p):
    c = PARTS[p['part']]
    w,d = c['width'], c['depth']
    return (d,w,c['height']) if p['rotation'] == 90 else (w,d,c['height'])

def footprint(p):
    w,d,_ = shape(p)
    return {(x,y) for x in range(p['x'],p['x']+w) for y in range(p['y'],p['y']+d)}

def bbox(model):
    if model.get('schema_version')=='1.1':
        import assembly
        return assembly.bbox(model)
    ps=model['parts']
    return (min(p['x'] for p in ps), min(p['y'] for p in ps), 0,
            max(p['x']+shape(p)[0] for p in ps), max(p['y']+shape(p)[1] for p in ps),
            max(p['z']+shape(p)[2] for p in ps))

def is_v11(model):
    return isinstance(model, dict) and model.get('schema_version') == '1.1'

def validate(model):
    from jsonschema import Draft202012Validator
    schema = 'model-1.1.schema.json' if is_v11(model) else 'model.schema.json'
    errors = [f'{"/".join(map(str,e.path)) or "model"}: {e.message}'
              for e in Draft202012Validator(read_json(ROOT/'references'/schema)).iter_errors(model)]
    report = {'schema_version':'1.0','validator_version':VERSION,'passed':False,'errors':errors,'warnings':[],
              'physical_build':'unverified','visual_review':'unverified',
              'checks':['schema','unique instances','step coverage','body collisions','stud overlap','assembly order','final connectivity'],
              'not_checked':['clutch force','stability and tipping','part/color market availability','full insertion path','underside mechanics']}
    if is_v11(model):
        import assembly
        report.update(schema_version='1.1', validator_version=assembly.VERSION,
                      checks=['schema','unique instances','step coverage','measured part geometry (official LDraw library)',
                              'body collisions (measured boxes)','stud-to-receiver connections in any direction','stud obstruction',
                              'pin/hole, bar/clip and hinge connections (inferred from connector primitives)',
                              'assembly order','top-down insertion of upright pieces','final connectivity',
                              'part/color produced (Rebrickable element records)'],
                      not_checked=['clutch force','stability and tipping','current market stock and price',
                                   'insertion path of sideways pieces','fit and angle of hinge, clip and pin connections',
                                   'collisions finer than the 4 LDU measuring grid'])
    if errors: return report
    ps = model['parts']; by_id = {p['id']:p for p in ps}
    if len(by_id) != len(ps): errors.append('Part instance IDs must be unique')
    ids = [pid for s in model['steps'] for pid in s['parts']]
    for pid in sorted(set(ids)-set(by_id)): errors.append(f'Unknown step part: {pid}')
    for pid in sorted(set(by_id)-set(ids)): errors.append(f'Part not assigned to a step: {pid}')
    for pid,n in Counter(ids).items():
        if n != 1: errors.append(f'Part occurs in {n} steps: {pid}')
    if errors: return report
    if is_v11(model):
        import assembly
        return assembly.validate(model, report)
    cells={}; graph=defaultdict(set); top=defaultdict(list); columns=defaultdict(list); collisions=set()
    for p in ps:
        w,d,h=shape(p)
        for x,y in footprint(p):
            columns[(x,y)].append(p)
            top[(x,y,p['z']+h)].append(p['id'])
            for z in range(p['z'],p['z']+h):
                cell=(x,y,z)
                if cell in cells: collisions.add(tuple(sorted((p['id'],cells[cell]))))
                cells[cell]=p['id']
    for a,b in sorted(collisions): errors.append(f'Body collision: {a} and {b}')
    order={pid:i for i,pid in enumerate(ids)}
    for p in ps:
        area=footprint(p); supported=set(); previous_support=set()
        for x,y in area:
            for below in top[(x,y,p['z'])]:
                graph[p['id']].add(below); graph[below].add(p['id']); supported.add((x,y))
                if order[below] < order[p['id']]: previous_support.add((x,y))
        if p['z'] > 0 and not previous_support:
            errors.append(f'{p["id"]}: no stud connection to an earlier piece below')
        elif p['z'] > 0 and len(previous_support) < len(area):
            report['warnings'].append(f'{p["id"]}: {len(previous_support)}/{len(area)} footprint studs supported at placement; review overhang')
        # An existing brick above blocks vertical placement, even without body collision.
        for x,y in area:
            for other in columns[(x,y)]:
                if order[other['id']] < order[p['id']] and other['z'] >= p['z']+shape(p)[2]:
                    errors.append(f'{p["id"]}: earlier piece {other["id"]} blocks insertion from above')
                    break
            else: continue
            break
    unseen=set(by_id); components=[]
    while unseen:
        todo=[min(unseen)]; seen=set()
        while todo:
            a=todo.pop()
            if a in seen:continue
            seen.add(a);todo.extend(graph[a]-seen)
        unseen-=seen;components.append(sorted(seen))
    if len(components)>1:errors.append(f'Final assembly has {len(components)} disconnected components')
    ground=sum(p['z']==0 for p in ps)
    if ground>1:report['warnings'].append(f'{ground} foundation pieces start loose on the table; keep aligned until tied together')
    report.update(passed=not errors,part_count=len(ps),step_count=len(model['steps']),connection_components=len(components),
                  dimensions_mm=[round(v,1) for v in ((bbox(model)[3]-bbox(model)[0])*8,(bbox(model)[4]-bbox(model)[1])*8,bbox(model)[5]*3.2+1.6)])
    return report

def _names(pid, c):
    if pid in PARTS and c in COLORS:
        return PARTS[pid]['name'], COLORS[c]['name']
    import gridlib
    return gridlib.part_name(pid), gridlib.color_name(c)

def color_hex(code):
    if code in COLORS:
        return COLORS[code]['hex']
    import partdb
    return partdb.color(code)['hex']

def inventory(parts):
    counts=Counter((p['part'],p['color']) for p in parts)
    return [{'part_id':pid,'part_name':_names(pid,c)[0],'color_id':c,'color_name':_names(pid,c)[1],'quantity':n}
            for (pid,c),n in sorted(counts.items())]

def catalog_for(model):
    """Catalog snapshot exported with a bundle: the fixed v1 catalog, or the measured parts/colours a 1.1 model uses."""
    if is_v11(model):
        import assembly
        return assembly.catalog_snapshot(model)
    return CATALOG

def parts_csv(model):
    out=io.StringIO(newline=''); w=csv.DictWriter(out,fieldnames=['part_id','part_name','color_id','color_name','quantity'],lineterminator='\n')
    w.writeheader();w.writerows(inventory(model['parts']));return out.getvalue()

def ldraw(model):
    if is_v11(model):
        import assembly
        pl=assembly.instances(model)
        rows=[f'0 {model["title"]}',f'0 Name: {model["id"]}.ldr',f'0 Author: {model["author"]}',
              '0 // Official LDraw parts; official library required to view.','0 // Coordinates: 20 LDU/stud, 8 LDU/plate.']
        for step in model['steps']:
            rows.append('0 // '+step['title'])
            rows.extend(pl[id].line() for id in step['parts'])
            rows.append('0 STEP')
        return '\n'.join(rows)+'\n'
    rows=[f'0 {model["title"]}',f'0 Name: {model["id"]}.ldr',f'0 Author: {model["author"]}',
          '0 // Upright rectangular parts; official library required to view.', '0 // Coordinates: 20 LDU/stud, 8 LDU/plate.']
    by={p['id']:p for p in model['parts']}
    for step in model['steps']:
        rows.append('0 // '+step['title'])
        for id in step['parts']:
            p=by[id];w,d,h=shape(p)
            # Official regular parts are centered on their TOP body face; LDraw Y points down.
            x=(p['x']+w/2)*20;y=-(p['z']+h)*8;z=(p['y']+d/2)*20
            matrix='1 0 0 0 1 0 0 0 1' if p['rotation']==0 else '0 0 -1 0 1 0 1 0 0'
            rows.append(f'1 {p["color"]} {x:g} {y:g} {z:g} {matrix} {p["part"]}.dat')
        rows.append('0 STEP')
    return '\n'.join(rows)+'\n'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def output_names(model,style='studio'):
    names={'model.json','model.ldr','catalog.json','parts.csv','validation.json','instructions.pdf','instructions/index.html','instructions/steps.json'}
    names.update(f'renders/{v}.png' for v in VIEWS)
    for n in range(1,len(model['steps'])+1):
        names.add(f'instructions/step-{n:03}.png');names.add(f'instructions/map-{n:03}.svg')
    if style=='technical':
        names.update(f'instructions/parts/{p["part_id"]}-{p["color_id"]}.png' for p in inventory(model['parts']))
    return names
