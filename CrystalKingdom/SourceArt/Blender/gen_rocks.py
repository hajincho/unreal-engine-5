"""Procedural rock assets: faceted boulders, cliffs, walkable plateaus, submerged rocks,
rubble and ceiling rock spikes.

run: blender --background --factory-startup --python gen_rocks.py
"""
import math
import os
import random
import sys

import bmesh
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_common as C  # noqa: E402

MAT = "M_Rock"


def append_bm(mb, bm, mat, smooth=True, zmin=None, zmax=None):
    zs = [v.co.z for v in bm.verts]
    z0 = min(zs) if zmin is None else zmin
    z1 = max(zs) if zmax is None else zmax
    for f in bm.faces:
        pts = [tuple(v.co) for v in f.verts]
        g = [(v.co.z - z0) / max(z1 - z0, 1e-3) for v in f.verts]
        mb.face(pts, mat, smooth=smooth, g=g)


def faceted(rng, size, subdiv=4, cuts=9, rough=0.12, seed_off=None):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    so = Vector(seed_off or (rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50)))
    for v in bm.verts:
        p = v.co.copy()
        v.co = p * (1.0 + 0.25 * C.fbm(p * 1.3 + so, 3))
    planes = []
    for _ in range(cuts):
        n = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 1))).normalized()
        planes.append((n, rng.uniform(0.55, 0.85)))
    for v in bm.verts:
        for n, d in planes:
            k = v.co.dot(n)
            if k > d:
                v.co -= n * (k - d)
    for v in bm.verts:
        p = v.co.copy()
        v.co = p + p.normalized() * rough * C.fbm(p * 6.0 + so, 3) * 0.3
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    return bm


def boulder(mb, rng, s):
    bm = faceted(rng, (s * rng.uniform(0.9, 1.4), s * rng.uniform(0.8, 1.2), s * rng.uniform(0.5, 0.9)))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, s * 0.25))
    append_bm(mb, bm, MAT)
    bm.free()


def cliff(mb, rng, w, h):
    bm = faceted(rng, (w, w * rng.uniform(0.5, 0.8), h), subdiv=5, cuts=14)
    for v in bm.verts:  # horizontal strata ledges
        v.co.x += math.sin(v.co.z * 0.9 + noise.noise(v.co * 0.2) * 3) * 0.04 * w
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h * 0.85))
    append_bm(mb, bm, MAT)
    bm.free()


def plateau(mb, rng, r, top, bottom=-22.0, rings=14, seg=72):
    """Walkable flat-topped rock terrace (pivot at ground center, top at z=top)."""
    so = Vector((rng.uniform(-90, 90), rng.uniform(-90, 90), 0))
    outline = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        k = 1.0 + 0.28 * C.fbm(Vector((math.cos(a), math.sin(a), 0)) * 1.6 + so, 3)
        outline.append((math.cos(a) * r * k, math.sin(a) * r * k))
    zs = [bottom + (top - bottom) * (i / (rings - 1)) for i in range(rings)]
    layers = []
    for zi, z in enumerate(zs):
        t = zi / (rings - 1)
        flare = 1.0 + 0.35 * (1 - t) ** 2  # wider base
        ring = []
        for (x, y) in outline:
            p = Vector((x, y, z))
            d = 1.0 + 0.10 * C.fbm(p * 0.07 + so, 4) + 0.03 * math.sin(z * 1.3 + noise.noise(p * 0.1) * 4)
            ring.append((x * flare * d, y * flare * d, z + (0.0 if zi == rings - 1 else rng.uniform(-0.3, 0.3))))
        layers.append(ring)
    # rim bevel + top
    rim = [(x * 0.97, y * 0.97, top + 0.25) for (x, y, _) in layers[-1]]
    layers.append(rim)
    for k in range(len(layers) - 1):
        a, b = layers[k], layers[k + 1]
        ta, tb = k / len(layers), (k + 1) / len(layers)
        for i in range(seg):
            j = (i + 1) % seg
            mb.face([a[i], a[j], b[j], b[i]], MAT, smooth=True, g=[ta, ta, tb, tb])
    # top surface: concentric rings toward center for a well-tessellated walkable cap
    prev = rim
    for s in (0.8, 0.6, 0.4, 0.2):
        ring = [(x * s / 0.97, y * s / 0.97, top + 0.25 + 0.08 * noise.noise(Vector((x, y, 0)) * 0.3)) for (x, y, _) in rim]
        for i in range(seg):
            j = (i + 1) % seg
            mb.face([prev[i], prev[j], ring[j], ring[i]], MAT, smooth=True, g=[1, 1, 1, 1])
        prev = ring
    c = (0.0, 0.0, top + 0.25)
    for i in range(seg):
        j = (i + 1) % seg
        mb.face([prev[i], prev[j], c], MAT, smooth=True, g=[1, 1, 1])
    mb.face(list(reversed(layers[0])), MAT)


