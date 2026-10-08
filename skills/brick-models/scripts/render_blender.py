"""Run with Blender --background --python ... -- MODEL OUTPUT QUALITY [STYLE] [steps-only].

Renders the official LDraw geometry of every part (library from setup_runtime.py), placed exactly as model.ldr places it.
Studio views and steps use Cycles; the technical guide uses flat Workbench shading with the parts' own LDraw edge lines
for newly added pieces.
"""
import json
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bricklib import VIEWS, color_hex
import assembly
import ldraw

args = sys.argv[sys.argv.index('--') + 1:]
model_path, out, quality = args[:3]
style = args[3] if len(args) > 3 else 'studio'
steps_only = len(args) > 4 and args[4] == 'steps-only'
views_only = len(args) > 4 and args[4] == 'views-only'
model = json.loads(Path(model_path).read_text()); out = Path(out)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 20 if quality == 'draft' else 48
scene.cycles.use_denoising = True
scene.cycles.seed = 0
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.world = bpy.data.worlds.new('White studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
scene.view_settings.view_transform = 'AgX'
scene.render.threads_mode = 'FIXED'; scene.render.threads = 6

S = 0.04                                   # Blender units per LDU (one stud = 0.8, as in earlier bundles)
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))   # LDraw (x, y down, z) → Blender (x, y, z up); a proper rotation


def linear_hex(v):
    vals = [int(v[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in vals]


def material(name, rgb, roughness=.3, transparent=False, finish='solid'):
    m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1); m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*rgb, 1); bs.inputs['Roughness'].default_value = roughness
    if transparent:
        bs.inputs['Transmission Weight'].default_value = 1.0; bs.inputs['Roughness'].default_value = .05
        bs.inputs['IOR'].default_value = 1.49
    elif finish in ('chrome', 'metal', 'pearlescent', 'matte_metallic'):
        # LDConfig finishes: metallic plastics read as metal, pearlescent ones with a softer sheen.
        # Pearlescent plastic keeps most of its diffuse colour (pearl gold reads gold, not bronze); metal and chrome mirror more.
        bs.inputs['Metallic'].default_value = {'chrome': 1.0, 'metal': .85, 'pearlescent': .45, 'matte_metallic': .6}[finish]
        bs.inputs['Roughness'].default_value = {'chrome': .08, 'metal': .25, 'pearlescent': .28, 'matte_metallic': .45}[finish]
        if finish == 'pearlescent':
            bs.inputs['Coat Weight'].default_value = .4; bs.inputs['Coat Roughness'].default_value = .15
    elif finish == 'rubber':
        bs.inputs['Roughness'].default_value = .8
    return m


def info(code):
    try:
        return ldraw.colors().get(code, {})
    except ValueError:
        return {}


placed = assembly.instances(model)
mats = {}
for p in model['parts']:
    if p['color'] not in mats:
        c = info(p['color'])
        mats[p['color']] = material(f'Colour {p["color"]}', linear_hex(color_hex(p['color'])), transparent=c.get('transparent', False),
                                    finish=c.get('finish', 'solid'))
muted = material('Earlier steps', (.66, .69, .72), .65)
white = material('Studio floor', (1, 1, 1), .8)


def ldraw_matrix(line):
    """World matrix (Blender) of one model.ldr line '1 colour x y z a..i part'."""
    b = line.split(); v = list(map(float, b[2:14]))
    t = Vector(v[:3]); r = Matrix((v[3:6], v[6:9], v[9:12]))
    rot = C @ r @ C.transposed(); loc = (C @ t) * S
    m = rot.to_4x4(); m.translation = loc
    return m


meshes, flats = {}, {}


def flat(part):
    if part not in flats:
        flats[part] = ldraw.flatten(part, with_edges=True)
    return flats[part]


def part_mesh(part):
    """Official geometry for one part ID, shared by all its instances (vertices merged, smoothed by angle)."""
    if part in meshes:
        return meshes[part]
    f = flat(part)
    bm = bmesh.new()
    for tri in f['tris']:
        try:
            bm.faces.new([bm.verts.new(C @ Vector(p) * S) for p in tri])
        except ValueError:
            continue
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.0004)
    mesh = bpy.data.meshes.new('ldraw ' + part); bm.to_mesh(mesh); bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    try:
        mesh.set_sharp_from_angle(angle=0.6)
    except AttributeError:
        pass
    mesh.materials.append(None)
    meshes[part] = mesh
    return mesh


lines = {pid: placed[pid].line() for pid in placed}
objects = {}
for p in model['parts']:
    obj = bpy.data.objects.new(p['id'], part_mesh(p['part']))
    scene.collection.objects.link(obj)
    obj.matrix_world = ldraw_matrix(lines[p['id']])
    obj.material_slots[0].link = 'OBJECT'; obj.material_slots[0].material = mats[p['color']]
    objects[p['id']] = obj

bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -.02))
plane = bpy.context.object; plane.data.materials.append(white); plane.is_shadow_catcher = True


def world_bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector(tuple(min(v[i] for v in pts) for i in range(3))); hi = Vector(tuple(max(v[i] for v in pts) for i in range(3)))
    return pts, lo, hi


_, lo, hi = world_bounds(objects.values())
rig_center = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0)); model_height = hi.z
rig_scale = max(hi.x - lo.x, hi.y - lo.y, model_height) / 20
for name, loc, power, size in [('Key', (-7, -9, 20), 1800, 12), ('Fill', (12, -2, 12), 1000, 10), ('Rim', (1, 12, 18), 1500, 8)]:
    data = bpy.data.lights.new(name, 'AREA'); data.energy = power * rig_scale ** 2; data.shape = 'DISK'; data.size = size * rig_scale
    o = bpy.data.objects.new(name, data); scene.collection.objects.link(o); o.location = rig_center + Vector(loc) * rig_scale
    o.rotation_euler = (rig_center + Vector((0, 0, model_height * .4)) - o.location).to_track_quat('-Z', 'Y').to_euler()
