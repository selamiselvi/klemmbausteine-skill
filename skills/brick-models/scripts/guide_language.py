"""Complete text overlays for additional PDFs; geometry and canonical bundles stay unchanged."""
import copy
import re
from bricklib import inventory

LABELS = {
    'building_guide': 'BUILDING GUIDE', 'counts': '{parts} parts / {steps} steps',
    'digital_status': 'Digitally checked · not physically test-built',
    'parts_to_add': 'PARTS TO ADD', 'turn': 'TURN',
    'new_edges': 'Blue edges: parts added in this step', 'inventory': 'Parts inventory',
    'availability': 'LDraw IDs / color availability not checked', 'front': 'FRONT',
    'front-right': 'front right', 'front-left': 'front left',
    'back-right': 'back right', 'back-left': 'back left',
}


def translation_template(model):
    inv = inventory(model['parts'])
    return {'language': 'en', 'title': model['title'], 'description': model['description'],
            'steps': [{'title': s['title'], 'note': s.get('note', '')} for s in model['steps']],
            'labels': dict(LABELS), 'part_names': {p['part_id']: p['part_name'] for p in inv},
            'color_names': {p['color_id']: p['color_name'] for p in inv}}


def translated_model(model, translation):
    template = translation_template(model)
    if not isinstance(translation, dict) or set(translation) != set(template):
        raise ValueError('Translation must contain exactly all template fields')
    if not isinstance(translation['language'], str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', translation['language']):
        raise ValueError('Invalid translation language tag')
    for key in ('labels', 'part_names', 'color_names'):
        if not isinstance(translation[key], dict) or set(translation[key]) != set(template[key]):
            raise ValueError(f'Translation has incomplete or unknown {key}')
    if not isinstance(translation['steps'], list) or len(translation['steps']) != len(model['steps']):
        raise ValueError('Translation must cover every step in order')
    for step in translation['steps']:
        if not isinstance(step, dict) or set(step) != {'title', 'note'}:
            raise ValueError('Each translated step needs exactly title and note')
    def check_text(value, limit=600, empty=False):
        if not isinstance(value, str) or (not empty and not value.strip()) or len(value)>limit or any(ord(c)<32 or ord(c)==127 for c in value):
            raise ValueError('Invalid or oversized translation text')
    check_text(translation['title'], 80)
    check_text(translation['description'])
    for key in ('labels', 'part_names', 'color_names'):
        for text in translation[key].values():
            check_text(text, 160)
    for original, step in zip(model['steps'], translation['steps']):
        check_text(step['title'], 80)
        check_text(step['note'], 240, empty=not bool(original.get('note')))
    from string import Formatter
    tokens = list(Formatter().parse(translation['labels']['counts']))
    if any(spec or conversion for _,_,spec,conversion in tokens):
        raise ValueError('Count placeholders must not contain format specifications or conversions')
    fields = [name for _,name,_,_ in tokens if name is not None]
    if sorted(fields) != ['parts', 'steps']:
        raise ValueError('The translated counts label must retain {parts} and {steps}')
    result = copy.deepcopy(model)
    result.update(title=translation['title'], description=translation['description'])
    for step, localized in zip(result['steps'], translation['steps']):
        step.update(localized)
    return result


def replace_model_text(original, candidate):
    """Allow a canonical text correction while proving all construction data is unchanged."""
    a, b = copy.deepcopy(original), copy.deepcopy(candidate)
    for obj in (a, b):
        for key in ('title', 'description'):
            obj.pop(key, None)
        for step in obj['steps']:
            step.pop('title', None)
            step.pop('note', None)
    if a != b:
        raise ValueError('Text-only refresh cannot change geometry, identity, step membership/order or cameras')
    return candidate