def spike(mb, rng, L, R):
    so = Vector((rng.uniform(-50, 50), rng.uniform(-50, 50), 0))
    seg, rings = 14, 10
    layers = []
    for k in range(rings + 1):
        t = k / rings
        rr = R * (1 - t) ** 1.4 + 0.05
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            p = Vector((math.cos(a), math.sin(a), t * 3))
            d = 1 + 0.3 * C.fbm(p + so, 3)
            ring.append((math.cos(a) * rr * d, math.sin(a) * rr * d, t * L))
        layers.append(ring)
    for k in range(rings):
        a, b = layers[k], layers[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            mb.face([a[i], a[j], b[j], b[i]], MAT, smooth=True, g=[k / rings] * 2 + [(k + 1) / rings] * 2)


def rubble(mb, rng, area, n):
    for _ in range(n):
        s = math.exp(rng.uniform(math.log(0.15), math.log(1.2)))
        bm = faceted(rng, (s, s * rng.uniform(0.6, 1.0), s * rng.uniform(0.4, 0.8)), subdiv=2, cuts=6)
        a = rng.uniform(0, 2 * math.pi)
        r = area * math.sqrt(rng.random())
        bmesh.ops.translate(bm, verts=bm.verts, vec=(r * math.cos(a), r * math.sin(a), s * 0.15))
        mb.piece_rand = rng.random()
        append_bm(mb, bm, MAT)
        bm.free()


def build(name, fn, seed, coll):
    rng = random.Random(seed)
    mb = C.MeshBuilder(name, [MAT])
    fn(mb, rng)
    ob, ucx = mb.finish(coll, uv_scale=0.25, triangulate=True)
    C.export_asset(ob, ucx, "Rocks")
    print("BUILT", name, len(ob.data.polygons))


def main():
    C.reset_scene()
    coll = C.collection("Rocks")
    specs = []
    for i in range(6):
        specs.append(("SM_Rock_Boulder_%02d" % (i + 1), lambda mb, r: boulder(mb, r, r.uniform(1.5, 4.0))))
    for i in range(4):
        specs.append(("SM_Rock_Cliff_%02d" % (i + 1), lambda mb, r: cliff(mb, r, r.uniform(8, 16), r.uniform(14, 30))))
    plateau_specs = [(26, 6), (34, 14), (22, 24), (40, 4), (30, 34), (18, 10)]
    for i, (rad, top) in enumerate(plateau_specs):
        specs.append(("SM_Rock_Plateau_%02d" % (i + 1), lambda mb, r, rad=rad, top=top: plateau(mb, r, rad, top)))
    for i in range(3):
        specs.append(("SM_Rock_Submerged_%02d" % (i + 1), lambda mb, r: boulder(mb, r, r.uniform(2.5, 6.0))))
    for i in range(4):
        specs.append(("SM_Rock_Rubble_%02d" % (i + 1), lambda mb, r: rubble(mb, r, r.uniform(2, 5), r.randint(10, 22))))
    for i in range(4):
        specs.append(("SM_Rock_CeilingSpike_%02d" % (i + 1), lambda mb, r: spike(mb, r, r.uniform(10, 30), r.uniform(3, 7))))
    for k, (name, fn) in enumerate(specs):
        build(name, fn, 500 + k * 31, coll)
    C.save_blend("CK_Rocks")


if __name__ == "__main__":
    main()
