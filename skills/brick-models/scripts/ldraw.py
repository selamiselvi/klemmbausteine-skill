"""Read the official LDraw parts library (as downloaded by setup_runtime.py) without Blender.

The library stays a ZIP in the user's runtime cache. This module flattens a part into triangles and edge lines, finds its
top studs from the library's own stud primitives, and derives the stud-grid data the validator uses: footprint cells,
body height in plates, occupied plate layers per cell, top studs and bottom stud receivers. Everything is measured from
the real part geometry; nothing is typed in by hand. Results are cached per library release.
"""
import json
import math
import re
import zipfile
from functools import lru_cache
from pathlib import Path

from runtime import library_paths

STUD_LDU, PLATE_LDU = 20, 8
# Male top studs (System). Duplo, Scala, Quatro and underside tubes are deliberately excluded.
TOP_STUD = re.compile(r'^(stud|studa|stud2|stud2a|stud6|stud6a|stud9|stud10|stud13|stud15|stud17|stud17a|stud26|studel|'
                      r'studh|studhl|studhr|studp01|studx|studxa|stud-logo\d?|stud2-logo\d?)\.dat$')
# Primitives that only exist on top studs; their triangles are left out of the body measurements.
STUD_GEOMETRY = re.compile(r'^(stud.*|stug.*|stu2.*)\.dat$')
# Connector primitives of the official library (kind, female?). Their placement in a part gives position and axis.
CONNECTOR = [(re.compile(r'^(connect\d*|confric\d*)\.dat$'), 'pin', False),
             (re.compile(r'^(axle|axleend|axl3end|axl2end)\.dat$'), 'pin', False),
             (re.compile(r'^(peghole\d*|npeghol\w*|npeghole|beamhole|connhole|axlehole|axl\dhole|axlhole\w*)\.dat$'), 'hole', True),
             (re.compile(r'^clip\d+\.dat$'), 'clip', True),
             (re.compile(r'^(clh\d+[a-z]?|arm\d)\.dat$'), 'hinge', False)]
CYLINDER = re.compile(r'^4-4cyl[io]\.dat$')


def _lib():
    return library_paths()


@lru_cache(None)
def archive():
    path = _lib()['ldraw']
    if not path.is_file():
        raise ValueError('LDraw library missing. Run scripts/setup_runtime.py first.')
    z = zipfile.ZipFile(path)
    return z, {n.lower(): n for n in z.namelist()}


def resolve(name):
    z, names = archive()
    name = name.replace('\\', '/').lower().strip()
    for prefix in ('ldraw/parts/', 'ldraw/p/', 'ldraw/'):
        if prefix + name in names:
            return names[prefix + name]
    raise KeyError(name)


def read(name):
    z, _ = archive()
    return z.read(resolve(name)).decode('utf-8-sig', errors='replace')


@lru_cache(None)
def release():
    """Newest UPDATE tag in the library's own release notes (or the archive's sha256 recorded at setup)."""
    meta = _lib()['meta']
    if meta.is_file():
        return json.loads(meta.read_text()).get('ldraw_release', 'unknown')
    return 'unknown'


@lru_cache(None)
def colors():
    """LDConfig colours: code → {name, hex, transparent}."""
    out = {}
    for line in read('LDConfig.ldr').splitlines():
        m = re.search(r'!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+(#[0-9A-Fa-f]{6})', line)
        if m:
            out[m[2]] = {'name': m[1].replace('_', ' '), 'hex': m[3].upper(), 'transparent': 'ALPHA' in line}
    return out


def header(part):
    """Title, category and keywords from the part's own header."""
    text = read(part + '.dat').splitlines()
    title = text[0][2:].strip() if text and text[0].startswith('0') else part
    cat = next((l.split(None, 2)[2].strip() for l in text if l.startswith('0 !CATEGORY')), title.lstrip('~_=|').split(' ')[0])
    keys = ' '.join(l.split(None, 2)[2] for l in text if l.startswith('0 !KEYWORDS') and len(l.split(None, 2)) > 2)
    lic = next((l[2:].strip() for l in text if l.startswith('0 !LICENSE')), '')
    author = next((l.split(None, 2)[2].strip() for l in text if l.startswith('0 Author:')), '')
    return {'title': title, 'category': cat, 'keywords': keys, 'license': lic, 'author': author}


