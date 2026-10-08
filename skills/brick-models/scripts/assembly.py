"""Format 1.1 assembly engine: official parts on the stud grid or placed freely in any of the 24 axis-aligned orientations.

A part is placed either on the grid (`x`, `y`, `z`, `rotation`, see gridlib) or freely with `pos` (LDraw units, LDraw
axes, -Y up) and `matrix` (a 3x3 rotation whose entries are -1, 0 or 1). Every part brings the measurements of
ldraw.analyze3d(): collision boxes and connectors. The checks:

- collisions between body boxes (studs excluded, stud cavities open), with a 0.6 LDU tolerance;
- stud ↔ receiver connections in any direction (sideways building), studs blocked by a body without a receiver;
- Technic pin/axle ↔ hole, bar ↔ clip and hinge finger ↔ finger connections, inferred from the library's connector
  primitives and reported separately because their fit is not modelled;
- every piece joins an earlier piece (pieces resting on the table excepted), top-down insertion for upright grid pieces,
  one connected assembly, and produced colours.
"""
import itertools
import math
from collections import defaultdict

import gridlib
import ldraw
import partdb

VERSION = '0.3.0'
TOL = 0.6


def _orientations():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = [0] * 9
            for r in range(3):
                m[r * 3 + perm[r]] = signs[r]
            det = (m[0] * (m[4] * m[8] - m[5] * m[7]) - m[1] * (m[3] * m[8] - m[5] * m[6]) + m[2] * (m[3] * m[7] - m[4] * m[6]))
            if det == 1:
                out.append(tuple(m))
    return out


ORIENTATIONS = _orientations()


def mul(m, v):
    return (m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2], m[6] * v[0] + m[7] * v[1] + m[8] * v[2])


def matmul(a, b):
    return tuple(sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3)) for r in range(3) for c in range(3))


def transpose(m):
    return (m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8])


class Instance:
    """One placed part in model space (LDraw units and axes)."""

    def __init__(self, p):
        self.p = p
        if 'matrix' in p:
            self.m = tuple(int(v) for v in p['matrix'])
            if self.m not in ORIENTATIONS:
                raise ValueError(f'{p["id"]}: matrix must be one of the 24 axis-aligned rotations (entries -1/0/1, determinant +1)')
            self.t = tuple(float(v) for v in p['pos'])
            self.grid = None
        else:
            self.grid = gridlib.Placed(p)
            b = self.grid.ldraw_line().split()
            self.t = tuple(float(v) for v in b[2:5]); self.m = tuple(int(float(v)) for v in b[5:14])
        a = ldraw.analyze3d(p['part'])
        if not a['boxes']:
            raise ValueError(f'{p["id"]}: part {p["part"]} has no measurable body ({a.get("reason", "unsupported")})')
        self.a = a
        self.boxes = []
        for b in a['boxes']:
            c1 = self.apply(b[:3]); c2 = self.apply(b[3:])
            self.boxes.append(tuple(min(c1[k], c2[k]) for k in range(3)) + tuple(max(c1[k], c2[k]) for k in range(3)))
        self.connectors = []
        for c in a['connectors']:
            w = dict(c, pos=self.apply(c['pos']), axis=tuple(round(v, 3) for v in mul(self.m, c['axis'])))
            if 'end' in c:
                w['end'] = self.apply(c['end'])
            self.connectors.append(w)
        self.upright = self.m in (gridlib.ROT[r] for r in (0, 90, 180, 270))

    def apply(self, v):
        r = mul(self.m, v)
        return tuple(round(r[k] + self.t[k], 3) for k in range(3))

    def line(self):
        m = ' '.join(f'{v:g}' for v in self.m)
        return f'1 {self.p["color"]} {self.t[0]:g} {self.t[1]:g} {self.t[2]:g} {m} {self.p["part"]}.dat'

    def extent(self):
        return (min(b[0] for b in self.boxes), min(b[1] for b in self.boxes), min(b[2] for b in self.boxes),
                max(b[3] for b in self.boxes), max(b[4] for b in self.boxes), max(b[5] for b in self.boxes))


def instances(model):
    return {p['id']: Instance(p) for p in model['parts']}


def _overlap(a, b, tol=TOL):
    return all(a[k] < b[k + 3] - tol and b[k] < a[k + 3] - tol for k in range(3))


def _buckets(box, size=40):
    return itertools.product(*(range(math.floor(box[k] / size), math.floor(box[k + 3] / size) + 1) for k in range(3)))


