"""Searchable index of every official LDraw part, joined with Rebrickable's record of which part exists in which colour.

`brick.py index` builds it once after setup (seconds). Data stays in the user runtime, never in the skill.
Rebrickable colour IDs follow LDraw codes for most colours; a code only counts as mapped when both sources also agree on
the colour's name. Unmapped colours or parts report availability as unknown instead of guessing.
"""
import csv
import gzip
import json
import re
import zipfile
from functools import lru_cache

from runtime import library_paths

INDEX_VERSION = 1


def _norm(name):
    return re.sub(r'[^a-z0-9]', '', name.lower().replace('grey', 'gray').replace('trans', 'trans'))


def _clean(title):
    return re.sub(r'\s+', ' ', title).strip()


def build_index():
    import ldraw
    paths = library_paths()
    z, _ = ldraw.archive()
    rb = paths['rebrickable']
    rb_colors = {r['id']: r for r in csv.DictReader(gzip.open(rb / 'colors.csv.gz', 'rt', encoding='utf-8'))}
    rb_parts = {r['part_num'].lower(): r for r in csv.DictReader(gzip.open(rb / 'parts.csv.gz', 'rt', encoding='utf-8'))}
    combos = {}
    for r in csv.DictReader(gzip.open(rb / 'elements.csv.gz', 'rt', encoding='utf-8')):
        combos.setdefault(r['part_num'].lower(), set()).add(r['color_id'])
    colors = {}
    for code, c in ldraw.colors().items():
        r = rb_colors.get(code)
        mapped = bool(r) and (_norm(c['name']) == _norm(r['name']) or _norm(c['name']) in _norm(r['name']) or _norm(r['name']) in _norm(c['name']))
        colors[code] = {**c, 'rebrickable': r['name'] if mapped else None}
    parts = []
    for n in z.namelist():
        low = n.lower()
        if not (low.startswith('ldraw/parts/') and low.endswith('.dat')) or low.count('/') != 2:
            continue
        pid = n.split('/')[-1][:-4]
        head = z.read(n)[:1500].decode('utf-8-sig', errors='replace').splitlines()
        title = _clean(head[0][2:]) if head and head[0].startswith('0') else pid
        cat = next((l.split(None, 2)[2].strip() for l in head if l.startswith('0 !CATEGORY') and len(l.split(None, 2)) > 2),
                   title.lstrip('~_=|').split(' ')[0])
        keys = ' '.join(l.split(None, 2)[2] for l in head if l.startswith('0 !KEYWORDS') and len(l.split(None, 2)) > 2)
        kind = next((l.split()[2] for l in head if l.startswith('0 !LDRAW_ORG') and len(l.split()) > 2), 'Part')
        alias = title.startswith(('~', '=', '_')) or 'Alias' in kind or 'Moved' in title or 'Obsolete' in title
        rbp = rb_parts.get(pid.lower())
        produced = sorted((c for c in combos.get(pid.lower(), ()) if c in colors and colors[c]['rebrickable']), key=int)
        parts.append({'id': pid, 'title': title, 'category': cat, 'keywords': keys, 'alias': alias,
                      'rebrickable': rbp['name'] if rbp else None, 'colors': produced})
    # LDraw renames parts ("~Moved to 3023b") while Rebrickable may keep the old number: credit the new ID too.
    by_id = {p['id'].lower(): p for p in parts}
    for p in parts:
        m = re.match(r'~Moved to (\S+)', p['title'])
        target = by_id.get(m[1].lower()) if m else None
        if target and p['colors']:
            target['colors'] = sorted(set(target['colors']) | set(p['colors']), key=int)
            target['rebrickable'] = target['rebrickable'] or p['rebrickable']
    index = {'version': INDEX_VERSION, 'ldraw_release': ldraw.release(), 'colors': colors, 'parts': parts}
    paths['index'].write_text(json.dumps(index, separators=(',', ':')))
    return {'parts': len(parts), 'with_known_colors': sum(bool(p['colors']) for p in parts), 'colors': len(colors)}


@lru_cache(None)
def index():
    path = library_paths()['index']
    if not path.is_file():
        raise ValueError('Parts index missing. Run scripts/setup_runtime.py (or brick.py index) first.')
    data = json.loads(path.read_text())
    data['by_id'] = {p['id'].lower(): p for p in data['parts']}
    return data


def part(pid):
    p = index()['by_id'].get(pid.lower())
    if not p:
        raise ValueError(f'Unknown LDraw part: {pid}')
    return p


def color(code):
    c = index()['colors'].get(str(code))
    if not c:
        raise ValueError(f'Unknown LDraw colour code: {code}')
    return c


def produced(pid, code):
    """True/False from Rebrickable's element records; None when the part or colour cannot be matched reliably."""
    p = index()['by_id'].get(pid.lower())
    c = index()['colors'].get(str(code))
    if not p or not c or not c['rebrickable'] or not p['rebrickable']:
        return None
    return str(code) in p['colors']


def search(query, limit=25, color_filter=None, include_aliases=False):
    terms = [t for t in re.split(r'\s+', query.lower().strip()) if t]
    want = None
    if color_filter:
        cf = _norm(color_filter)
        want = {code for code, c in index()['colors'].items() if code == color_filter or _norm(c['name']) == cf}
        if not want:
            raise ValueError(f'Unknown colour: {color_filter}')
    hits = []
    for p in index()['parts']:
        if p['alias'] and not include_aliases:
            continue
        text = ' '.join([p['id'], p['title'], p['category'], p['keywords'], p['rebrickable'] or '']).lower()
        squashed = re.sub(r'\s+', ' ', text)
        if not all(t in squashed for t in terms):
            continue
        if want is not None and not want & set(p['colors']):
            continue
        # Prefer real, widely produced parts and exact title matches.
        score = len(p['colors']) + (50 if all(t in p['title'].lower() for t in terms) else 0)
        hits.append((-score, p['id']))
    hits.sort()
    out = []
    for _, pid in hits[:limit]:
        p = part(pid)
        out.append({'id': p['id'], 'title': p['title'], 'category': p['category'],
                    'colors_produced': len(p['colors']),
                    'colors': [f"{c} {index()['colors'][c]['name']}" for c in p['colors'][:12]]})
    return {'query': query, 'matches': len(hits), 'shown': len(out), 'results': out}