def _mat(v):
    return (v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8])


def _mul(a, b):
    return tuple(sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3)) for r in range(3) for c in range(3))


def _apply(m, t, p):
    return (m[0] * p[0] + m[1] * p[1] + m[2] * p[2] + t[0], m[3] * p[0] + m[4] * p[1] + m[5] * p[2] + t[1],
            m[6] * p[0] + m[7] * p[1] + m[8] * p[2] + t[2])


def _det(m):
    return m[0] * (m[4] * m[8] - m[5] * m[7]) - m[1] * (m[3] * m[8] - m[5] * m[6]) + m[2] * (m[3] * m[7] - m[4] * m[6])


@lru_cache(4096)
def _raw(name):
    """One file, unflattened: triangles, quads→triangles, edges and sub-file references (with BFC winding)."""
    tris, edges, subs = [], [], []
    ccw, invert = True, False
    for line in read(name).splitlines():
        b = line.split()
        if not b:
            continue
        if b[0] == '0':
            if len(b) > 1 and b[1] == 'BFC':
                if 'CW' in b[2:]:
                    ccw = False
                if 'CCW' in b[2:]:
                    ccw = True
                if 'INVERTNEXT' in b[2:]:
                    invert = True
            continue
        if b[0] == '1' and len(b) >= 15:
            v = list(map(float, b[2:14]))
            subs.append((b[1], (v[0], v[1], v[2]), _mat(v[3:12]), ' '.join(b[14:]), invert))
            invert = False
        elif b[0] == '2' and len(b) >= 8:
            v = list(map(float, b[2:8]))
            edges.append(((v[0], v[1], v[2]), (v[3], v[4], v[5])))
        elif b[0] in ('3', '4'):
            n = int(b[0]); v = list(map(float, b[2:2 + n * 3]))
            pts = [(v[i], v[i + 1], v[i + 2]) for i in range(0, n * 3, 3)]
            faces = [pts[:3]] if n == 3 else [pts[:3], [pts[0], pts[2], pts[3]]]
            for f in faces:
                tris.append(tuple(f) if ccw else (f[0], f[2], f[1]))
    return tris, edges, subs


def flatten(part, with_edges=False):
    """All triangles of a part in part coordinates (LDraw: -Y is up). Returns dict with tris, stud flags, edges, studs."""
    tris, flags, edges, studs, connectors, cylinders = [], [], [], [], [], []
    ident = (1, 0, 0, 0, 1, 0, 0, 0, 1)

    def walk(name, m, t, flip, in_stud):
        try:
            ftris, fedges, subs = _raw(name)
        except KeyError:
            return
        base = name.replace('\\', '/').split('/')[-1].lower()
        stud_geo = in_stud or bool(STUD_GEOMETRY.match(base))
        for tri in ftris:
            pts = [_apply(m, t, p) for p in tri]
            tris.append(tuple(pts[::-1]) if flip else tuple(pts)); flags.append(stud_geo)
        if with_edges:
            for a, b2 in fedges:
                edges.append((_apply(m, t, a), _apply(m, t, b2)))
        for color, st, sm, sub, inv in subs:
            nm = _mul(m, sm); nt = _apply(m, t, st)
            sb = sub.replace('\\', '/').split('/')[-1].lower()
            if TOP_STUD.match(sb):
                up = (-nm[1], -nm[4], -nm[7])   # where the primitive's -Y axis points
                studs.append({'pos': nt, 'up': up})
            for rx, kind, female in CONNECTOR:
                if rx.match(sb):
                    connectors.append({'kind': kind, 'female': female, 'pos': nt, 'axis': (nm[1], nm[4], nm[7]), 'name': sb})
                    break
            if CYLINDER.match(sb):
                cylinders.append({'pos': nt, 'm': nm})
            walk(sub, nm, nt, flip ^ inv ^ (_det(sm) < 0), stud_geo)

    walk(part + '.dat', ident, (0.0, 0.0, 0.0), False, False)
    return {'tris': tris, 'stud': flags, 'edges': edges, 'studs': studs, 'connectors': connectors, 'cylinders': cylinders}