def _key(pos, axis):
    return tuple(round(v * 2) / 2 for v in pos), tuple(round(v) for v in axis)


def connections(inst):
    """All mated connector pairs: [(kind, a, b)], with a and b instance IDs."""
    out = []
    receivers = defaultdict(list)
    for pid, q in inst.items():
        for c in q.connectors:
            if c['kind'] == 'stud' and c['female']:
                receivers[_key(c['pos'], c['axis'])].append(pid)
    studs_mated = defaultdict(set)
    for pid, q in inst.items():
        for c in q.connectors:
            if c['kind'] == 'stud' and not c['female']:
                for other in receivers.get(_key(c['pos'], c['axis']), ()):
                    if other != pid:
                        out.append(('stud', pid, other)); studs_mated[pid, _key(c['pos'], c['axis'])].add(other)
    points = defaultdict(list)
    for pid, q in inst.items():
        for c in q.connectors:
            if c['kind'] in ('hole', 'clip', 'hinge'):
                points[tuple(math.floor(v / 20) for v in c['pos'])].append((pid, c))

    def near(pos, reach=1):
        base = [math.floor(v / 20) for v in pos]
        for d in itertools.product(range(-reach, reach + 1), repeat=3):
            yield from points.get(tuple(base[k] + d[k] for k in range(3)), ())

    def lateral(point, origin, axis):
        d = [point[k] - origin[k] for k in range(3)]; along = sum(d[k] * axis[k] for k in range(3))
        return math.sqrt(max(0.0, sum(v * v for v in d) - along * along)), along
    seen = set()
    for pid, q in inst.items():
        for c in q.connectors:
            if c['kind'] == 'pin':
                for other, h in near(c['pos'], 2):
                    if other == pid or h['kind'] != 'hole' or abs(abs(sum(c['axis'][k] * h['axis'][k] for k in range(3))) - 1) > .02:
                        continue
                    lat, along = lateral(h['pos'], c['pos'], c['axis'])
                    if lat < 1.5 and abs(along) <= 21 and ('pin', pid, other) not in seen:
                        seen.add(('pin', pid, other)); out.append(('pin', pid, other))
            elif c['kind'] == 'bar':
                length = math.dist(c['pos'], c['end'])
                for other, h in itertools.chain(near(c['pos'], 2), near(c['end'], 2)):
                    if other == pid or h['kind'] != 'clip':
                        continue
                    lat, along = lateral(h['pos'], c['pos'], c['axis'])
                    if lat < 2.5 and -2 <= along <= length + 2 and ('clip', pid, other) not in seen:
                        seen.add(('clip', pid, other)); out.append(('clip', pid, other))
            elif c['kind'] == 'hinge':
                for other, h in near(c['pos']):
                    if other != pid and h['kind'] == 'hinge' and math.dist(c['pos'], h['pos']) <= 10 and ('hinge', other, pid) not in seen:
                        seen.add(('hinge', pid, other)); out.append(('hinge', pid, other))
    return out, studs_mated


def bbox(model, inst=None):
    """Stud-unit bounds for maps: x0, y0 (model y = LDraw Z), 0, x1, y1, height in plates."""
    inst = inst or instances(model)
    ex = [q.extent() for q in inst.values()]
    x0 = math.floor(min(e[0] for e in ex) / 20 + 1e-6); x1 = math.ceil(max(e[3] for e in ex) / 20 - 1e-6)
    z0 = math.floor(min(e[2] for e in ex) / 20 + 1e-6); z1 = math.ceil(max(e[5] for e in ex) / 20 - 1e-6)
    height = math.ceil((max(e[4] for e in ex) - min(e[1] for e in ex)) / 8 - 1e-6)
    return x0, z0, 0, max(x1, x0 + 1), max(z1, z0 + 1), height


