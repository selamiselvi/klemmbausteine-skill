"""Run with Blender --background --python ... -- MODEL OUTPUT QUALITY."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bricklib import COLORS, VIEWS, shape

args=sys.argv[sys.argv.index('--')+1:]
model_path,out,quality=args[:3]
style=args[3] if len(args)>3 else 'studio'
steps_only=len(args)>4 and args[4]=='steps-only'
model=json.loads(Path(model_path).read_text());out=Path(out)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=20 if quality=='draft' else 48
scene.cycles.use_denoising=True
scene.cycles.seed=0
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('White studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.view_transform='AgX'
scene.render.threads_mode='FIXED';scene.render.threads=6

def material(name,rgb,roughness=.3):
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Roughness'].default_value=roughness
    return m

def linear_hex(v):
    vals=[int(v[i:i+2],16)/255 for i in (1,3,5)]
    return [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals]

mats={id:material(c['name'],linear_hex(c['hex'])) for id,c in COLORS.items()}
muted=material('Earlier steps',(.66,.69,.72),.65)
white=material('Studio floor',(1,1,1),.8)

# Original simplified rectangular meshes. Stud pitches/body heights follow the catalog.
def make_part(p):
    w,d,h=shape(p);W=w*.8-.025;D=d*.8-.025;H=h*.32-.014
    verts=[(x,y,z) for z in (0,H) for y in (-D/2,D/2) for x in (-W/2,W/2)]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    for ix in range(w):
        for iy in range(d):
            cx=(ix+.5-w/2)*.8;cy=(iy+.5-d/2)*.8;n=len(verts);seg=24
            for z in (H,H+.16):
                verts.extend((cx+.24*math.cos(a*math.tau/seg),cy+.24*math.sin(a*math.tau/seg),z) for a in range(seg))
            faces.append(tuple(n+seg+i for i in range(seg)))
            for i in range(seg):faces.append((n+i,n+(i+1)%seg,n+seg+(i+1)%seg,n+seg+i))
    mesh=bpy.data.meshes.new(p['id']);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(p['id'],mesh);scene.collection.objects.link(obj)
    obj.location=((p['x']+w/2)*.8,(p['y']+d/2)*.8,p['z']*.32+.007)
    obj.data.materials.append(mats[p['color']])
    bevel=obj.modifiers.new('Soft molded edges','BEVEL');bevel.width=.012;bevel.segments=2
    bevel.limit_method='ANGLE'
    return obj

def technical_faces(obj,color):
    # Flat face tones retain depth cues without directional scene illumination.
    base=linear_hex(COLORS[color]['hex'])
    if max(base)<.03:base=[.028]*3
    obj.data.materials.clear()
    for i,factor in enumerate((1.0,.76,.54)):
        rgb=[v*factor for v in base]
        obj.data.materials.append(material(f'{color} face {i}',rgb,.8))
    for face in obj.data.polygons:
        face.material_index=0 if face.normal.z>.5 else (1 if abs(face.normal.y)>.5 else 2)

objects={p['id']:make_part(p) for p in model['parts']}
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.02))
plane=bpy.context.object;plane.data.materials.append(white)
plane.is_shadow_catcher=True
# Scale the studio rig to the model so large assemblies remain evenly lit.
min_x=min(p['x'] for p in model['parts'])*.8
min_y=min(p['y'] for p in model['parts'])*.8
max_x=max(p['x']+shape(p)[0] for p in model['parts'])*.8
max_y=max(p['y']+shape(p)[1] for p in model['parts'])*.8
model_height=max(p['z']+shape(p)[2] for p in model['parts'])*.32
rig_center=Vector(((min_x+max_x)/2,(min_y+max_y)/2,0))
rig_scale=max(max_x-min_x,max_y-min_y,model_height)/20
for name,loc,power,size in [('Key',(-7,-9,20),1800,12),('Fill',(12,-2,12),1000,10),('Rim',(1,12,18),1500,8)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power*rig_scale**2;data.shape='DISK';data.size=size*rig_scale
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=rig_center+Vector(loc)*rig_scale
    o.rotation_euler=(rig_center+Vector((0,0,model_height*.4))-o.location).to_track_quat('-Z','Y').to_euler()
cam_data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cam_data)
scene.collection.objects.link(cam);scene.camera=cam;cam_data.type='ORTHO';cam_data.lens=50

def frame(parts,view):
    bounds=[]
    for p in parts:
        w,d,h=shape(p)
        for x in (p['x']*.8,(p['x']+w)*.8):
            for y in (p['y']*.8,(p['y']+d)*.8):
                for z in (p['z']*.32,(p['z']+h)*.32+.16):bounds.append(Vector((x,y,z)))
    center=(Vector(tuple(min(v[i] for v in bounds) for i in range(3)))+Vector(tuple(max(v[i] for v in bounds) for i in range(3))))/2
    dx,dy=VIEWS[view];cam.location=center+Vector((dx,dy,1))*25
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    rot=cam.rotation_euler.to_matrix().transposed();coords=[rot@(p-center) for p in bounds]
    # Uneven skylines need the projected bounds centered, not the 3D box center.
    offset=Vector(((min(v.x for v in coords)+max(v.x for v in coords))/2,
                   (min(v.y for v in coords)+max(v.y for v in coords))/2,0))
    cam.location+=rot.transposed()@offset
    cam_data.ortho_scale=max(max(v.x for v in coords)-min(v.x for v in coords),max(v.y for v in coords)-min(v.y for v in coords))*1.22

def render(name,parts,view,size):
    frame(parts,view);scene.render.resolution_x=size;scene.render.resolution_y=size
    scene.render.filepath=str(out/name);bpy.ops.render.render(write_still=True)

if not steps_only:
    for view in VIEWS:render(f'renders/{view}.png',model['parts'],view,720 if quality=='draft' else 1200)

edges={}
if style=='technical':
    # Workbench supplies restrained face shading without studio shadows or gloss.
    scene.render.engine='BLENDER_WORKBENCH'
    scene.view_settings.view_transform='Standard'
    shading=scene.display.shading
    shading.light='FLAT';shading.color_type='MATERIAL'
    shading.show_shadows=False;shading.show_specular_highlight=False
    shading.show_cavity=True;shading.cavity_type='SCREEN'
    shading.curvature_ridge_factor=.2;shading.curvature_valley_factor=1.2
    shading.show_object_outline=True;shading.object_outline_color=(.10,.13,.16)
    plane.hide_render=True
    for p in model['parts']:technical_faces(objects[p['id']],p['color'])
    accent=material('New part outline',linear_hex('#007da8'))
    # Physical edge curves are depth-tested, so hidden edges stay hidden.
    for p in model['parts']:
        w,d,h=shape(p);W=w*.8-.025;D=d*.8-.025;H=h*.32-.014
        vertices=[(x,y,z) for z in (0,H) for y in (-D/2,D/2) for x in (-W/2,W/2)]
        curve=bpy.data.curves.new('Outline '+p['id'],'CURVE');curve.dimensions='3D'
        curve.bevel_depth=.012;curve.bevel_resolution=1
        for a,b in [(0,1),(1,3),(3,2),(2,0),(4,5),(5,7),(7,6),(6,4),(0,4),(1,5),(2,6),(3,7)]:
            line=curve.splines.new('POLY');line.points.add(1)
            line.points[0].co=(*vertices[a],1);line.points[1].co=(*vertices[b],1)
        obj=bpy.data.objects.new('Outline '+p['id'],curve);scene.collection.objects.link(obj)
        obj.location=objects[p['id']].location;obj.data.materials.append(accent)
        edges[p['id']]=obj

by={p['id']:p for p in model['parts']};seen=set();view='front-right'
for n,step in enumerate(model['steps'],1):
    current=set(step['parts']);seen|=current;view=step.get('view',view)
    for id,obj in objects.items():
        obj.hide_render=id not in seen
        if style!='technical':obj.data.materials[0]=mats[by[id]['color']] if id in current else muted
    for id,obj in edges.items():obj.hide_render=id not in current
    render(f'instructions/step-{n:03}.png',[by[id] for id in sorted(seen)],view,640 if quality=='draft' else 1000)
if style=='technical':
    for obj in [*objects.values(),*edges.values()]:obj.hide_render=True
    (out/'instructions/parts').mkdir(exist_ok=True)
    from bricklib import inventory
    for item in inventory(model['parts']):
        p=dict(id='icon',part=item['part_id'],color=item['color_id'],x=0,y=0,z=0,rotation=0)
        obj=make_part(p)
        technical_faces(obj,p['color'])
        render(f'instructions/parts/{p["part"]}-{p["color"]}.png',[p],'front-right',320)
        bpy.data.objects.remove(obj,do_unlink=True)
print('BRICK_RENDER_COMPLETE',flush=True)