def _ray_y(tris, x, z, downward):
    """First hit along a vertical ray through (x, z): from the top (smallest y) or from the bottom (largest y)."""
    best = None
    for a, b, c in tris:
        # Barycentric point-in-triangle test in the XZ plane, then interpolate y.
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) < -1e-6:
            continue
        y = l1 * a[1] + l2 * b[1] + l3 * c[1]
        if best is None or (y < best if downward else y > best):
            best = y
    return best


def _tri_box(t, lo, hi):
    """Separating-axis test: does triangle t intersect the axis-aligned box [lo, hi]?"""
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]; h = [(hi[i] - lo[i]) / 2 for i in range(3)]
    v = [[p[i] - c[i] for i in range(3)] for p in t]
    for i in range(3):
        if min(p[i] for p in v) > h[i] or max(p[i] for p in v) < -h[i]:
            return False
    e = [[v[1][i] - v[0][i] for i in range(3)], [v[2][i] - v[1][i] for i in range(3)], [v[0][i] - v[2][i] for i in range(3)]]
    n = [e[0][1] * e[1][2] - e[0][2] * e[1][1], e[0][2] * e[1][0] - e[0][0] * e[1][2], e[0][0] * e[1][1] - e[0][1] * e[1][0]]
    r = sum(h[i] * abs(n[i]) for i in range(3)); dd = sum(n[i] * v[0][i] for i in range(3))
    if abs(dd) > r:
        return False
    for ed in e:
        for ax in ((0, -ed[2], ed[1]), (ed[2], 0, -ed[0]), (-ed[1], ed[0], 0)):
            ps = [sum(ax[i] * p[i] for i in range(3)) for p in v]
            rr = sum(h[i] * abs(ax[i]) for i in range(3))
            if min(ps) > rr or max(ps) < -rr:
                return False
    return True


def _near(v, step, tol=0.6):
    q = round(v / step)
    return abs(v - q * step) <= tol, q


