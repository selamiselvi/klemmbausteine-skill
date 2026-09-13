"""Run with Blender --background --python ... -- MODEL OUTPUT QUALITY."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bricklib import COLORS, VIEWS, shape

model_path,out,quality=sys.argv[sys.argv.index('--')+1:]
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
objects={p['id']:make_part(p) for p in model['parts']}
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.02))
plane=bpy.context.object;plane.data.materials.append(white)
plane.is_shadow_catcher=True
for name,loc,power,size in [('Key',(-7,-9,20),1800,12),('Fill',(12,-2,12),1000,10),('Rim',(1,12,18),1500,8)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((3,3,4))-o.location).to_track_quat('-Z','Y').to_euler()
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
    cam_data.ortho_scale=max(max(v.x for v in coords)-min(v.x for v in coords),max(v.y for v in coords)-min(v.y for v in coords))*1.22

def render(name,parts,view,size):
    frame(parts,view);scene.render.resolution_x=size;scene.render.resolution_y=size
    scene.render.filepath=str(out/name);bpy.ops.render.render(write_still=True)

for view in VIEWS:render(f'renders/{view}.png',model['parts'],view,720 if quality=='draft' else 1200)
by={p['id']:p for p in model['parts']};seen=set();view='front-right'
for n,step in enumerate(model['steps'],1):
    current=set(step['parts']);seen|=current;view=step.get('view',view)
    for id,obj in objects.items():
        obj.hide_render=id not in seen
        obj.data.materials[0]=mats[by[id]['color']] if id in current else muted
    render(f'instructions/step-{n:03}.png',[by[id] for id in sorted(seen)],view,640 if quality=='draft' else 1000)
print('BRICK_RENDER_COMPLETE',flush=True)