def validate(model, report):
    errors, warnings = report['errors'], report['warnings']
    try:
        inst = instances(model)
    except (ValueError, KeyError) as e:
        errors.append(str(e)); return report
    for p in model['parts']:
        try:
            partdb.color(p['color'])
        except ValueError as e:
            errors.append(f'{p["id"]}: {e}'); continue
        made = partdb.produced(p['part'], p['color'])
        if made is False:
            errors.append(f'{p["id"]}: {p["part"]} is not recorded as produced in colour {p["color"]} '
                          f'({partdb.color(p["color"])["name"]}); pick a produced colour (brick.py part {p["part"]})')
        elif made is None:
            warnings.append(f'{p["id"]}: availability of {p["part"]} in colour {p["color"]} could not be checked')
    ids = [pid for s in model['steps'] for pid in s['parts']]
    order = {pid: i for i, pid in enumerate(ids)}
    # Collisions between bodies (spatial hash of boxes).
    grid, clashes = defaultdict(list), set()
    for pid in ids:
        for b in inst[pid].boxes:
            for cell in _buckets(b):
                for other, ob in grid[cell]:
                    if other != pid and (other, pid) not in clashes and _overlap(b, ob):
                        clashes.add((other, pid))
                grid[cell].append((pid, b))
    pairs, studs_mated = connections(inst)
    # Pins sit inside holes, clips wrap bars, hinge fingers interleave: those bodies overlap by design.
    nested = {frozenset((a, b)) for kind, a, b in pairs if kind != 'stud'}
    errors.extend(f'Body collision: {a} and {b}' for a, b in sorted(clashes, key=lambda x: (order[x[0]], order[x[1]]))
                  if frozenset((a, b)) not in nested)
    graph = defaultdict(set); kinds = defaultdict(int)
    for kind, a, b in pairs:
        graph[a].add(b); graph[b].add(a); kinds[kind] += 1
    # A stud whose volume meets another body without entering one of its receivers is blocked.
    for pid in ids:
        for c in inst[pid].connectors:
            if c['kind'] != 'stud' or c['female']:
                continue
            ax = c['axis']; ctr = [c['pos'][k] + ax[k] * 2 for k in range(3)]
            half = [2 if abs(ax[k]) > .5 else 6 for k in range(3)]
            vol = tuple(ctr[k] - half[k] for k in range(3)) + tuple(ctr[k] + half[k] for k in range(3))
            mates = studs_mated.get((pid, _key(c['pos'], c['axis'])), set())
            for cell in _buckets(vol):
                hit = next((o for o, ob in grid[cell] if o != pid and o not in mates and frozenset((pid, o)) not in nested
                            and _overlap(vol, ob)), None)
                if hit:
                    errors.append(f'{pid}: stud at {tuple(round(v, 1) for v in c["pos"])} is blocked by {hit} (no receiver there)')
                    break
    table = max(q.extent()[4] for q in inst.values())
    stud_owner = defaultdict(list)
    for o, q in inst.items():
        for c in q.connectors:
            if c['kind'] == 'stud' and not c['female']:
                stud_owner[_key(c['pos'], c['axis'])].append(o)
    columns = defaultdict(list)                     # XZ buckets of every body box, for the top-down insertion test
    for o in ids:
        for ob in inst[o].boxes:
            for bx in range(math.floor(ob[0] / 40), math.floor(ob[3] / 40) + 1):
                for bz in range(math.floor(ob[2] / 40), math.floor(ob[5] / 40) + 1):
                    columns[bx, bz].append((o, ob))
    for pid in ids:
        q = inst[pid]
        earlier = [o for o in graph[pid] if order[o] < order[pid]]
        on_table = abs(q.extent()[4] - table) < 0.5
        if not earlier and not on_table:
            errors.append(f'{pid}: not connected to an earlier piece')
        if q.upright and q.grid and not on_table:
            held = sum(1 for c in q.connectors if c['kind'] == 'stud' and c['female']
                       and any(o != pid and order[o] < order[pid] for o in stud_owner.get(_key(c['pos'], c['axis']), ())))
            total = sum(1 for c in q.connectors if c['kind'] == 'stud' and c['female'] and abs(c['axis'][1] + 1) < .01)
            if earlier and total and held < total:
                warnings.append(f'{pid}: {held}/{total} receivers on studs at placement; review overhang')
        if q.upright:
            ex = q.extent(); blocker = None
            for b in q.boxes:
                for bx in range(math.floor(b[0] / 40), math.floor(b[3] / 40) + 1):
                    for bz in range(math.floor(b[2] / 40), math.floor(b[5] / 40) + 1):
                        for o, ob in columns[bx, bz]:
                            if (o != pid and order[o] < order[pid] and ob[4] <= ex[1] + TOL and b[0] < ob[3] - TOL and ob[0] < b[3] - TOL
                                    and b[2] < ob[5] - TOL and ob[2] < b[5] - TOL):
                                blocker = blocker or o
            if blocker:
                errors.append(f'{pid}: earlier piece {blocker} blocks insertion from above')
    unseen, components = set(ids), []
    while unseen:
        todo, seen = [min(unseen)], set()
        while todo:
            a = todo.pop()
            if a in seen:
                continue
            seen.add(a); todo.extend(graph[a] - seen)
        unseen -= seen; components.append(seen)
    if len(components) > 1:
        errors.append(f'Final assembly has {len(components)} disconnected components')
    loose = sum(1 for q in inst.values() if abs(q.extent()[4] - table) < 0.5)
    if loose > 1:
        warnings.append(f'{loose} foundation pieces start loose on the table; keep aligned until tied together')
    inferred = {k: v for k, v in kinds.items() if k != 'stud'}
    if inferred:
        warnings.append('Connections inferred from connector primitives (fit not modelled): '
                        + ', '.join(f'{v} {k}' for k, v in sorted(inferred.items())))
    if any(not q.upright for q in inst.values()):
        warnings.append(f'{sum(not q.upright for q in inst.values())} sideways or inverted pieces: insertion path not checked')
    ex = [q.extent() for q in inst.values()]
    dims = [max(e[3] for e in ex) - min(e[0] for e in ex), max(e[5] for e in ex) - min(e[2] for e in ex),
            max(e[4] for e in ex) - min(e[1] for e in ex) + 4]
    report.update(passed=not errors, part_count=len(model['parts']), step_count=len(model['steps']),
                  connection_components=len(components), connections=dict(sorted(kinds.items())),
                  dimensions_mm=[round(v * 0.4, 1) for v in dims])
    return report