def analyze(part):
    """Stud-grid description of a part, measured from its official geometry. Cached per library release."""
    cache = _lib()['analysis'] / release() / f'{part.lower()}.json'
    if cache.is_file():
        return json.loads(cache.read_text())
    flat = flatten(part)
    body = [t for t, s in zip(flat['tris'], flat['stud']) if not s]
    info = {'part': part, **{k: v for k, v in header(part).items() if k in ('title', 'category')}, 'grid': False}
    if not body:
        info['reason'] = 'no body geometry'
        return _store(cache, info)
    xs = [p[0] for t in body for p in t]; ys = [p[1] for t in body for p in t]; zs = [p[2] for t in body for p in t]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    okx, w = _near(x1 - x0, STUD_LDU); okz, d = _near(z1 - z0, STUD_LDU); oky, h = _near(y1 - y0, PLATE_LDU)
    up = [s for s in flat['studs'] if abs(s['up'][1] + 1) < 1e-3 and abs(s['up'][0]) < 1e-3 and abs(s['up'][2]) < 1e-3]
    side = len(flat['studs']) - len(up)
    info.update(bbox_ldu=[round(v, 3) for v in (x0, y0, z0, x1, y1, z1)], side_studs=side)
    if not (okx and okz and oky and w > 0 and d > 0 and h > 0):
        anchored = _grid_by_connectors(part, info, y1)
        if anchored:
            return _store(cache, anchored)
        info['reason'] = f'body {x1 - x0:g}×{z1 - z0:g}×{y1 - y0:g} LDU is not a whole stud footprint and plate height'
        return _store(cache, info)
    # Bucket triangles by cell so each vertical ray only tests nearby faces.
    buckets = {}
    for t in body:
        cx0 = int((min(p[0] for p in t) - x0) // STUD_LDU); cx1 = int((max(p[0] for p in t) - x0) // STUD_LDU)
        cz0 = int((min(p[2] for p in t) - z0) // STUD_LDU); cz1 = int((max(p[2] for p in t) - z0) // STUD_LDU)
        for i in range(max(0, cx0), min(w - 1, cx1) + 1):
            for j in range(max(0, cz0), min(d - 1, cz1) + 1):
                buckets.setdefault((i, j), []).append(t)
    cells, layers, receivers = [], {}, []
    for i in range(w):
        for j in range(d):
            cx, cz = x0 + (i + .5) * STUD_LDU, z0 + (j + .5) * STUD_LDU
            near = buckets.get((i, j), [])
            # Several sample columns per cell: a hollow stud or an axle hole must not hide the body around it.
            samples = [(cx, cz)] + [(cx + dx, cz + dz) for dx, dz in ((6, 0), (-6, 0), (0, 6), (0, -6))]
            tops = [y for y in (_ray_y(near, x, z, True) for x, z in samples) if y is not None]
            if not tops:
                continue
            center = _ray_y(near, cx, cz, True)
            top = center if center is not None else min(tops)
            bottom = _ray_y(near, cx, cz, False)
            # A receiver: material grips a stud in the lowest 4 LDU around the stud position, and the stud can enter.
            # A stud is 12 LDU wide: walls or tubes that hold it touch a ring about 6 LDU from the stud centre.
            grip = any(_tri_box(t, (cx - 7.5, y1 - 4, cz - 7.5), (cx + 7.5, y1 - 0.25, cz + 7.5)) for t in near
                       if max(p[1] for p in t) > y1 - 4.5)
            entry = _ray_y(near, cx, cz, False)
            hollow = entry is None or y1 - entry >= 3.5
            receiver = grip and hollow and not any(_tri_box(t, (cx - 3, y1 - 3.5, cz - 3), (cx + 3, y1 - 0.5, cz + 3)) for t in near
                                                   if max(p[1] for p in t) > y1 - 4)
            lo = y1 if receiver else (bottom if bottom is not None else y1)
            occ = [k for k in range(h) if top - .5 <= y1 - (k + .5) * PLATE_LDU <= lo + .5]
            if not occ:
                continue
            cells.append([i, j]); layers[f'{i},{j}'] = occ
            if receiver and 0 in occ:
                receivers.append([i, j])
    studs = []
    for s in up:
        okx2, si = _near(s['pos'][0] - x0 - 10, STUD_LDU, 1.0); okz2, sj = _near(s['pos'][2] - z0 - 10, STUD_LDU, 1.0)
        okh, sh = _near(y1 - s['pos'][1], PLATE_LDU, 1.0)
        if okx2 and okz2 and okh and 0 <= si < w and 0 <= sj < d:
            studs.append([si, sj, sh])
    info.update(grid=True, width=w, depth=d, height=h, cells=cells, layers=layers, studs=sorted(studs), receivers=sorted(receivers),
                origin_ldu=[round(x0, 3), round(y1, 3), round(z0, 3)])
    if not cells:
        info.update(grid=False, reason='no measurable body over the stud grid')
    return _store(cache, info)


def _grid_by_connectors(part, info, y1):
    """Grid anchor for parts whose body overhangs the stud grid (handles, clips, hinge fingers): the footprint is the
    lattice of their upward studs and bottom receivers; the height runs from the bottom to the top-stud base."""
    a3 = analyze3d(part)
    up = [c for c in a3['connectors'] if c['kind'] == 'stud' and not c['female'] and c['axis'] == [0, -1, 0]]
    rec = [c for c in a3['connectors'] if c['kind'] == 'stud' and c['female']]
    pts = up + rec
    if not pts:
        return None
    xs = [c['pos'][0] for c in pts]; zs = [c['pos'][2] for c in pts]
    gx0, gz0 = min(xs) - 10, min(zs) - 10
    w = round((max(xs) - min(xs)) / STUD_LDU) + 1; d = round((max(zs) - min(zs)) / STUD_LDU) + 1
    tops = {round(c['pos'][1], 1) for c in up}
    if len(tops) > 1:
        return None
    h = round((y1 - tops.pop()) / PLATE_LDU) if up else round((y1 - min(b[1] for b in a3['boxes'])) / PLATE_LDU)
    if h <= 0:
        return None
    cell = lambda c: [round((c['pos'][0] - gx0 - 10) / STUD_LDU), round((c['pos'][2] - gz0 - 10) / STUD_LDU)]
    cells = sorted({tuple(cell(c)) for c in pts})
    info.update(grid=True, anchor='connectors', width=w, depth=d, height=h, cells=[list(c) for c in cells],
                layers={f'{i},{j}': list(range(h)) for i, j in cells}, studs=sorted(cell(c) + [h] for c in up),
                receivers=sorted(cell(c) for c in rec), origin_ldu=[round(gx0, 3), round(y1, 3), round(gz0, 3)])
    return info


def _store(path, info):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, separators=(',', ':')))
    return info


