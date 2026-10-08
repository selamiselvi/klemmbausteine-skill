"""Grid placement for format 1.1: any official upright stud-grid part, rotated in 90-degree steps.

ldraw.analyze() measures a part's footprint cells, occupied plate layers, top studs and bottom receivers from its real
geometry. Placement: x/y are the minimum footprint corner in studs, z the body bottom in plates. Placed converts that into
the LDraw position and rotation; assembly.py does the checks.
"""
import ldraw
import partdb

ROT = {0: (1, 0, 0, 0, 1, 0, 0, 0, 1), 90: (0, 0, -1, 0, 1, 0, 1, 0, 0),
       180: (-1, 0, 0, 0, 1, 0, 0, 0, -1), 270: (0, 0, 1, 0, 1, 0, -1, 0, 0)}


def _rot_xz(r, x, z):
    m = ROT[r]
    return m[0] * x + m[2] * z, m[6] * x + m[8] * z


class Placed:
    """One part instance mapped onto the model's stud grid (cells/voxels in model x, y and plate z)."""

    def __init__(self, p):
        self.p = p
        a = ldraw.analyze(p['part'])
        if not a.get('grid'):
            raise ValueError(f'{p["id"]}: part {p["part"]} is not an upright stud-grid part ({a.get("reason", "unsupported")})')
        self.a = a
        w, d = a['width'], a['depth']
        # Rotate cell centres about the part's own footprint centre, then re-anchor at the minimum corner.
        def cell(i, j):
            cx, cz = _rot_xz(p['rotation'], i + .5 - w / 2, j + .5 - d / 2)
            return cx, cz
        self.w, self.d = (w, d) if p['rotation'] in (0, 180) else (d, w)
        self.h = a['height']
        off_x, off_z = self.w / 2, self.d / 2

        def to_model(i, j):
            cx, cz = cell(i, j)
            return p['x'] + round(cx + off_x - .5), p['y'] + round(cz + off_z - .5)

        self.cells = {}
        for i, j in a['cells']:
            self.cells[to_model(i, j)] = [p['z'] + k for k in a['layers'][f'{i},{j}']]
        self.studs = [(*to_model(i, j), p['z'] + k) for i, j, k in a['studs']]
        self.receivers = [(*to_model(i, j), p['z']) for i, j in a['receivers']]
        self.voxels = {(x, y, z) for (x, y), zs in self.cells.items() for z in zs}

    def ldraw_line(self):
        """LDraw line: official parts keep their own origin, so translate the measured footprint corner to the grid."""
        p, a = self.p, self.a
        x0, ybottom, z0 = a['origin_ldu']
        w, d = a['width'], a['depth']
        cxl, czl = x0 + w * 10, z0 + d * 10          # local footprint centre (LDU)
        rx, rz = _rot_xz(p['rotation'], cxl, czl)     # where that centre lands after rotation about the origin
        tx = (p['x'] + self.w / 2) * 20 - rx
        tz = (p['y'] + self.d / 2) * 20 - rz
        ty = -p['z'] * 8 - ybottom
        m = ' '.join(f'{v:g}' for v in ROT[p['rotation']])
        return f'1 {p["color"]} {tx:g} {ty:g} {tz:g} {m} {p["part"]}.dat'


def part_name(pid):
    return partdb.part(pid)['title']


def color_name(code):
    return partdb.color(code)['name']