cam_data = bpy.data.cameras.new('Camera'); cam = bpy.data.objects.new('Camera', cam_data)
scene.collection.objects.link(cam); scene.camera = cam; cam_data.type = 'ORTHO'; cam_data.lens = 50


def frame(objs, view):
    bounds, blo, bhi = world_bounds(objs)
    center = (blo + bhi) / 2
    dx, dy = VIEWS[view]; cam.location = center + Vector((dx, dy, 1)) * max(25, (bhi - blo).length * 2)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.clip_end = max(200, (bhi - blo).length * 6)
    rot = cam.rotation_euler.to_matrix().transposed(); coords = [rot @ (p - center) for p in bounds]
    # Uneven skylines need the projected bounds centered, not the 3D box center.
    offset = Vector(((min(v.x for v in coords) + max(v.x for v in coords)) / 2, (min(v.y for v in coords) + max(v.y for v in coords)) / 2, 0))
    cam.location += rot.transposed() @ offset
    cam_data.ortho_scale = max(max(v.x for v in coords) - min(v.x for v in coords), max(v.y for v in coords) - min(v.y for v in coords)) * 1.22


def render(name, objs, view, size):
    frame(objs, view); scene.render.resolution_x = size; scene.render.resolution_y = size
    scene.render.filepath = str(out / name); bpy.ops.render.render(write_still=True)


if not steps_only:
    for view in VIEWS:
        render(f'renders/{view}.png', list(objects.values()), view, 720 if quality == 'draft' else 1200)

if views_only:
    print('BRICK_RENDER_COMPLETE', flush=True)
    sys.exit(0)

tech = {}
if style == 'technical':
    # Workbench supplies restrained face shading without studio shadows or gloss.
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.view_settings.view_transform = 'Standard'
    shading = scene.display.shading
    shading.light = 'FLAT'; shading.color_type = 'MATERIAL'
    shading.show_shadows = False; shading.show_specular_highlight = False
    shading.show_cavity = True; shading.cavity_type = 'SCREEN'
    shading.curvature_ridge_factor = .2; shading.curvature_valley_factor = 1.2
    shading.show_object_outline = True; shading.object_outline_color = (.10, .13, .16)
    plane.hide_render = True
    accent = material('New part outline', linear_hex('#007da8'))

    def tech_mesh(part, color):
        """Per part/colour copy with three flat face tones (top, front/back, sides) for depth without lighting."""
        key = (part, color)
        if key in tech:
            return tech[key]
        mesh = part_mesh(part).copy(); mesh.materials.clear()
        base = linear_hex(color_hex(color))
        if max(base) < .03:
            base = [.028] * 3
        for i, factor in enumerate((1.0, .76, .54)):
            mesh.materials.append(material(f'{color} face {i}', [v * factor for v in base], .8))
        for face in mesh.polygons:
            face.material_index = 0 if abs(face.normal.z) > .5 else (1 if abs(face.normal.y) > .5 else 2)
        tech[key] = mesh
        return mesh

    for p in model['parts']:
        obj = objects[p['id']]; obj.material_slots[0].link = 'DATA'; obj.data = tech_mesh(p['part'], p['color'])

    def outline(p):
        """The part's own LDraw edge lines, as thin depth-tested curves in the new-part accent colour."""
        curve = bpy.data.curves.new('Outline ' + p['id'], 'CURVE'); curve.dimensions = '3D'
        curve.bevel_depth = .006; curve.bevel_resolution = 1
        for a, b in flat(p['part'])['edges']:
            line = curve.splines.new('POLY'); line.points.add(1)
            line.points[0].co = (*(C @ Vector(a) * S), 1); line.points[1].co = (*(C @ Vector(b) * S), 1)
        obj = bpy.data.objects.new('Outline ' + p['id'], curve); scene.collection.objects.link(obj)
        obj.matrix_world = objects[p['id']].matrix_world; obj.data.materials.append(accent)
        return obj

by = {p['id']: p for p in model['parts']}; seen = set(); view = 'front-right'
for n, step in enumerate(model['steps'], 1):
    current = set(step['parts']); seen |= current; view = step.get('view', view)
    for id, obj in objects.items():
        obj.hide_render = id not in seen
        if style != 'technical':
            obj.material_slots[0].material = mats[by[id]['color']] if id in current else muted
    lines_now = [outline(by[id]) for id in step['parts']] if style == 'technical' else []
    render(f'instructions/step-{n:03}.png', [objects[id] for id in sorted(seen)], view, 640 if quality == 'draft' else 1000)
    for o in lines_now:
        curve = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.curves.remove(curve)
if style == 'technical':
    for obj in objects.values():
        obj.hide_render = True
    (out / 'instructions/parts').mkdir(exist_ok=True)
    from bricklib import inventory
    for item in inventory(model['parts']):
        obj = bpy.data.objects.new('icon', tech_mesh(item['part_id'], item['color_id'])); scene.collection.objects.link(obj)
        render(f'instructions/parts/{item["part_id"]}-{item["color_id"]}.png', [obj], 'front-right', 320)
        bpy.data.objects.remove(obj, do_unlink=True)
print('BRICK_RENDER_COMPLETE', flush=True)
