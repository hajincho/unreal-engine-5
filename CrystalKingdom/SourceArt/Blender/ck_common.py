"""Shared helpers for Crystal Kingdom Blender generators (Blender 5.2, run headless).

Conventions
- Units: meters in Blender (FBX export -> UE centimeters).
- Every exported asset is one object named SM_* with pivot at the world origin.
- Vertex color "Col" (linear): R = piece random, G = 0..1 along growth axis, B = face random.
- Optional UCX_<name>_NN convex collision objects are exported in the same FBX.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # CrystalKingdom/
EXPORT = os.path.join(ROOT, "SourceArt", "Export")
TEXOUT = os.path.join(ROOT, "SourceArt", "Textures")


# --------------------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0


def get_material(name, color=(0.6, 0.6, 0.6, 1.0)):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.diffuse_color = color
    return m


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


# --------------------------------------------------------------------------- builder
class MeshBuilder:
    """Accumulates geometry in one bmesh with material slots, a transform stack,
    per-corner vertex colors and optional UCX collision hulls."""

    def __init__(self, name, materials):
        self.name = name
        self.materials = list(materials)
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new("Col")
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.stack = [Matrix.Identity(4)]
        self.ucx = []  # list of point lists (world space)
        self.piece_rand = 0.5

    # transform stack
    @property
    def M(self):
        return self.stack[-1]

    def push(self, m):
        self.stack.append(self.M @ m)

    def pop(self):
        self.stack.pop()

    def mat_index(self, mat):
        if mat not in self.materials:
            self.materials.append(mat)
        return self.materials.index(mat)

    # raw face
    def face(self, pts, mat, smooth=False, g=None, local=True, b=None):
        M = self.M
        vs = [self.bm.verts.new((M @ Vector(p)) if local else Vector(p)) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mat_index(mat)
        f.smooth = smooth
        fr = random.random() if b is None else b
        for i, l in enumerate(f.loops):
            gv = g[i] if g is not None else 0.0
            l[self.col] = (self.piece_rand, gv, fr, 1.0)
        return f

    ucx_enabled = True

    def add_ucx(self, pts_local, force=False):
        if not self.ucx_enabled and not force:
            return
        M = self.M
        self.ucx.append([M @ Vector(p) for p in pts_local])

    # primitives -------------------------------------------------------------
    def box(self, mat, c, s, collide=False, smooth=False):
        cx, cy, cz = c
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        p = [(cx + x * hx, cy + y * hy, cz + z * hz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        # indices: x,y,z bits -> 0..7 = (-,-,-),(-,-,+),(-,+,-),(-,+,+),(+,-,-),(+,-,+),(+,+,-),(+,+,+)
        quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for q in quads:
            self.face([p[i] for i in q], mat, smooth)
        if collide:
            self.add_ucx(p)

    def prism(self, mat, poly, z0, z1, cap_bottom=True, cap_top=True, collide=False, smooth=False):
        """Vertical extrusion of a CCW 2D polygon."""
        n = len(poly)
        bot = [(x, y, z0) for x, y in poly]
        top = [(x, y, z1) for x, y in poly]
        for i in range(n):
            j = (i + 1) % n
            self.face([bot[i], bot[j], top[j], top[i]], mat, smooth)
        if cap_top:
            self.face(top, mat)
        if cap_bottom:
            self.face(list(reversed(bot)), mat)
        if collide:
            self.add_ucx(bot + top)

    def cyl(self, mat, c, r, h, sides=12, r_top=None, cap=True, collide=False, smooth=True):
        r_top = r if r_top is None else r_top
        cx, cy, cz = c
        b = [(cx + r * math.cos(2 * math.pi * i / sides), cy + r * math.sin(2 * math.pi * i / sides), cz) for i in range(sides)]
        t = [(cx + r_top * math.cos(2 * math.pi * i / sides), cy + r_top * math.sin(2 * math.pi * i / sides), cz + h) for i in range(sides)]
        for i in range(sides):
            j = (i + 1) % sides
            self.face([b[i], b[j], t[j], t[i]], mat, smooth)
        if cap:
            if r_top > 1e-4:
                self.face(t, mat)
            self.face(list(reversed(b)), mat)
        if collide:
            self.add_ucx(b + t)

    def lathe(self, mat, c, profile, sides=12, smooth=True):
        """profile: list of (r, z) bottom->top, revolved around local Z at c."""
        cx, cy, cz = c
        rings = []
        for r, z in profile:
            rings.append([(cx + r * math.cos(2 * math.pi * i / sides), cy + r * math.sin(2 * math.pi * i / sides), cz + z) for i in range(sides)])
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            for i in range(sides):
                j = (i + 1) % sides
                self.face([a[i], a[j], b[j], b[i]], mat, smooth)
        if profile[0][0] > 1e-4:
            self.face(list(reversed(rings[0])), mat)
        if profile[-1][0] > 1e-4:
            self.face(rings[-1], mat)

    def slab_xz(self, outline, y0, y1, mat="M_Stone", collide=False):
        """Extrude a 2D outline drawn in the XZ plane (CCW seen from -Y) between y0..y1."""
        n = len(outline)
        f = [(x, y0, z) for x, z in outline]
        b = [(x, y1, z) for x, z in outline]
        self.face(list(reversed(f)), mat)
        self.face(b, mat)
        for i in range(n):
            j = (i + 1) % n
            self.face([f[i], f[j], b[j], b[i]], mat)
        if collide:
            self.add_ucx(f + b)

    # ------------------------------------------------------------------ output
    def finish(self, coll=None, uv_scale=0.5, triangulate=True, recalc=False):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if triangulate:
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        box_uv(bm, self.uv, uv_scale)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(self.name, me)
        for m in self.materials:
            me.materials.append(get_material(m))
        (coll or bpy.context.scene.collection).objects.link(ob)
        ucx_objs = []
        for i, pts in enumerate(self.ucx):
            ucx_objs.append(make_hull("UCX_%s_%02d" % (self.name, i), pts, coll))
        return ob, ucx_objs


def make_hull(name, pts, coll=None):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    # remove interior/unused verts
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.display_type = "WIRE"
    return ob


def box_uv(bm, uv_layer, scale=0.5):
    """Box projection UVs in world meters * scale (scale 0.5 -> 1 UV tile per 2 m)."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        for l in f.loops:
            co = l.vert.co
            if ax == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            elif ax == 1:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            else:
                u, v = co.x, co.y * (1 if n.z > 0 else -1)
            l[uv_layer].uv = (u * scale, v * scale)


# --------------------------------------------------------------------------- export
def export_fbx(objs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={"MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        bake_space_transform=False,
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        colors_type="LINEAR",
        add_leaf_bones=False,
        path_mode="STRIP",
        axis_forward="-Z",
        axis_up="Y",
    )


def export_asset(ob, ucx, subdir):
    path = os.path.join(EXPORT, subdir, ob.name + ".fbx")
    export_fbx([ob] + list(ucx), path)
    return path


def save_blend(name):
    path = os.path.join(HERE, name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    return path


# --------------------------------------------------------------------------- noise
def fbm(p, octaves=5, lac=2.0, gain=0.5):
    a, f, s = 1.0, 1.0, 0.0
    for _ in range(octaves):
        s += a * noise.noise(Vector(p) * f)
        a *= gain
        f *= lac
    return s


def ridged(p, octaves=4):
    a, f, s = 1.0, 1.0, 0.0
    for _ in range(octaves):
        s += a * (1.0 - abs(noise.noise(Vector(p) * f)))
        a *= 0.5
        f *= 2.0
    return s


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t
