"""Readable building steps for large models: one step = one compact working area.

Official instruction booklets keep each step's new pieces close together, so the step view can zoom in on them.
`regroup` reorders the pieces *within* each authored phase (consecutive steps sharing a title before " (n/m)") into
compact steps, without ever placing a piece before the pieces it connects to that came earlier in the authored order.
`spread_warnings` reports steps whose pieces are scattered over a large part of the model.
"""
import math
import re
from collections import defaultdict

import assembly


def _phase(title):
    return re.sub(r'\s*\(\d+/\d+\)$', '', title)


def _centre(q):
    e = q.extent()
    return ((e[0] + e[3]) / 2, (e[2] + e[5]) / 2, (e[1] + e[4]) / 2)


def spread_warnings(model, inst=None, limit=0.5, min_model_studs=32):
    """Warn about steps whose new pieces span more than `limit` of the model's footprint (only for large models)."""
    inst = inst or assembly.instances(model)
    ex = [q.extent() for q in inst.values()]
    size = max(max(e[3] for e in ex) - min(e[0] for e in ex), max(e[5] for e in ex) - min(e[2] for e in ex))
    if size < min_model_studs * 20:
        return []
    out = []
    for n, s in enumerate(model['steps'], 1):
        es = [inst[p].extent() for p in s['parts']]
        span = max(max(e[3] for e in es) - min(e[0] for e in es), max(e[5] for e in es) - min(e[2] for e in es))
        largest = max(max(e[3] - e[0], e[5] - e[2]) for e in es)
        if span > limit * size and span > largest + 80:   # a single large plate is not a scattered step
            out.append(f'step {n}: new pieces spread over {round(100 * span / size)} % of the model; group nearby pieces '
                       f'(brick.py regroup) so the zoomed step view stays readable')
    return out


def regroup(model, max_parts=8, max_span=12):
    """New step list: within each phase, greedy compact clusters of at most `max_parts` pieces whose footprint spans at
    most `max_span` studs, respecting the authored dependency order (a piece follows the earlier pieces it connects to)."""
    inst = assembly.instances(model)
    pairs, _ = assembly.connections(inst)
    order = {pid: i for i, pid in enumerate(p for s in model['steps'] for p in s['parts'])}
    after = defaultdict(set)                      # piece -> earlier pieces it is connected to
    for _, a, b in pairs:
        if order[a] < order[b]:
            after[b].add(a)
        elif order[b] < order[a]:
            after[a].add(b)
    phases, current = [], None
    for s in model['steps']:
        t = _phase(s['title'])
        if current is None or current[0] != t:
            current = (t, [], s.get('view'))
            phases.append(current)
        current[1].extend(s['parts'])
    centre = {pid: _centre(q) for pid, q in inst.items()}
    span_ldu = max_span * 20

    def fits(group):
        es = [inst[p].extent() for p in group]
        span = max(max(e[3] for e in es) - min(e[0] for e in es), max(e[5] for e in es) - min(e[2] for e in es))
        largest = max(max(e[3] - e[0], e[5] - e[2]) for e in es)   # big plates alone may exceed max_span
        return span <= max(span_ldu, largest + 80)
    placed, steps = set(), []
    for title, ids, view in phases:
        todo = set(ids)
        chunks = []
        last = None
        while todo:
            ready = [p for p in todo if after[p] <= placed]
            if not ready:                              # authored order inside the phase is the only safe fallback
                ready = [min(todo, key=order.get)]
            # start next to the previous cluster (a sweep), else at the lowest, front-most piece
            ref = last or min((centre[p] for p in ready), key=lambda c: (c[2] * -1, c[1], c[0]))
            seed = min(ready, key=lambda p: (round(-centre[p][2] / 8), math.dist(centre[p][:2], ref[:2]), order[p]))
            chunk = [seed]; todo.discard(seed); placed.add(seed)
            while len(chunk) < max_parts:
                ready = [p for p in todo if after[p] <= placed]
                if not ready:
                    break
                cx = sum(centre[p][0] for p in chunk) / len(chunk); cy = sum(centre[p][1] for p in chunk) / len(chunk)
                cand = min(ready, key=lambda p: (math.dist(centre[p][:2], (cx, cy)), order[p]))
                if not fits(chunk + [cand]):
                    break
                chunk.append(cand); todo.discard(cand); placed.add(cand)
            last = (sum(centre[p][0] for p in chunk) / len(chunk), sum(centre[p][1] for p in chunk) / len(chunk), 0)
            # a tiny chunk joins the previous one when both together still form one compact area
            if chunks and len(chunk) + len(chunks[-1]) <= max_parts and fits(chunks[-1] + chunk):
                chunks[-1].extend(chunk)
            else:
                chunks.append(chunk)
        for k, chunk in enumerate(chunks, 1):
            step = {'title': (title if len(chunks) == 1 else f'{title} ({k}/{len(chunks)})')[:80], 'parts': chunk}
            if view:
                step['view'] = view
            steps.append(step)
    return dict(model, steps=steps)
