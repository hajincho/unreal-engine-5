"""Contact-sheet preview of generated assets (Workbench render).
usage: blender -b <file.blend> --python preview.py -- <out.png> <name_substr,...>
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
subs = argv[1].split(",") if len(argv) > 1 else [""]
objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("UCX_") and any(s in o.name for s in subs)]
for o in bpy.data.objects:
    o.hide_render = o not in objs
# grid layout by bounding size
cols = max(1, math.ceil(math.sqrt(len(objs))))
x = y = 0.0
rowh = 0.0
for i, o in enumerate(objs):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    size = max((max(v[k] for v in bb) - min(v[k] for v in bb)) for k in range(3))
    o.location = (x - min(v.x for v in bb) + o.location.x, y - min(v.y for v in bb) + o.location.y, o.location.z)
    x += size * 1.15
    rowh = max(rowh, size)
    if (i + 1) % cols == 0:
        x = 0.0
        y += rowh * 1.15
        rowh = 0.0
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (mn + mx) / 2
rad = (mx - mn).length / 2
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.scene.collection.objects.link(cam)
d = Vector((0.55, -1.0, 0.55)).normalized()
cam.location = ctr + d * rad * 2.3
cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 40
cam.data.clip_end = 100000
sc = bpy.context.scene
sc.camera = cam
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_cavity = True
sc.display.shading.show_shadows = True
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.render.filepath = out
for m in bpy.data.materials:
    m.diffuse_color = {"M_Stone": (0.75, 0.72, 0.66, 1), "M_StoneTrim": (0.9, 0.88, 0.82, 1), "M_Roof": (0.35, 0.55, 0.6, 1),
                       "M_WindowGlow": (1.0, 0.7, 0.2, 1), "M_Door": (0.3, 0.2, 0.12, 1), "M_Crystal": (0.55, 0.85, 0.9, 1)}.get(m.name, (0.6, 0.6, 0.6, 1))
bpy.ops.render.render(write_still=True)
print("PREVIEW", out, len(objs))