def catalog_snapshot(model):
    parts, colors = {}, {}
    for p in model['parts']:
        if p['part'] not in parts:
            a = ldraw.analyze3d(p['part']); b = a['bbox_ldu']
            parts[p['part']] = {'name': partdb.part(p['part'])['title'],
                                'size_ldu': [round(b[3] - b[0], 1), round(b[4] - b[1], 1), round(b[5] - b[2], 1)],
                                'source': f'https://library.ldraw.org/library/official/parts/{p["part"]}.dat'}
        c = partdb.color(p['color'])
        colors[p['color']] = {'name': c['name'], 'hex': c['hex']}
    return {'version': '1.1', 'ldraw_release': ldraw.release(), 'parts': dict(sorted(parts.items())),
            'colors': dict(sorted(colors.items(), key=lambda kv: int(kv[0])))}


def snap(target, connector_index, part, color, own_index, spin=0, new_id='new', offset=(0, 0, 0)):
    """Placement that docks connector `own_index` of a new part onto connector `connector_index` of placed instance
    `target`. Studs dock into receivers (and the reverse), pins into holes, bars into clips. `spin` (0/90/180/270)
    turns the new part about the shared axis. `offset` (LDU) nudges the result: hinge fingers and clips meet slightly
    off their primitives' origins, so slide until the validator reports no collision."""
    goal = target.connectors[connector_index]
    a = ldraw.analyze3d(part)
    own = a['connectors'][own_index]
    pairs = {('stud', False): ('stud', True), ('stud', True): ('stud', False), ('pin', False): ('hole', True),
             ('hole', True): ('pin', False), ('bar', False): ('clip', True), ('clip', True): ('bar', False),
             ('hinge', False): ('hinge', False)}
    if pairs.get((goal['kind'], goal['female'])) != (own['kind'], own['female']):
        raise ValueError(f'Connector types do not mate: {goal["kind"]}{"(F)" if goal["female"] else ""} and '
                         f'{own["kind"]}{"(F)" if own["female"] else ""}')
    want = tuple(round(v) for v in goal['axis'])
    options = [m for m in ORIENTATIONS if tuple(round(v) for v in mul(m, own['axis'])) == want]
    if goal['kind'] in ('pin', 'hole', 'bar', 'clip', 'hinge'):
        options += [m for m in ORIENTATIONS if tuple(-round(v) for v in mul(m, own['axis'])) == want]
    if not options:
        raise ValueError('No axis-aligned orientation brings the connector axes together')
    # Upright orientations first (the part keeps its own up axis), then the rest; `spin` steps through them.
    options = sorted(set(options), key=lambda m: (m[4] != 1, m))
    m = options[(spin // 90) % len(options)]
    r = mul(m, own['pos'])
    pos = [round(goal['pos'][k] - r[k] + offset[k], 3) for k in range(3)]
    return {'id': new_id, 'part': part, 'color': color, 'pos': pos, 'matrix': list(m)}
