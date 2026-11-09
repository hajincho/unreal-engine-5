"""Procedural crystal assets for Crystal Kingdom.

Every crystal grows along local +Z from its pivot (ceiling crystals are rotated 180 deg in UE).
Geometry features: irregular polygonal sections, growth striation rings, asymmetric
rhombohedral terminations, chisel tips, broken tops, twist/taper, satellite crystals.

run: blender --background --factory-startup --python gen_crystals.py
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_common as C  # noqa: E402

MAT = "M_Crystal"


def frame_from_dir(d):
    d = Vector(d).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.99 else Vector((1, 0, 0))
    x = up.cross(d).normalized()
    y = d.cross(x).normalized()
    m = Matrix.Identity(4)
    m.col[0][:3] = x
    m.col[1][:3] = y
    m.col[2][:3] = d
    return m


def crystal(mb, base, direction, length, radius, rng, sides=None, tip="point", twist=0.0,
            taper=0.12, rings=None, flat_top_tilt=0.35, sink=0.6, mat=MAT, rad_jit=(0.72, 1.12), ang_jit=0.35, spin=None):
    """Add one crystal to MeshBuilder mb. base/direction in builder-local space."""
    sides = sides or rng.choice([5, 6, 6, 6, 6, 7, 8])
    # irregular section
    angs = []
    a_off = 0.0 if spin is None else spin   # None keeps the original random stream for existing assets
    for i in range(sides):
        angs.append(a_off + 2 * math.pi * i / sides + rng.uniform(-ang_jit, ang_jit) * math.pi / sides)
    rads = [radius * rng.uniform(*rad_jit) for _ in range(sides)]
    tip_len = length * rng.uniform(0.12, 0.28) if tip in ("point", "chisel") else 0.0
    body = length - tip_len
    nr = rings or max(3, min(14, int(body / max(radius * 0.9, 0.05)) + 2))
    M = Matrix.Translation(Vector(base)) @ frame_from_dir(direction)
    mb.push(M)
    mb.piece_rand = rng.random()
    side_b = [rng.random() for _ in range(sides)]   # one value per prism facet (whole facet reads as one plane)
    tip_b = [rng.random() for _ in range(sides)]
    ring_pts = []
    zs = [-radius * sink] + sorted(rng.uniform(0.05, 0.95) * body for _ in range(nr - 2)) + [body]
    for k, z in enumerate(zs):
        t = max(0.0, z) / length
        s = 1.0 - taper * t
        jitter = 1.0 + (rng.uniform(-0.035, 0.035) if 0 < k < len(zs) - 1 else 0.0)  # striations
        a0 = twist * t
        ring = []
        for i in range(sides):
            a = angs[i] + a0
            r = rads[i] * s * jitter
            ring.append((r * math.cos(a), r * math.sin(a), z))
        ring_pts.append((ring, t))
    for k in range(len(ring_pts) - 1):
        (a, ta), (b, tb) = ring_pts[k], ring_pts[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            mb.face([a[i], a[j], b[j], b[i]], mat, g=[ta, ta, tb, tb], b=side_b[i])
    mb.face(list(reversed(ring_pts[0][0])), mat, g=[0] * sides)
    top, tt = ring_pts[-1]
    if tip == "point":
        off = Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45), 0)) * radius
        apex = (off.x, off.y, length)
        for i in range(sides):
            j = (i + 1) % sides
            mb.face([top[i], top[j], apex], mat, g=[tt, tt, 1.0], b=tip_b[i])
    elif tip == "chisel":
        ax = rng.uniform(0, math.pi)
        h = radius * rng.uniform(0.25, 0.55)
        p1 = (h * math.cos(ax), h * math.sin(ax), length)
        p2 = (-h * math.cos(ax), -h * math.sin(ax), length * rng.uniform(0.96, 1.0))
        # split ring by side of the ridge line
        d = Vector((math.cos(ax), math.sin(ax), 0))
        for i in range(sides):
            j = (i + 1) % sides
            mid = (Vector(top[i]) + Vector(top[j])) * 0.5
            p = p1 if Vector((mid.x, mid.y, 0)).dot(d) > 0 else p2
            mb.face([top[i], top[j], p], mat, g=[tt, tt, 1.0], b=tip_b[i])
        # close the ridge with two triangles toward ring verts nearest the ridge normal
        nrm = Vector((-d.y, d.x, 0))
        ia = max(range(sides), key=lambda i: Vector(top[i][:2] + (0,)).dot(nrm))
        ib = min(range(sides), key=lambda i: Vector(top[i][:2] + (0,)).dot(nrm))
        mb.face([top[ia], p2, p1], mat, g=[tt, 1, 1])
        mb.face([top[ib], p1, p2], mat, g=[tt, 1, 1])
    elif tip == "broken":
        c = (rng.uniform(-0.2, 0.2) * radius, rng.uniform(-0.2, 0.2) * radius, -radius * rng.uniform(0.0, 0.5))
        jag = []
        for i, p in enumerate(top):
            jag.append((p[0] * 0.97, p[1] * 0.97, p[2] + rng.uniform(-0.6, 0.6) * radius))
        for i in range(sides):
            j = (i + 1) % sides
            mb.face([top[i], top[j], jag[j], jag[i]], mat, g=[tt, tt, tt, tt])
        cz = (c[0], c[1], body + c[2])
        for i in range(sides):
            j = (i + 1) % sides
            mb.face([jag[i], jag[j], cz], mat, g=[tt, tt, tt])
    else:  # flat cut (slanted)
        n = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * flat_top_tilt
        cap = [(p[0], p[1], p[2] + n.x * p[0] + n.y * p[1]) for p in top]
        bevel = [(p[0] * 0.9, p[1] * 0.9, p[2] + radius * 0.06) for p in cap]
        for i in range(sides):
            j = (i + 1) % sides
            mb.face([top[i], top[j], cap[j], cap[i]], mat, g=[tt] * 4, b=side_b[i])
            mb.face([cap[i], cap[j], bevel[j], bevel[i]], mat, g=[tt] * 4)
        mb.face(bevel, mat, g=[1.0] * sides, b=tip_b[0])
    mb.pop()


def cone_dir(rng, axis, spread):
    """Random unit vector within a cone of half-angle `spread` (radians) around axis."""
    axis = Vector(axis).normalized()
    ct = rng.uniform(math.cos(spread), 1.0)
    st = math.sqrt(1 - ct * ct)
    ph = rng.uniform(0, 2 * math.pi)
    local = Vector((st * math.cos(ph), st * math.sin(ph), ct))
    return (frame_from_dir(axis).to_3x3() @ local).normalized()


# --------------------------------------------------------------------------- asset types
def cluster(mb, rng, n, base_r, lmin, lmax, spread, axis=(0, 0, 1), tip_mix=(0.75, 0.15, 0.10), rscale=0.13):
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        rr = base_r * math.sqrt(rng.random())
        base = Vector((rr * math.cos(a), rr * math.sin(a), 0))
        d = cone_dir(rng, Vector(axis) + base.normalized() * 0.35 * (rr / max(base_r, 1e-3)), spread)
        L = math.exp(rng.uniform(math.log(lmin), math.log(lmax)))
        tip = rng.choices(["point", "chisel", "broken"], weights=tip_mix)[0]
        crystal(mb, base, d, L, L * rscale * rng.uniform(0.7, 1.3), rng, tip=tip,
                twist=rng.uniform(-0.15, 0.15), taper=rng.uniform(0.0, 0.25))


def giant(mb, rng, L, R, sats, sat_scale=0.45, spread=0.55):
    crystal(mb, (0, 0, 0), cone_dir(rng, (0, 0, 1), 0.08), L, R, rng, sides=rng.choice([6, 6, 7, 8]),
            tip=rng.choice(["point", "point", "chisel"]), twist=rng.uniform(-0.1, 0.1), taper=rng.uniform(0.05, 0.2))
    for _ in range(sats):
        a = rng.uniform(0, 2 * math.pi)
        base = Vector((math.cos(a), math.sin(a), 0)) * R * rng.uniform(0.6, 1.4)
        d = cone_dir(rng, (0, 0, 1), spread)
        l = L * rng.uniform(0.15, sat_scale)
        crystal(mb, base, d, l, l * rng.uniform(0.09, 0.15), rng, tip=rng.choice(["point", "point", "chisel", "broken"]))


def column_mass(mb, rng, w, d, hmin, hmax, spacing):
    """Packed near-vertical crystal columns (the 'crystal skyscraper' masses of the reference)."""
    pts = []
    tries = 0
    while tries < 4000:
        tries += 1
        p = Vector((rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2), 0))
        e = (p.x / (w / 2)) ** 2 + (p.y / (d / 2)) ** 2
        if e > 1.0:
            continue
        if all((p - q).length > spacing * rng.uniform(0.75, 1.0) for q in pts):
            pts.append(p)
    for p in pts:
        e = math.sqrt((p.x / (w / 2)) ** 2 + (p.y / (d / 2)) ** 2)
        h = C.lerp(hmax, hmin, e ** 1.3) * rng.uniform(0.55, 1.15)
        tip = rng.choices(["flat", "point", "chisel", "broken"], weights=(0.45, 0.3, 0.15, 0.1))[0]
        dirv = cone_dir(rng, (0, 0, 1), 0.06 + 0.1 * e)
        crystal(mb, p - Vector((0, 0, 1.0)), dirv, h, spacing * rng.uniform(0.48, 0.62), rng, sides=rng.choice([5, 6, 6, 7]),
                tip=tip, twist=rng.uniform(-0.05, 0.05), taper=rng.uniform(0.0, 0.08), flat_top_tilt=rng.uniform(0.1, 0.6))


def hex_cliff(mb, rng, w, d, h_front, h_back, r):
    """Stepped cliff of tightly packed, near-vertical regular hexagonal columns (the reference's crystal walls).
    Honeycomb packing; heights rise in terraces from the low front (-Y in Blender = +Y in UE after the FBX
    mirror) to the tall back; most tops are flat cuts, a few short points / broken stumps."""
    pitch = r * 1.86                      # centre spacing: columns touch with a thin seam
    row_h = pitch * math.sqrt(3) / 2
    steps = rng.randint(3, 5)             # terrace levels front->back
    ny = int(d / row_h) + 1
    nx = int(w / pitch) + 1
    for j in range(ny):
        y = -d / 2 + j * row_h
        t = j / max(ny - 1, 1)            # 0 front .. 1 back
        level = math.floor(t * steps + rng.uniform(-0.35, 0.35)) / max(steps - 1, 1)
        for i in range(nx):
            x = -w / 2 + i * pitch + (pitch / 2 if j % 2 else 0.0)
            edge = abs(x) / (w / 2)       # ragged, lower side ends
            if edge > 0.92 and rng.random() < 0.5:
                continue
            h = C.lerp(h_front, h_back, min(1.0, max(0.0, level))) * (1.0 - 0.45 * edge ** 2) * rng.uniform(0.82, 1.12)
            if rng.random() < 0.12:       # occasional tall spire breaking the terrace line
                h *= rng.uniform(1.25, 1.6)
            tip = rng.choices(["flat", "point", "broken"], weights=(0.72, 0.18, 0.10))[0]
            rr = r * rng.uniform(0.9, 1.0)
            crystal(mb, (x + rng.uniform(-0.05, 0.05) * r, y, -1.0), cone_dir(rng, (0, 0, 1), 0.025), h, rr, rng, sides=6,
                    tip=tip, taper=0.0, twist=0.0, flat_top_tilt=rng.uniform(0.05, 0.3), rad_jit=(0.97, 1.03), ang_jit=0.04,
                    spin=0.0, sink=0.3)


def branching(mb, rng, L, R):
    d0 = cone_dir(rng, (0, 0, 1), 0.15)
    crystal(mb, (0, 0, 0), d0, L, R, rng, tip="point")
    for _ in range(rng.randint(4, 8)):
        t = rng.uniform(0.15, 0.75)
        base = d0 * (L * t)
        side = cone_dir(rng, d0, 1.2)
        side = (side - d0 * side.dot(d0) * 0.6).normalized()
        l = L * rng.uniform(0.2, 0.5) * (1 - t * 0.5)
        crystal(mb, base, side, l, l * rng.uniform(0.1, 0.14), rng, tip=rng.choice(["point", "chisel"]))


def block(mb, rng, R, H):
    """Chunky hex column stump cut flat — the foreground rubble blocks of the reference."""
    # plan step 7: regular hexagonal stumps with flat (slightly slanted) cuts, like the reference foreground
    crystal(mb, (0, 0, -0.3), cone_dir(rng, (0, 0, 1), 0.12), H, R, rng, sides=6, tip=rng.choice(["flat", "flat", "flat", "broken"]),
            taper=0.0, rings=rng.randint(3, 4), flat_top_tilt=rng.uniform(0.08, 0.3), sink=0.2, rad_jit=(0.95, 1.04), ang_jit=0.06,
            spin=rng.uniform(0, 1.0))
    for _ in range(rng.randint(1, 3)):
        a = rng.uniform(0, 2 * math.pi)
        base = Vector((math.cos(a), math.sin(a), 0)) * R * 1.75
        crystal(mb, base, cone_dir(rng, (0, 0, 1), 0.15), H * rng.uniform(0.35, 0.85), R * rng.uniform(0.45, 0.7), rng, sides=6,
                tip=rng.choice(["flat", "flat", "broken"]), taper=0.0, rings=3, rad_jit=(0.95, 1.04), ang_jit=0.06, spin=rng.uniform(0, 1.0))


def opal(mb, rng, L, R):
    crystal(mb, (0, 0, 0), cone_dir(rng, (0, 0, 1), 0.2), L, R, rng, sides=rng.choice([9, 10, 11, 12]), tip="point",
            taper=0.35, twist=rng.uniform(-0.4, 0.4))
    for _ in range(rng.randint(2, 4)):
        a = rng.uniform(0, 2 * math.pi)
        base = Vector((math.cos(a), math.sin(a), 0)) * R * 0.9
        l = L * rng.uniform(0.3, 0.6)
        crystal(mb, base, cone_dir(rng, (0, 0, 1), 0.6), l, l * 0.22, rng, sides=rng.choice([8, 9, 10]), tip="point", taper=0.35)


def broken_pile(mb, rng, R):
    # stump with broken top + toppled fragments lying around
    crystal(mb, (0, 0, 0), cone_dir(rng, (0, 0, 1), 0.2), R * rng.uniform(3, 6), R, rng, tip="broken", taper=0.02)
    for _ in range(rng.randint(3, 6)):
        a = rng.uniform(0, 2 * math.pi)
        base = Vector((math.cos(a), math.sin(a), 0)) * R * rng.uniform(1.8, 4.0)
        d = Vector((math.cos(a + rng.uniform(-1, 1)), math.sin(a + rng.uniform(-1, 1)), rng.uniform(-0.05, 0.2))).normalized()
        l = R * rng.uniform(1.5, 3.5)
        crystal(mb, base + Vector((0, 0, 0.1)), d, l, R * rng.uniform(0.35, 0.7), rng, tip=rng.choice(["broken", "point"]), taper=0.05)


# --------------------------------------------------------------------------- build all
def build(name, fn, seed, coll):
    rng = random.Random(seed)
    mb = C.MeshBuilder(name, [MAT])
    fn(mb, rng)
    ob, ucx = mb.finish(coll, uv_scale=0.25, triangulate=False)
    bevel_edges(ob)
    C.export_asset(ob, ucx, "Crystals")
    dg = bpy.context.evaluated_depsgraph_get()
    tris = sum(len(p.vertices) - 2 for p in ob.evaluated_get(dg).data.polygons)
    print("BUILT", name, "tris", tris)
    return ob


def bevel_edges(ob, pct=7.0, angle_deg=28.0):
    """Chamfer every facet edge so it catches a thin highlight (the reference crystals have bright
    edges). Width scales with each crystal (percent of the adjacent edge); harden_normals keeps the
    facets themselves flat-shaded while the bevel strip rolls the normal over."""
    ob.data.shade_smooth()
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.offset_type = "PERCENT"
    m.width_pct = pct
    m.segments = 1   # was 2: one chamfer still catches the edge highlight; ~35% fewer triangles (matters on non-Nanite GPUs)
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle_deg)
    m.harden_normals = True
    m.use_clamp_overlap = True
    m.miter_outer = "MITER_ARC"
    t = ob.modifiers.new("Triangulate", "TRIANGULATE")
    t.keep_custom_normals = True


def main():
    C.reset_scene()
    coll = C.collection("Crystals")
    specs = []
    for i in range(5):
        specs.append(("SM_Crystal_CeilingGiant_%02d" % (i + 1), lambda mb, r: giant(mb, r, r.uniform(30, 60), r.uniform(3.0, 5.5), r.randint(4, 9))))
    for i in range(4):
        specs.append(("SM_Crystal_FloorGiant_%02d" % (i + 1), lambda mb, r: giant(mb, r, r.uniform(28, 55), r.uniform(3.5, 6.0), r.randint(5, 10), 0.5, 0.45)))
    for i in range(5):
        specs.append(("SM_Crystal_Pillar_%02d" % (i + 1), lambda mb, r: crystal(mb, (0, 0, 0), cone_dir(r, (0, 0, 1), 0.06), r.uniform(6, 15), r.uniform(0.8, 1.6), r, tip=r.choice(["point", "chisel", "flat"]))))
    for i in range(4):
        specs.append(("SM_Crystal_Leaning_%02d" % (i + 1), lambda mb, r: crystal(mb, (0, 0, 0), cone_dir(r, (1, 0, 1.4), 0.15), r.uniform(8, 18), r.uniform(0.9, 1.7), r, tip=r.choice(["point", "chisel"]), twist=r.uniform(-0.2, 0.2))))
    for i in range(4):
        specs.append(("SM_Crystal_Branch_%02d" % (i + 1), lambda mb, r: branching(mb, r, r.uniform(8, 16), r.uniform(0.9, 1.5))))
    for i in range(4):
        specs.append(("SM_Crystal_Wall_%02d" % (i + 1), lambda mb, r: cluster(mb, r, r.randint(14, 24), r.uniform(4, 8), 1.5, 9.0, 0.9)))
    for i in range(5):
        specs.append(("SM_Crystal_FloorCluster_%02d" % (i + 1), lambda mb, r: cluster(mb, r, r.randint(10, 26), r.uniform(0.8, 2.0), 0.25, 2.2, 0.6)))
    for i in range(4):
        specs.append(("SM_Crystal_Broken_%02d" % (i + 1), lambda mb, r: broken_pile(mb, r, r.uniform(0.6, 1.4))))
    for i in range(3):
        specs.append(("SM_Crystal_Glow_%02d" % (i + 1), lambda mb, r: cluster(mb, r, r.randint(3, 6), r.uniform(0.6, 1.2), 2.0, 7.0, 0.35, rscale=0.16)))
    for i in range(3):
        specs.append(("SM_Crystal_Opal_%02d" % (i + 1), lambda mb, r: opal(mb, r, r.uniform(3, 7), r.uniform(0.7, 1.3))))
    for i in range(6):
        specs.append(("SM_Crystal_ColumnMass_%02d" % (i + 1), lambda mb, r: column_mass(mb, r, r.uniform(22, 40), r.uniform(14, 26), 15, r.uniform(70, 130), r.uniform(3.5, 6.0))))
    for i in range(6):  # plan step 3: reference-style hex column cliffs
        specs.append(("SM_Crystal_HexCliff_%02d" % (i + 1), lambda mb, r: hex_cliff(mb, r, r.uniform(30, 46), r.uniform(14, 22),
                                                                                   r.uniform(8, 18), r.uniform(55, 105), r.uniform(1.8, 2.8))))
    for i in range(5):
        specs.append(("SM_Crystal_Block_%02d" % (i + 1), lambda mb, r: block(mb, r, r.uniform(1.1, 2.0), r.uniform(1.2, 3.0))))
    for i in range(6):
        specs.append(("SM_Crystal_Shard_%02d" % (i + 1), lambda mb, r: cluster(mb, r, r.randint(4, 9), 0.25, 0.08, 0.5, 1.2)))
    only = os.environ.get("CK_ONLY")
    for k, (name, fn) in enumerate(specs):
        if only and only not in name:
            continue
        build(name, fn, 1000 + k * 17, coll)
    C.save_blend("CK_Crystals" if not only else "CK_Crystals_" + only)   # partial runs must not overwrite the full .blend


if __name__ == "__main__":
    main()