def _rects(cells):
    """Greedy decomposition of a set of (i, j) grid cells into rectangles (i0, j0, i1, j1), inclusive."""
    cells, out = set(cells), []
    while cells:
        i0, j0 = min(cells)
        i1 = i0
        while (i1 + 1, j0) in cells:
            i1 += 1
        j1 = j0
        while all((i, j1 + 1) in cells for i in range(i0, i1 + 1)):
            j1 += 1
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                cells.discard((i, j))
        out.append((i0, j0, i1, j1))
    return out


def analyze3d(part):
    """Full-3D description in the part's own LDraw frame (LDU, -Y up), measured from official geometry:
    collision boxes (studs excluded, stud cavities left open), and connectors with position and axis:
    studs (male) and stud receivers (female) in any direction, Technic pins/axles and holes, bars and clips, hinge fingers.
    Cached per library release."""
    cache = _lib()['analysis'] / release() / f'{part.lower()}.3d.json'
    if cache.is_file():
        return json.loads(cache.read_text())
    flat = flatten(part)
    body = [t for t, s in zip(flat['tris'], flat['stud']) if not s]
    info = {'part': part, 'title': header(part)['title'], 'boxes': [], 'connectors': []}
    if not body:
        info['reason'] = 'no body geometry'
        return _store(cache, info)
    xs = [p[0] for t in body for p in t]; ys = [p[1] for t in body for p in t]; zs = [p[2] for t in body for p in t]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    info['bbox_ldu'] = [round(v, 3) for v in (x0, y0, z0, x1, y1, z1)]
    up = [s for s in flat['studs'] if abs(s['up'][1] + 1) < 1e-3]
    # Stud lattice: aligned with the part's own top studs where it has them, else with its bounding box.
    ox = (up[0]['pos'][0] - 10) % 20 if up else x0 % 20
    oz = (up[0]['pos'][2] - 10) % 20 if up else z0 % 20
    gx0 = math.floor((x0 - ox) / 20 + 1e-6) * 20 + ox; gz0 = math.floor((z0 - oz) / 20 + 1e-6) * 20 + oz
    nx = max(1, math.ceil((x1 - gx0) / 20 - 1e-6)); nz = max(1, math.ceil((z1 - gz0) / 20 - 1e-6))
    def near(xa, xb, za, zb):
        return [t for t in body if min(p[0] for p in t) <= xb and max(p[0] for p in t) >= xa and min(p[2] for p in t) <= zb and max(p[2] for p in t) >= za]
    enclosed, receivers = set(), []
    for i in range(nx):
        for j in range(nz):
            cx, cz = gx0 + (i + .5) * 20, gz0 + (j + .5) * 20
            nb = near(cx - 10.5, cx + 10.5, cz - 10.5, cz + 10.5)
            grip = any(_tri_box(t, (cx - 7.5, y1 - 4, cz - 7.5), (cx + 7.5, y1 - 0.25, cz + 7.5)) for t in nb if max(p[1] for p in t) > y1 - 4.5)
            entry = _ray_y(nb, cx, cz, False)
            hollow = entry is None or y1 - entry >= 3.5
            plug = any(_tri_box(t, (cx - 3, y1 - 3.5, cz - 3), (cx + 3, y1 - 0.5, cz + 3)) for t in nb if max(p[1] for p in t) > y1 - 4)
            if grip:
                enclosed.add((i, j))
            covered = any(_ray_y(nb, x, z, True) is not None for x, z in ((cx, cz), (cx + 6, cz), (cx - 6, cz), (cx, cz + 6), (cx, cz - 6)))
            if grip and hollow and not plug and covered:
                receivers.append((cx, cz))
    # Collision columns every 4 LDU; enclosed cells count as solid down to the bottom except the stud cavities.
    cols = {}
    for a in range(max(1, math.ceil((x1 - x0) / 4 - 1e-6))):
        for b in range(max(1, math.ceil((z1 - z0) / 4 - 1e-6))):
            cx, cz = x0 + (a + .5) * 4, z0 + (b + .5) * 4
            nb = near(cx - 2, cx + 2, cz - 2, cz + 2)
            top = _ray_y(nb, cx, cz, True)
            if top is None:
                continue
            cell = (int((cx - gx0) // 20), int((cz - gz0) // 20))
            bottom = y1 if cell in enclosed else _ray_y(nb, cx, cz, False)
            if any(abs(cx - rx) <= 6.5 and abs(cz - rz) <= 6.5 for rx, rz in receivers):
                bottom = min(bottom, y1 - 4)
            if bottom - top > 0.5:
                cols[(a, b)] = (round(top * 2) / 2, round(bottom * 2) / 2)
    by_interval = {}
    for k, v in cols.items():
        by_interval.setdefault(v, set()).add(k)
    for (top, bottom), cells in sorted(by_interval.items()):
        for a0, b0, a1, b1 in _rects(cells):
            info['boxes'].append([round(x0 + a0 * 4, 3), top, round(z0 + b0 * 4, 3), round(x0 + (a1 + 1) * 4, 3), bottom, round(z0 + (b1 + 1) * 4, 3)])
    con = info['connectors']
    for s in flat['studs']:
        con.append({'kind': 'stud', 'female': False, 'pos': [round(v, 3) for v in s['pos']], 'axis': [round(v) for v in s['up']]})
    for rx, rz in receivers:
        con.append({'kind': 'stud', 'female': True, 'pos': [round(rx, 3), round(y1, 3), round(rz, 3)], 'axis': [0, -1, 0]})
    seen = set()
    for c in flat['connectors']:
        key = (c['kind'], tuple(round(v, 1) for v in c['pos']), tuple(round(v, 2) for v in c['axis']))
        if key in seen:
            continue
        seen.add(key)
        n = math.sqrt(sum(v * v for v in c['axis'])) or 1
        con.append({'kind': c['kind'], 'female': c['female'], 'pos': [round(v, 3) for v in c['pos']], 'axis': [round(v / n, 3) for v in c['axis']]})
    stud_pts = [s['pos'] for s in flat['studs']]
    for cyl in flat['cylinders']:
        m, t = cyl['m'], cyl['pos']
        c0 = (m[0], m[3], m[6]); c1 = (m[1], m[4], m[7]); c2 = (m[2], m[5], m[8])
        r0 = math.sqrt(sum(v * v for v in c0)); r2 = math.sqrt(sum(v * v for v in c2)); ln = math.sqrt(sum(v * v for v in c1))
        if not (abs(r0 - 4) < .3 and abs(r2 - 4) < .3 and ln >= 4):
            continue
        axis = tuple(v / ln for v in c1); end = tuple(t[k] + c1[k] for k in range(3))
        mid = tuple((t[k] + end[k]) / 2 for k in range(3))
        if any(math.dist(mid, sp) < 8 for sp in stud_pts):
            continue                                      # the hollow inside a stud, not a bar
        if abs(axis[1]) > .99 and min(t[1], end[1]) >= y1 - 8.5:
            continue                                      # an underside pin between tubes, not a bar
        def on_axis(c):
            d = [mid[k] - c['pos'][k] for k in range(3)]; ax = c['axis']
            along = sum(d[k] * ax[k] for k in range(3))
            return abs(abs(sum(axis[k] * ax[k] for k in range(3))) - 1) < .02 and math.sqrt(max(0, sum(v * v for v in d) - along * along)) < 1
        if any(on_axis(c) for c in flat['connectors'] if c['kind'] in ('pin', 'hole')):
            continue                                      # the bore of a pin or hole, not a bar
        key = ('bar', tuple(round(v, 1) for v in t), tuple(round(v, 1) for v in end))
        if key in seen:
            continue
        seen.add(key)
        con.append({'kind': 'bar', 'female': False, 'pos': [round(v, 3) for v in t], 'end': [round(v, 3) for v in end],
                    'axis': [round(v, 3) for v in axis]})
    return _store(cache, info)
