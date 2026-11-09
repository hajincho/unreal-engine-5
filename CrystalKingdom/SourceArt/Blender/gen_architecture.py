"""Gothic-fantasy architecture for Crystal Kingdom: modular exterior pieces and composite
buildings assembled from those modules. Exterior only — doors are closed, no interiors.

Module local frame: X = along the facade, -Y = facade front, Z = up, pivot at bottom-left-front.
Materials: M_Stone (walls), M_StoneTrim (carved trim), M_Roof, M_WindowGlow (warm emissive), M_Door.
Collision: UCX_ boxes for walls, floors, decks, stair ramps (walkable surfaces stay simple).

run: blender --background --factory-startup --python gen_architecture.py
"""
import math
import os
import random
import sys

from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_common as C  # noqa: E402

ST, TR, RF, GL, DR = "M_Stone", "M_StoneTrim", "M_Roof", "M_WindowGlow", "M_Door"
FH = 4.2   # house storey (floor-to-floor) in metres - was 6.0, which made houses read ~1.5x too tall
TFH = 4.5  # tower storey
MATS = [ST, TR, RF, GL, DR]


def T(x=0.0, y=0.0, z=0.0, rz=0.0, s=1.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rz), 4, "Z") @ Matrix.Scale(s, 4)


def place(mb, fn, x=0.0, y=0.0, z=0.0, rz=0.0, **kw):
    mb.push(T(x, y, z, rz))
    fn(mb, **kw)
    mb.pop()


# --------------------------------------------------------------------------- curves
def pointed_arch(x0, x1, zs, k=0.85, n=12):
    """Pointed (k>0.5) or round (k=0.5) arch from left to right springing, in XZ."""
    w = x1 - x0
    R = k * w
    xm = (x0 + x1) * 0.5
    ca = max(-1.0, min(1.0, (xm - (x0 + R)) / R))
    ta = math.acos(ca)
    left = [(x0 + R + R * math.cos(th), zs + R * math.sin(th)) for th in [math.pi + (ta - math.pi) * i / n for i in range(n + 1)]]
    right = [(x1 - R + R * math.cos(th), zs + R * math.sin(th)) for th in [(math.pi - ta) * (1 - i / n) for i in range(n + 1)]]
    return left + right[1:]


def arch_apex(x0, x1, zs, k):
    w = x1 - x0
    R = k * w
    return zs + math.sqrt(max(R * R - (R - w / 2) ** 2, 0.0))


def arch_ring(mb, mat, x0, x1, zs, k, th, y0, y1, n=12):
    w = x1 - x0
    R = k * w
    inner = pointed_arch(x0, x1, zs, k, n)
    outer = pointed_arch(x0 - th, x1 + th, zs, (R + th) / (w + 2 * th), n)
    for a in range(len(inner) - 1):
        i0, i1, o0, o1 = inner[a], inner[a + 1], outer[a], outer[a + 1]
        mb.face([(i0[0], y0, i0[1]), (o0[0], y0, o0[1]), (o1[0], y0, o1[1]), (i1[0], y0, i1[1])], mat)
        mb.face([(i0[0], y1, i0[1]), (i1[0], y1, i1[1]), (o1[0], y1, o1[1]), (o0[0], y1, o0[1])], mat)
        mb.face([(i0[0], y0, i0[1]), (i1[0], y0, i1[1]), (i1[0], y1, i1[1]), (i0[0], y1, i0[1])], mat)
        mb.face([(o0[0], y0, o0[1]), (o0[0], y1, o0[1]), (o1[0], y1, o1[1]), (o1[0], y0, o1[1])], mat)
    for p, q in ((inner[0], outer[0]), (inner[-1], outer[-1])):
        mb.face([(p[0], y0, p[1]), (p[0], y1, p[1]), (q[0], y1, q[1]), (q[0], y0, q[1])], mat)


def xz_face(mb, mat, outline, y):
    mb.face([(x, y, z) for x, z in outline], mat)


# --------------------------------------------------------------------------- small parts
def cornice(mb, x0, x1, z, y=0.0, depth=0.35, mat=TR):
    L = x1 - x0
    xc = (x0 + x1) / 2
    for i, (dz, dd) in enumerate(((0.0, 0.12), (0.14, 0.24), (0.28, depth))):
        mb.box(mat, (xc, y - dd / 2 + 0.01, z + dz + 0.07), (L + dd * 0.6, dd, 0.14))


def plinth(mb, x0, x1, y=0.0, h=0.7, d=0.18, mat=TR):
    mb.box(mat, ((x0 + x1) / 2, y - d / 2, h / 2), (x1 - x0 + d * 0.5, d, h))


def baluster(mb, x, y, z0, h, r=0.09, mat=TR):
    prof = [(r * 1.2, 0.0), (r * 1.2, 0.06), (r * 0.7, 0.1), (r * 1.25, h * 0.35), (r * 0.55, h * 0.75), (r * 0.8, h * 0.9), (r * 1.1, h)]
    mb.lathe(mat, (x, y, z0), prof, sides=8)


def balustrade(mb, L=4.0, h=1.1, t=0.32, collide=True):
    mb.box(TR, (L / 2, t / 2, 0.09), (L, t, 0.18))                 # base rail
    mb.box(TR, (L / 2, t / 2, h - 0.08), (L + 0.04, t + 0.08, 0.16))  # top rail
    n = max(2, int(L / 0.32))
    for i in range(n):
        baluster(mb, (i + 0.5) * L / n, t / 2, 0.18, h - 0.34)
    mb.box(TR, (0.12, t / 2, h / 2), (0.24, t + 0.04, h))
    if collide:
        mb.add_ucx([(x, y, z) for x in (0, L) for y in (0, t) for z in (0, h)])


def finial(mb, x=0.0, y=0.0, z=0.0, s=1.0, mat=TR):
    prof = [(0.25 * s, 0), (0.18 * s, 0.25 * s), (0.28 * s, 0.45 * s), (0.08 * s, 0.9 * s), (0.14 * s, 1.1 * s), (0.0, 1.6 * s)]
    mb.lathe(mat, (x, y, z), prof, sides=8)


def pinnacle(mb, x=0.0, y=0.0, z=0.0, s=1.0):
    mb.box(TR, (x, y, z + 0.9 * s), (0.7 * s, 0.7 * s, 1.8 * s))
    mb.cyl(TR, (x, y, z + 1.8 * s), 0.5 * s, 2.4 * s, sides=4, r_top=0.0, smooth=False)
    finial(mb, x, y, z + 4.0 * s, 0.35 * s)


def crenels(mb, L=4.0, t=0.6, z=0.0, n=4):
    mb.box(ST, (L / 2, t / 2, z + 0.35), (L, t, 0.7), collide=True)
    for i in range(n):
        x = (i + 0.5) * L / n
        mb.box(ST, (x, t / 2, z + 0.7 + 0.45), (L / n * 0.55, t, 0.9))


def buttress(mb, h=8.0, d=1.6, w=0.9):
    steps = 3
    for i in range(steps):
        z0 = h * i / steps
        z1 = h * (i + 1) / steps
        dd = d * (1 - i / steps * 0.45)
        mb.box(ST, (0, -dd / 2, (z0 + z1) / 2), (w, dd, z1 - z0))
        mb.slab_xz([(-w / 2, z1), (w / 2, z1), (w / 2, z1 + 0.5), (-w / 2, z1 + 0.5)], -dd, -dd * 0.5)
    pinnacle(mb, 0, -d * 0.35, h, 0.45)


# --------------------------------------------------------------------------- wall modules
def wall_opening(mb, w, h, t, ox0, ox1, oz0, zs, kind="pointed", k=0.85, mat=ST):
    mb.box(mat, (ox0 / 2, t / 2, h / 2), (ox0, t, h), collide=True)
    mb.box(mat, ((ox1 + w) / 2, t / 2, h / 2), (w - ox1, t, h), collide=True)
    if oz0 > 0:
        mb.box(mat, ((ox0 + ox1) / 2, t / 2, oz0 / 2), (ox1 - ox0, t, oz0), collide=True)
    if kind == "rect":
        mb.box(mat, ((ox0 + ox1) / 2, t / 2, (zs + h) / 2), (ox1 - ox0, t, h - zs), collide=True)
    else:
        arch = pointed_arch(ox0, ox1, zs, k)
        outline = arch + [(ox1, h), (ox0, h)]
        mb.slab_xz(outline, 0.0, t, collide=True)


def wall_plain(mb, w=4.0, h=6.0, t=0.8):
    mb.box(ST, (w / 2, t / 2, h / 2), (w, t, h), collide=True)
    plinth(mb, 0, w)
    cornice(mb, 0, w, h - 0.42)


def wall_deco(mb, w=4.0, h=6.0, t=0.8):
    wall_plain(mb, w, h, t)
    for x in (0.25, w - 0.25):
        mb.box(TR, (x, -0.12, h / 2), (0.5, 0.24, h - 0.4))
    mb.box(TR, (w / 2, -0.08, h * 0.45), (w, 0.16, 0.22))
    # blind arcade relief (two small pointed arches)
    for i in range(2):
        x0 = 0.75 + i * (w - 1.5) / 2 + 0.12
        x1 = 0.75 + (i + 1) * (w - 1.5) / 2 - 0.12
        arch_ring(mb, TR, x0, x1, h * 0.55, 0.8, 0.1, -0.1, 0.0, n=8)
        mb.box(TR, (x0 + 0.05, -0.05, h * 0.5), (0.1, 0.1, h * 0.1))
        mb.box(TR, (x1 - 0.05, -0.05, h * 0.5), (0.1, 0.1, h * 0.1))


def window_rect(mb, w=4.0, h=6.0, t=0.8):
    ox0, ox1, oz0, oz1 = w / 2 - 0.7, w / 2 + 0.7, 1.6, 4.2
    if h < 5.5:  # domestic storey: 0.9 m sill, 1.2 m wide, header 1.2 m below the next floor
        ox0, ox1, oz0, oz1 = w / 2 - 0.6, w / 2 + 0.6, 0.9, h - 1.25
    wall_opening(mb, w, h, t, ox0, ox1, oz0, oz1, "rect")
    for (cx, cz, sx, sz) in ((ox0 - 0.1, (oz0 + oz1) / 2, 0.2, oz1 - oz0 + 0.4), (ox1 + 0.1, (oz0 + oz1) / 2, 0.2, oz1 - oz0 + 0.4),
                             ((ox0 + ox1) / 2, oz1 + 0.12, ox1 - ox0 + 0.6, 0.24)):
        mb.box(TR, (cx, -0.08, cz), (sx, 0.16, sz))
    mb.box(TR, ((ox0 + ox1) / 2, -0.15, oz0 - 0.08), (ox1 - ox0 + 0.5, 0.3, 0.16))  # sill
    for x in (ox0 + 0.1, ox1 - 0.1):  # HQ: sill corbels + triangular pediment
        mb.box(TR, (x, -0.12, oz0 - 0.32), (0.22, 0.24, 0.32))
    mb.slab_xz([(ox0 - 0.35, oz1 + 0.24), (ox1 + 0.35, oz1 + 0.24), ((ox0 + ox1) / 2, oz1 + min(0.95, h - oz1 - 0.55))], -0.28, -0.02, mat=TR)
    xz_face(mb, GL, [(ox0, oz0), (ox1, oz0), (ox1, oz1), (ox0, oz1)], t * 0.55)
    mb.box(TR, ((ox0 + ox1) / 2, t * 0.5, (oz0 + oz1) / 2), (0.08, 0.1, oz1 - oz0))
    mb.box(TR, ((ox0 + ox1) / 2, t * 0.5, oz0 + (oz1 - oz0) * 0.62), (ox1 - ox0, 0.1, 0.08))
    plinth(mb, 0, w)
    cornice(mb, 0, w, h - 0.42)


def window_gothic(mb, w=4.0, h=7.0, t=0.8):
    ox0, ox1, oz0, zs, k = w / 2 - 0.85, w / 2 + 0.85, 1.7, 4.3, 0.85
    if h < 5.5:  # domestic storey: narrower lancet that fits under the floor band
        ox0, ox1, oz0, k = w / 2 - 0.6, w / 2 + 0.6, 0.9, 0.85
        zs = h - 0.75 - arch_apex(ox0, ox1, 0.0, k)
    wall_opening(mb, w, h, t, ox0, ox1, oz0, zs, "pointed", k)
    arch_ring(mb, TR, ox0, ox1, zs, k, 0.18, -0.12, 0.05)
    # HQ: drip-mould hood over the arch with carved label stops, and a deep splayed reveal
    arch_ring(mb, TR, ox0 - 0.28, ox1 + 0.28, zs, (k * (ox1 - ox0) + 0.28) / (ox1 - ox0 + 0.56), 0.12, -0.3, -0.12, n=12)
    for x in (ox0 - 0.34, ox1 + 0.34):
        mb.box(TR, (x, -0.24, zs - 0.1), (0.26, 0.24, 0.32))
        finial(mb, x, -0.26, zs - 0.75, 0.22)
    for x in (ox0 + 0.06, ox1 - 0.06):
        mb.box(ST, (x, t * 0.28, (oz0 + zs) / 2), (0.12, t * 0.5, zs - oz0))
    for x in (ox0 - 0.09, ox1 + 0.09):
        mb.box(TR, (x, -0.04, (oz0 + zs) / 2), (0.18, 0.18, zs - oz0))
    mb.box(TR, ((ox0 + ox1) / 2, -0.15, oz0 - 0.08), (ox1 - ox0 + 0.5, 0.3, 0.16))
    xz_face(mb, GL, [(ox0, oz0), (ox1, oz0)] + pointed_arch(ox0, ox1, zs, k)[::-1][1:-1] + [(ox0, zs)], t * 0.55)
    # tracery: central mullion, two lancets and an oculus
    xm = (ox0 + ox1) / 2
    mb.box(TR, (xm, t * 0.5, (oz0 + zs) / 2), (0.1, 0.12, zs - oz0))
    arch_ring(mb, TR, ox0 + 0.02, xm - 0.05, zs - 0.2, 0.8, 0.07, t * 0.45, t * 0.56, n=6)
    arch_ring(mb, TR, xm + 0.05, ox1 - 0.02, zs - 0.2, 0.8, 0.07, t * 0.45, t * 0.56, n=6)
    ap = arch_apex(ox0, ox1, zs, k)
    ring_xz(mb, TR, xm, (zs + ap) / 2 + 0.25, 0.32, 0.07, t * 0.45, t * 0.56)
    plinth(mb, 0, w)
    cornice(mb, 0, w, h - 0.42)


def ring_xz(mb, mat, cx, cz, r, th, y0, y1, n=16):
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        p = [(cx + rr * math.cos(a), cz + rr * math.sin(a)) for rr, a in ((r, a0), (r + th, a0), (r + th, a1), (r, a1))]
        mb.face([(x, y0, z) for x, z in p], mat)
        mb.face([(x, y1, z) for x, z in reversed(p)], mat)
        mb.face([(p[0][0], y0, p[0][1]), (p[3][0], y0, p[3][1]), (p[3][0], y1, p[3][1]), (p[0][0], y1, p[0][1])], mat)
        mb.face([(p[1][0], y0, p[1][1]), (p[1][0], y1, p[1][1]), (p[2][0], y1, p[2][1]), (p[2][0], y0, p[2][1])], mat)


def window_rose(mb, w=6.0, h=6.0, t=0.9):
    cx, cz, r = w / 2, h / 2, w * 0.33
    n = 24
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n

        def sq(a):
            dx, dz = math.cos(a), math.sin(a)
            s = min((w / 2) / max(abs(dx), 1e-6), (h / 2) / max(abs(dz), 1e-6))
            return (cx + dx * s, cz + dz * s)
        c0 = (cx + r * math.cos(a0), cz + r * math.sin(a0))
        c1 = (cx + r * math.cos(a1), cz + r * math.sin(a1))
        s0, s1 = sq(a0), sq(a1)
        mb.slab_xz([c0, s0, s1, c1], 0.0, t)
        if abs(math.cos((a0 + a1) / 2)) > 0.98 or abs(math.sin((a0 + a1) / 2)) > 0.98:
            pass
    # square corners missed by the radial fan are covered by the quad fan above (s0,s1 lie on the square)
    mb.add_ucx([(x, y, z) for x in (0, w) for y in (0, t) for z in (0, h)])
    ring_xz(mb, TR, cx, cz, r, 0.22, -0.15, 0.1, n=24)
    ring_xz(mb, TR, cx, cz, r * 0.35, 0.1, t * 0.4, t * 0.55, n=16)
    for i in range(12):
        a = 2 * math.pi * i / 12
        mb.push(T(cx, t * 0.48, cz) @ Matrix.Rotation(-a, 4, "Y"))
        mb.box(TR, (r * 0.68, 0, 0), (r * 0.62, 0.1, 0.07))
        mb.pop()
    xz_face(mb, GL, [(cx + r * math.cos(2 * math.pi * i / 24), cz + r * math.sin(2 * math.pi * i / 24)) for i in range(24)], t * 0.6)


def portal(mb, w=8.0, h=11.0, t=2.4):
    """Recessed gothic portal with three archivolts and a closed double door."""
    ow = 3.2
    ox0, ox1, zs, k = w / 2 - ow / 2, w / 2 + ow / 2, 4.2, 0.8
    steps = 3
    for s in range(steps):
        e = (steps - s) * 0.45
        y0, y1 = s * t / steps, (s + 1) * t / steps
        wall_opening(mb, w, h, y1 - y0, ox0 - e + 0.45, ox1 + e - 0.45, 0.0, zs, "pointed", k) if s == 0 else None
        mb.push(T(0, y0, 0))
        if s > 0:
            a0, a1 = ox0 - e + 0.45, ox1 + e - 0.45
            mb.box(ST, ((0 + a0) / 2, (y1 - y0) / 2, h / 2), (a0, y1 - y0, h))
            mb.box(ST, ((a1 + w) / 2, (y1 - y0) / 2, h / 2), (w - a1, y1 - y0, h))
            mb.slab_xz(pointed_arch(a0, a1, zs, k) + [(a1, h), (a0, h)], 0.0, y1 - y0)
        a0, a1 = ox0 - e + 0.45, ox1 + e - 0.45
        arch_ring(mb, TR, a0, a1, zs, k, 0.22, -0.05, 0.25)
        for x in (a0 - 0.11, a1 + 0.11):
            mb.cyl(TR, (x, 0.1, 0.0), 0.16, zs, sides=10)
        mb.pop()
    # door
    door = [(ox0, 0.0), (ox1, 0.0)] + pointed_arch(ox0, ox1, zs, k)[::-1][1:-1] + [(ox0, zs)]
    mb.slab_xz(door, t - 0.15, t, collide=True)
    for x in (w / 2 - 0.05,):
        mb.box(DR, (x, t - 0.2, zs / 2 + 0.6), (0.1, 0.1, zs + 1.2))
    xz_face(mb, DR, door, t - 0.16)
    # gable (wimperg) with finial
    ap = arch_apex(ox0 - 1.35, ox1 + 1.35, zs, k)
    mb.slab_xz([(ox0 - 1.6, ap - 0.6), (ox1 + 1.6, ap - 0.6), (w / 2, ap + 2.6)], -0.35, 0.0)
    finial(mb, w / 2, -0.17, ap + 2.5, 0.8)
    for x in (ox0 - 1.9, ox1 + 1.9):
        pinnacle(mb, x, -0.25, ap - 1.0, 0.5)
    cornice(mb, 0, w, h - 0.42)
    plinth(mb, 0, w)


def door_house(mb, w=4.0, h=4.2, t=0.8):
    """Street door: 1.5 m x 2.6 m round-headed opening, panelled door, stone surround and a small hood."""
    ox0, ox1, zs = w / 2 - 0.75, w / 2 + 0.75, 2.6 - 0.75
    wall_opening(mb, w, h, t, ox0, ox1, 0.0, zs, "pointed", 0.5)
    arch_ring(mb, TR, ox0, ox1, zs, 0.5, 0.22, -0.18, 0.05)
    for x in (ox0 - 0.11, ox1 + 0.11):
        mb.box(TR, (x, -0.08, zs / 2), (0.22, 0.26, zs))
    door = [(ox0, 0.0), (ox1, 0.0)] + pointed_arch(ox0, ox1, zs, 0.5)[::-1][1:-1] + [(ox0, zs)]
    mb.slab_xz(door, t * 0.6, t * 0.6 + 0.12, mat=DR)
    xz_face(mb, DR, door, t * 0.6 - 0.01)
    mb.box(TR, (w / 2, -0.35, zs + 0.95), (2.2, 0.7, 0.14))           # hood
    for x in (w / 2 - 0.9, w / 2 + 0.9):
        mb.box(TR, (x, -0.3, zs + 0.7), (0.16, 0.5, 0.4))
    mb.box(TR, (w / 2, -0.5, 0.08), (2.0, 1.0, 0.16))                   # door step
    plinth(mb, 0, w)
    cornice(mb, 0, w, h - 0.42)


def column(mb, h=6.0, r=0.38, x=0.0, y=0.0, z=0.0):
    mb.box(TR, (x, y, z + 0.2), (r * 2.8, r * 2.8, 0.4))
    mb.lathe(TR, (x, y, z + 0.4), [(r * 1.3, 0), (r * 1.1, 0.12), (r * 1.2, 0.22), (r, 0.3)], sides=12)
    mb.cyl(TR, (x, y, z + 0.7), r, h - 1.5, sides=12)
    capital(mb, x, y, z + h - 0.8, r)
    mb.add_ucx([(x + dx, y + dy, z + dz) for dx in (-r, r) for dy in (-r, r) for dz in (0, h)])


def capital(mb, x=0.0, y=0.0, z=0.0, r=0.38):
    mb.lathe(TR, (x, y, z), [(r, 0), (r * 1.05, 0.1), (r * 1.25, 0.4), (r * 1.6, 0.6), (0.0, 0.6)], sides=12)
    mb.box(TR, (x, y, z + 0.7), (r * 3.6, r * 3.6, 0.2))


def stairs_straight(mb, w=4.0, steps=20, rise=0.18, run=0.32, rails=True):
    """Ascends along +X, width along +Y (from 0 to w)."""
    L = steps * run
    H = steps * rise
    for i in range(steps):
        mb.box(ST, ((i + 0.5) * run, w / 2, (i + 1) * rise / 2), (run, w, (i + 1) * rise))
        mb.box(TR, ((i + 0.5) * run + run * 0.45, w / 2, (i + 1) * rise - 0.02), (run * 0.15, w, 0.04))
    # ramp collision (wedge)
    mb.add_ucx([(0, 0, 0), (L, 0, 0), (L, 0, H), (0, w, 0), (L, w, 0), (L, w, H)])
    if rails:
        ang = math.degrees(math.atan2(H, L))
        for y in (-0.32, w):
            mb.push(T(0, y, 0.15) @ Matrix.Rotation(math.radians(-ang), 4, "Y"))
            balustrade(mb, math.hypot(L, H), 1.0, 0.32, collide=False)
            mb.pop()
            mb.add_ucx([(0, y, 0), (L, y, H), (L, y + 0.32, H), (0, y + 0.32, 0), (0, y, 1.2), (L, y, H + 1.2), (L, y + 0.32, H + 1.2), (0, y + 0.32, 1.2)])


def stairs_curved(mb, r_in=4.0, r_out=7.5, steps=16, rise=0.18, sweep=90.0):
    da = math.radians(sweep) / steps
    for i in range(steps):
        a0, a1 = i * da, (i + 1) * da
        z = (i + 1) * rise
        poly = [(r_in * math.cos(a0), r_in * math.sin(a0)), (r_out * math.cos(a0), r_out * math.sin(a0)),
                (r_out * math.cos(a1), r_out * math.sin(a1)), (r_in * math.cos(a1), r_in * math.sin(a1))]
        mb.prism(ST, poly, 0.0, z)
    seg = 4
    for s in range(seg):
        a0, a1 = math.radians(sweep) * s / seg, math.radians(sweep) * (s + 1) / seg
        z0, z1 = steps * rise * s / seg, steps * rise * (s + 1) / seg
        pts = []
        for a, z in ((a0, z0), (a1, z1)):
            for r in (r_in, r_out):
                pts += [(r * math.cos(a), r * math.sin(a), 0.0), (r * math.cos(a), r * math.sin(a), z)]
        mb.add_ucx(pts)
    # outer parapet wall following the curve
    for i in range(steps):
        a0, a1 = i * da, (i + 1) * da
        z = (i + 1) * rise
        poly = [(r_out * math.cos(a0), r_out * math.sin(a0)), ((r_out + 0.4) * math.cos(a0), (r_out + 0.4) * math.sin(a0)),
                ((r_out + 0.4) * math.cos(a1), (r_out + 0.4) * math.sin(a1)), (r_out * math.cos(a1), r_out * math.sin(a1))]
        mb.prism(TR, poly, 0.0, z + 1.05)


def balcony(mb, w=5.0, d=2.4):
    mb.box(ST, (w / 2, -d / 2, -0.2), (w, d, 0.4), collide=True)
    for x in (0.6, w / 2, w - 0.6):
        for k, (dd, hh) in enumerate(((d * 0.9, 0.35), (d * 0.6, 0.4), (d * 0.3, 0.45))):
            mb.box(TR, (x, -dd / 2, -0.4 - k * 0.4 - hh / 2 + 0.2), (0.45, dd, hh))
    place(mb, balustrade, 0, -d, 0.0, L=w)
    place(mb, balustrade, 0, -d, 0.0, rz=90, L=d)
    place(mb, balustrade, w + 0.32, -d, 0.0, rz=90, L=d)


def bridge_span(mb, span=15.0, width=8.0, deck=12.0, pier=3.5, depth=-22.0, arch="round", parapet=True):
    """One arch + its left pier. Spans along +X from x=0 (pier) .. pier+span. Deck top at z=deck."""
    t = 1.0
    x0, x1 = pier, pier + span
    zs = deck - 1.6 - span * 0.5
    k = 0.5 if arch == "round" else 0.62
    # pier with cutwaters
    mb.box(ST, (pier / 2, width / 2, (depth + deck) / 2), (pier, width, deck - depth), collide=True)
    for y, sgn in ((0.0, -1), (width, 1)):
        mb.prism(ST, [(0, y), (pier, y), (pier / 2, y + sgn * pier * 0.7)][:: (1 if sgn > 0 else -1)], depth, zs + 1.0)
        mb.prism(TR, [(0.2, y), (pier - 0.2, y), (pier / 2, y + sgn * pier * 0.6)][:: (1 if sgn > 0 else -1)], zs + 1.0, zs + 1.6)
    # spandrel walls (two faces) and the barrel vault soffit between them
    outline = pointed_arch(x0, x1, zs, k, 16) + [(x1, deck - 0.4), (x0, deck - 0.4)]
    mb.slab_xz(outline, 0.0, t)
    mb.slab_xz(outline, width - t, width)
    arc = pointed_arch(x0, x1, zs, k, 16)
    for a in range(len(arc) - 1):
        p, q = arc[a], arc[a + 1]
        mb.face([(p[0], t, p[1]), (q[0], t, q[1]), (q[0], width - t, q[1]), (p[0], width - t, p[1])], ST)
    arch_ring(mb, TR, x0, x1, zs, k, 0.6, -0.2, 0.3, n=16)
    arch_ring(mb, TR, x0, x1, zs, k, 0.6, width - 0.3, width + 0.2, n=16)
    # fill above vault + deck
    mb.box(ST, ((x0 + x1) / 2, width / 2, deck - 0.6), (span, width - 2 * t, 0.4))
    mb.box(ST, ((0 + x1) / 2, width / 2, deck - 0.2), (x1, width + 0.4, 0.4), collide=True)
    mb.box(TR, ((0 + x1) / 2, -0.15, deck - 0.55), (x1, 0.3, 0.3))
    mb.box(TR, ((0 + x1) / 2, width + 0.15, deck - 0.55), (x1, 0.3, 0.3))
    if parapet:
        place(mb, balustrade, 0.0, 0.0, deck, L=x1)
        place(mb, balustrade, 0.0, width - 0.32, deck, L=x1)
        for y in (0.16, width - 0.16):
            mb.box(TR, (pier / 2, y, deck + 0.7), (0.7, 0.7, 1.4))
            mb.cyl(TR, (pier / 2, y, deck + 1.4), 0.08, 2.6, sides=6)
            mb.box(GL, (pier / 2, y, deck + 4.2), (0.45, 0.45, 0.6))   # lamp
            mb.cyl(TR, (pier / 2, y, deck + 4.5), 0.35, 0.5, sides=4, r_top=0.0, smooth=False)


def bridge_end_pier(mb, width=8.0, deck=12.0, pier=3.5, depth=-22.0):
    mb.box(ST, (pier / 2, width / 2, (depth + deck) / 2), (pier, width, deck - depth), collide=True)
    place(mb, balustrade, 0.0, 0.0, deck, L=pier)
    place(mb, balustrade, 0.0, width - 0.32, deck, L=pier)


def arcade(mb, bays=4, bay=4.0, h=6.0, depth=4.0, k=0.5):
    """Open cloister: columns in front, back wall, arches, roof slab ("회랑")."""
    L = bays * bay
    mb.box(ST, (L / 2, depth / 2, -0.25), (L + 0.6, depth + 0.6, 0.5), collide=True)
    mb.box(ST, (L / 2, depth + 0.4, h / 2 + 0.6), (L, 0.8, h + 1.2), collide=True)
    zs = h - 1.6 - bay * 0.5 * (1 if k == 0.5 else 1.2)
    for i in range(bays + 1):
        column(mb, zs, 0.3, i * bay, 0.0)
    for i in range(bays):
        x0, x1 = i * bay + 0.35, (i + 1) * bay - 0.35
        mb.slab_xz(pointed_arch(x0, x1, zs, k, 10) + [(x1, h), (x0, h)], -0.3, 0.3)
        arch_ring(mb, TR, x0, x1, zs, k, 0.16, -0.4, -0.3, n=10)
    mb.box(ST, (L / 2, depth / 2, h + 0.2), (L + 0.8, depth + 1.4, 0.4), collide=True)
    cornice(mb, -0.4, L + 0.4, h + 0.4, y=-0.3)
    place(mb, balustrade, 0.0, -0.4, h + 0.4, L=L)


def gallery(mb, L=12.0, w=3.0):
    """Exterior corridor on corbels with parapet and lean-to roof on slim columns."""
    mb.box(ST, (L / 2, -w / 2, -0.2), (L, w, 0.4), collide=True)
    n = int(L / 2.0)
    for i in range(n + 1):
        x = i * L / n
        mb.box(TR, (x, -w * 0.4, -0.75), (0.4, w * 0.8, 0.7))
        mb.cyl(TR, (x, -w + 0.3, 0.0), 0.15, 3.2, sides=8)
    place(mb, balustrade, 0.0, -w, 0.0, L=L)
    mb.push(T(0, 0, 3.4) @ Matrix.Rotation(math.radians(-12), 4, "X"))
    mb.box(RF, (L / 2, -w / 2, 0.0), (L + 0.6, w + 0.8, 0.22))
    mb.pop()


def spire(mb, r=2.5, h=14.0, sides=8):
    mb.cyl(TR, (0, 0, 0), r * 1.08, 0.6, sides=sides, smooth=False)
    mb.cyl(RF, (0, 0, 0.6), r, h, sides=sides, r_top=0.0, smooth=False)
    for i in range(sides):  # lucarnes
        a = 2 * math.pi * (i + 0.5) / sides
        mb.push(T(r * 0.78 * math.cos(a), r * 0.78 * math.sin(a), 1.6, math.degrees(a) + 90))
        mb.slab_xz([(-0.45, 0), (0.45, 0), (0.45, 1.0), (0, 1.9), (-0.45, 1.0)], -0.3, 0.3)
        xz_face(mb, GL, [(-0.25, 0.2), (0.25, 0.2), (0.25, 0.9), (0, 1.3), (-0.25, 0.9)], -0.31)
        mb.pop()
    for i in range(4):
        a = 2 * math.pi * i / 4 + math.pi / 4
        pinnacle(mb, r * 1.15 * math.cos(a), r * 1.15 * math.sin(a), 0.6, 0.55)
    finial(mb, 0, 0, h + 0.4, 1.0)


def roof_gable(mb, w=8.0, d=10.0, ph=5.0, over=0.5):
    """Gable roof spanning X (width) with ridge along Y (depth), eaves at z=0."""
    tri = [(-over, -0.3), (w + over, -0.3), (w / 2, ph)]
    mb.slab_xz(tri, -over, d + over)
    mb.slab_xz([(-over - 0.15, -0.45), (w + over + 0.15, -0.45), (w + over + 0.15, -0.3), (-over - 0.15, -0.3)], -over, d + over, )
    for y in range(int(d / 1.2) + 1):
        finial(mb, w / 2, -over + y * (d + 2 * over) / max(1, int(d / 1.2)), ph - 0.1, 0.35)
    # re-skin slopes with roof material by overlaying thin slabs
    ang = math.atan2(ph + 0.3, w / 2 + over)
    L = math.hypot(w / 2 + over, ph + 0.3)
    for side in (0, 1):
        mirror = Matrix.Scale(-1, 4, Vector((1, 0, 0))) if side == 0 else Matrix.Identity(4)
        mb.push(T(w / 2, 0, ph) @ mirror @ Matrix.Rotation(ang, 4, "Y"))
        mb.box(RF, (L / 2, d / 2, 0.06), (L, d + 2 * over + 0.1, 0.12))
        mb.pop()


def roof_cone(mb, r=3.0, h=7.0, sides=16):
    mb.cyl(TR, (0, 0, -0.3), r * 1.12, 0.3, sides=sides)
    mb.cyl(RF, (0, 0, 0.0), r * 1.1, h, sides=sides, r_top=0.0)
    finial(mb, 0, 0, h - 0.2, 0.6)


def roof_dome(mb, r=4.0):
    prof = [(r * math.cos(a), r * math.sin(a)) for a in [i * (math.pi / 2) / 10 for i in range(11)]]
    mb.lathe(RF, (0, 0, 0), [(max(p[0], 0.0), p[1]) for p in prof], sides=20)
    mb.cyl(TR, (0, 0, r - 0.2), r * 0.22, r * 0.45, sides=8)
    for i in range(8):
        a = 2 * math.pi * i / 8
        mb.box(GL, (r * 0.2 * math.cos(a), r * 0.2 * math.sin(a), r + 0.05), (0.12, 0.12, r * 0.25))
    mb.cyl(RF, (0, 0, r + r * 0.25), r * 0.28, r * 0.4, sides=8, r_top=0.0, smooth=False)
    finial(mb, 0, 0, r + r * 0.6, 0.4)


# --------------------------------------------------------------------------- HQ detail helpers
def string_course(mb, x0, y0, x1, y1, z, d=0.28):
    """Moulded band running round a rectangular footprint (front = -Y)."""
    for (cx, cy, sx, sy) in (((x0 + x1) / 2, y0 - d / 2, x1 - x0 + 2 * d, d), ((x0 + x1) / 2, y1 + d / 2, x1 - x0 + 2 * d, d),
                             (x0 - d / 2, (y0 + y1) / 2, d, y1 - y0), (x1 + d / 2, (y0 + y1) / 2, d, y1 - y0)):
        mb.box(TR, (cx, cy, z), (sx, sy, 0.22))
        if sx > sy:
            mb.box(TR, (cx, cy + (0.05 if cy > (y0 + y1) / 2 else -0.05) * 0, z - 0.16), (sx * 0.98, sy * 0.6, 0.12))
        else:
            mb.box(TR, (cx, cy, z - 0.16), (sx * 0.6, sy * 0.98, 0.12))


def quoins(mb, x, y, z0, z1, sx=1.0, sy=1.0):
    """Alternating long/short dressed corner stones; (sx, sy) point out of the corner."""
    n = max(2, int((z1 - z0) / 0.7))
    for i in range(n):
        z = z0 + (i + 0.5) * (z1 - z0) / n
        lx, ly = (0.9, 0.5) if i % 2 == 0 else (0.5, 0.9)
        mb.box(TR, (x - sx * (lx / 2 - 0.1), y - sy * (ly / 2 - 0.1), z), (lx, ly, (z1 - z0) / n * 0.86))


def corner_turret(mb, x, y, z, h=6.0, r=1.4):
    """Corbelled bartizan with lancet slits, conical roof and finial."""
    mb.lathe(TR, (x, y, z - 2.2), [(0.15, 0.0), (r * 0.5, 0.8), (r * 0.85, 1.6), (r * 1.05, 2.2)], sides=16)
    mb.cyl(ST, (x, y, z), r, h, sides=16)
    for zz in (z + h * 0.25, z + h * 0.62):
        mb.cyl(TR, (x, y, zz), r + 0.08, 0.18, sides=16)
    for k in range(4):
        a = math.pi * 0.5 * k + math.pi / 4
        mb.push(T(x + r * math.cos(a), y + r * math.sin(a), z, math.degrees(a) + 90))
        xz_face(mb, GL, [(-0.22, 1.8), (0.22, 1.8), (0.22, 3.4), (0.0, 3.8), (-0.22, 3.4)], -0.03)
        mb.pop()
    mb.cyl(TR, (x, y, z + h), r + 0.2, 0.3, sides=16)
    mb.cyl(RF, (x, y, z + h + 0.3), r + 0.15, r * 3.2, sides=16, r_top=0.0)
    finial(mb, x, y, z + h + 0.2 + r * 3.1, 0.5)


def dormer(mb, w=1.6, h=1.8):
    """Gabled dormer window, front facing -Y, sitting at z=0."""
    mb.box(ST, (0, 0.6, h / 2), (w, 1.4, h))
    mb.slab_xz([(-w / 2 - 0.2, h), (w / 2 + 0.2, h), (0, h + w * 0.7)], -0.15, 1.3, mat=RF)
    xz_face(mb, GL, [(-w * 0.3, 0.3), (w * 0.3, 0.3), (w * 0.3, h * 0.75), (0, h * 0.9), (-w * 0.3, h * 0.75)], -0.11)
    mb.box(TR, (0, -0.1, 0.22), (w * 0.8, 0.2, 0.12))
    finial(mb, 0, -0.1, h + w * 0.68, 0.25)


def chimney(mb, x, y, z, h=3.5):
    mb.box(ST, (x, y, z + h / 2), (1.1, 1.1, h))
    mb.box(TR, (x, y, z + h + 0.12), (1.4, 1.4, 0.24))
    for dx in (-0.25, 0.25):
        mb.cyl(TR, (x + dx, y, z + h + 0.24), 0.17, 0.7, sides=8)


# --------------------------------------------------------------------------- composites
def facade_row(mb, mods, w=4.0, h=6.0, z=0.0):
    for i, m in enumerate(mods):
        place(mb, m, i * w, 0.0, z, w=w, h=h)


def box_building(mb, nx, ny, levels, rng, h=6.0, w=4.0, front=None):
    """Rectangular block of wall modules. Footprint nx*w by ny*w, front faces -Y."""
    choices = [window_gothic, window_gothic, window_rect, wall_deco]
    prev = mb.ucx_enabled
    mb.ucx_enabled = False  # closed exterior block -> one simple collision box (no interiors)
    mb.add_ucx([(x, y, z) for x in (0, nx * w) for y in (0, ny * w) for z in (0, levels * h)], force=True)
    _box_building_body(mb, nx, ny, levels, rng, h, w, front, choices)
    mb.ucx_enabled = prev


def _box_building_body(mb, nx, ny, levels, rng, h, w, front, choices):
    for lv in range(levels):
        z = lv * h
        for side in range(4):
            n = nx if side % 2 == 0 else ny
            for i in range(n):
                fn = rng.choice(choices)
                if front is not None and side == 0 and lv == 0 and i == n // 2:
                    continue
                if side == 0:
                    place(mb, fn, i * w, 0, z, w=w, h=h)
                elif side == 1:
                    place(mb, fn, nx * w, i * w, z, rz=90, w=w, h=h)
                elif side == 2:
                    place(mb, fn, nx * w - i * w, ny * w, z, rz=180, w=w, h=h)
                else:
                    place(mb, fn, 0, ny * w - i * w, z, rz=270, w=w, h=h)
    # floor slabs per level (collision + closes interior from view)
    for lv in range(levels + 1):
        mb.box(ST, (nx * w / 2, ny * w / 2, lv * h - 0.2), (nx * w, ny * w, 0.4), collide=(lv == levels))
    # corner buttresses
    for (x, y, r) in ((0, 0, 0), (nx * w, 0, 0), (nx * w, ny * w, 180), (0, ny * w, 180)):
        place(mb, buttress, x, y, 0, rz=r, h=levels * h * 0.75)
    for lv in range(1, levels):  # HQ: moulded band at every floor
        string_course(mb, 0, 0, nx * w, ny * w, lv * h - 0.3)


def bldg_hall(mb, rng):
    nx, ny, lv = 6, 3, 2
    box_building(mb, nx, ny, lv, rng, h=7.0, front=True)
    place(mb, portal, nx * 4 / 2 - 4, -2.4, 0, w=8.0, h=7.0, t=2.4)
    # gable roof with ridge along X: rotate a gable spanning Y
    place(mb, roof_gable, nx * 4, 0, lv * 7.0, rz=90, w=ny * 4, d=nx * 4, ph=6.5)
    place(mb, window_rose, -0.15, ny * 2 + 2.5, lv * 7.0 - 5.6, rz=270, w=5.0, h=5.0)
    for x in (0, nx * 4):
        for y in (0, ny * 4):
            pinnacle(mb, x, y, lv * 7.0 + 0.2, 0.9)
    place(mb, spire, nx * 4 / 2, ny * 4 / 2, lv * 7.0 + 6.0, r=1.4, h=9.0)
    for i in range(1, nx):  # HQ: buttress + pinnacle at every bay of both long sides
        place(mb, buttress, i * 4, 0, 0, h=lv * 7.0 * 0.8)
        place(mb, buttress, i * 4, ny * 4, 0, rz=180, h=lv * 7.0 * 0.8)


def bldg_tower_square(mb, rng, s=2, levels=7, h=TFH):
    box_building(mb, s, s, levels, rng, h=h)
    top = levels * h
    for side in range(4):
        rz = side * 90
        ox, oy = [(0, 0), (s * 4, 0), (s * 4, s * 4), (0, s * 4)][side]
        place(mb, crenels, ox, oy, top, rz=rz, L=s * 4, t=0.6)
    for (x, y) in ((0, 0), (s * 4, 0), (s * 4, s * 4), (0, s * 4)):
        corner_turret(mb, x, y, top - 3.0, 5.0, 1.3)
    place(mb, spire, s * 2, s * 2, top, r=s * 1.4, h=s * 7.0)


def bldg_tower_round(mb, rng, r=5.5, h=36.0, sides=20):
    lv = int(h / TFH)
    for i in range(lv):
        z = i * TFH
        rr = r * (1.0 - 0.02 * i)
        mb.cyl(ST, (0, 0, z), rr, TFH, sides=sides, collide=(i == 0), smooth=False)
        mb.cyl(TR, (0, 0, z + TFH - 0.35), rr + 0.25, 0.35, sides=sides, smooth=False)
        for k in range(6):
            a = 2 * math.pi * (k + 0.5 * (i % 2)) / 6
            mb.push(T(rr * math.cos(a), rr * math.sin(a), z, math.degrees(a) + 90))
            arch_ring(mb, TR, -0.55, 0.55, 2.4, 0.85, 0.14, -0.22, 0.05, n=8)
            xz_face(mb, GL, [(-0.55, 1.0), (0.55, 1.0)] + pointed_arch(-0.55, 0.55, 2.4, 0.85, 8)[::-1][1:-1] + [(-0.55, 2.4)], -0.06)
            mb.pop()
    mb.add_ucx([(r * math.cos(a), r * math.sin(a), z) for a in [2 * math.pi * k / 12 for k in range(12)] for z in (0, h)])
    # belfry: open colonnade ring
    zt = lv * TFH
    rt = r * (1.0 - 0.02 * lv)
    mb.cyl(ST, (0, 0, zt), rt + 1.6, 0.5, sides=sides * 2, smooth=False)        # HQ: walk-round gallery
    mb.lathe(TR, (0, 0, zt - 1.6), [(rt, 0.0), (rt + 0.6, 0.7), (rt + 1.4, 1.4), (rt + 1.6, 1.6)], sides=sides * 2)
    for k in range(sides * 3):
        a = 2 * math.pi * k / (sides * 3)
        baluster(mb, (rt + 1.4) * math.cos(a), (rt + 1.4) * math.sin(a), zt + 0.5, 0.8)
    mb.cyl(TR, (0, 0, zt + 1.3), rt + 1.55, 0.15, sides=sides * 2)
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        corner_turret(mb, (rt + 0.9) * math.cos(a), (rt + 0.9) * math.sin(a), zt - 3.0, 4.0, 0.9)
    mb.cyl(ST, (0, 0, zt), rt + 0.6, 0.6, sides=sides, smooth=False)
    for k in range(10):
        a = 2 * math.pi * k / 10
        column(mb, 5.5, 0.32, (rt - 0.2) * math.cos(a), (rt - 0.2) * math.sin(a), zt + 0.6)
    mb.cyl(ST, (0, 0, zt + 0.6), rt * 0.55, 5.5, sides=12)
    xz_face(mb, GL, [(-1.0, zt + 1.2), (1.0, zt + 1.2), (1.0, zt + 5.0), (-1.0, zt + 5.0)], -rt * 0.56)
    mb.cyl(TR, (0, 0, zt + 6.1), rt + 0.7, 0.8, sides=sides, smooth=False)
    place(mb, roof_dome, 0, 0, zt + 6.9, r=rt + 0.3)


def bldg_house(mb, rng):
    nx, ny = rng.choice([(2, 2), (2, 3), (3, 2)])
    lv = rng.choice([2, 3, 3])
    choices = [window_rect, window_rect, window_gothic, wall_plain]
    mb.add_ucx([(x, y, z) for x in (0, nx * 4) for y in (0, ny * 4) for z in (0, lv * FH)], force=True)
    mb.ucx_enabled = False
    for l in range(lv):
        for side in range(4):
            n = nx if side % 2 == 0 else ny
            for i in range(n):
                fn = rng.choice(choices)
                if l == 0 and side == 0 and i == (n - 1) // 2:
                    fn = door_house          # every house gets a street door on the front (-Y) facade
                ox, oy, rz = [(i * 4, 0, 0), (nx * 4, i * 4, 90), (nx * 4 - i * 4, ny * 4, 180), (0, ny * 4 - i * 4, 270)][side]
                place(mb, fn, ox, oy, l * FH, rz=rz, w=4.0, h=FH)
    for l in range(lv + 1):
        mb.box(ST, (nx * 2, ny * 2, l * FH - 0.2), (nx * 4, ny * 4, 0.4), collide=(l == lv))
    W, D, H = nx * 4, ny * 4, lv * FH
    # HQ: floor bands, plinth course, dressed corners
    for l in range(1, lv):
        string_course(mb, 0, 0, W, D, l * FH - 0.3)
    string_course(mb, 0, 0, W, D, 0.6, d=0.3)
    for (x, y, sx, sy) in ((0, 0, -1, 1), (W, 0, 1, 1), (W, D, 1, -1), (0, D, -1, -1)):
        quoins(mb, x, y, 0.0, H, sx, -sy)
    if rng.random() < 0.65:
        ph = rng.uniform(4.0, 5.5)   # ~40-45 degree pitch for an 8-12 m span
        place(mb, roof_gable, 0, 0, H, w=W, d=D, ph=ph)
        # front gable oculus + eave finials
        ring_xz(mb, TR, W / 2, H + ph * 0.42, 0.55, 0.14, -0.6, -0.3, n=16)
        xz_face(mb, GL, [(W / 2 + 0.55 * math.cos(2 * math.pi * i / 16), H + ph * 0.42 + 0.55 * math.sin(2 * math.pi * i / 16)) for i in range(16)], -0.45)
        for x in (-0.3, W + 0.3):
            finial(mb, x, -0.4, H - 0.2, 0.5)
        # dormers on both roof slopes
        for side in (-1, 1):
            nd = max(1, ny - 1)
            for j in range(nd):
                y = (j + 0.5) * D / nd
                mb.push(T(W / 2 + side * W * 0.27, y, H + ph * 0.38, -90 if side > 0 else 90))
                dormer(mb, 1.3, 1.5)
                mb.pop()
        chimney(mb, W * rng.choice([0.3, 0.7]), D * 0.7, H + ph * 0.4, 3.0)
    else:
        mb.cyl(ST, (W / 2, D / 2, H), min(nx, ny) * 1.6, FH, sides=16)
        mb.cyl(TR, (W / 2, D / 2, H + FH * 0.5), min(nx, ny) * 1.6 + 0.12, 0.2, sides=16)
        place(mb, roof_cone, W / 2, D / 2, H + FH, r=min(nx, ny) * 1.6, h=5.5)
        place(mb, crenels, 0, 0, H, L=W, t=0.5)
    # corbelled corner turrets on the front corners
    if rng.random() < 0.7:
        for x in ((0.0, W) if rng.random() < 0.5 else (W,)):
            corner_turret(mb, x, 0.0, H - FH, FH + 0.6, 1.1)
    # balconies on the upper floors of the front
    for l in range(1, lv):
        if rng.random() < 0.6:
            place(mb, balcony, 0.8, 0, l * FH, w=W - 1.6, d=1.3)


def bldg_loggia(mb, rng, bays=7, bay=4.6):
    """West loggia hall (left building of the reference): podium, two stacked arcades,
    roof terrace with balustrade, end turrets, side walls with windows."""
    L = bays * bay
    D = 14.0
    mb.box(ST, (L / 2, D / 2, 1.5), (L + 4, D + 4, 3.0), collide=True)        # podium
    cornice(mb, -2, L + 2, 2.6, y=-2.0)
    place(mb, arcade, 0, 0, 3.0, bays=bays, bay=bay, h=8.0, depth=D * 0.45, k=0.62)
    place(mb, arcade, 0, 0, 11.8, bays=bays, bay=bay, h=6.5, depth=D * 0.45, k=0.5)
    # back mass of the hall behind the arcades + closed side walls
    mb.box(ST, (L / 2, D * 0.75, 10.0), (L, D * 0.5, 20.0), collide=True)
    for x in (-0.4, L + 0.4):
        mb.box(ST, (x, D / 2, 10.8), (0.8, D, 15.6), collide=True)
    prev_ucx = mb.ucx_enabled
    mb.ucx_enabled = False  # the hall walls already have box collision; window modules would add ~80 hulls
    for z in (3.0, 10.4):  # HQ: back and side elevations get two storeys of tracery windows, bands and buttresses
        for x in range(int(L / 4)):
            place(mb, window_gothic, (x + 1) * 4, D + 0.05, z, rz=180, w=4.0, h=7.0)
        for i in range(int(D / 4)):
            place(mb, window_gothic, -0.85, (i + 1) * 4, z, rz=90, w=4.0, h=7.0)
            place(mb, window_gothic, L + 0.85, i * 4, z, rz=270, w=4.0, h=7.0)
    mb.push(T(0, D * 0.5, 0))
    string_course(mb, -0.85, 0, L + 0.85, D * 0.5, 10.1)
    string_course(mb, -0.85, 0, L + 0.85, D * 0.5, 17.6)
    mb.pop()
    for x in range(0, int(L / 4) + 1, 2):
        place(mb, buttress, x * 4, D + 0.05, 3.0, rz=180, h=13.0)
    mb.ucx_enabled = prev_ucx
    mb.box(ST, (L / 2, D / 2, 18.6), (L + 1.2, D + 1.2, 0.5), collide=True)
    place(mb, balustrade, 0, -0.6, 18.85, L=L)
    for x in (-1.0, L + 1.0):
        mb.cyl(ST, (x, 0.5, 3.0), 2.4, 20.0, sides=16)
        mb.cyl(TR, (x, 0.5, 22.8), 2.7, 0.5, sides=16)
        place(mb, roof_cone, x, 0.5, 23.3, r=2.4, h=7.0)
        for k in range(3):
            a = math.radians(-90 + (k - 1) * 40)
            mb.box(GL, (x + 2.38 * math.cos(a), 0.5 + 2.38 * math.sin(a), 8 + k * 4.0), (0.6, 0.06, 1.6))
    place(mb, spire, L / 2, D * 0.75, 19.0, r=2.2, h=10.0)


def bldg_cathedral(mb, rng):
    nx, ny = 10, 4
    box_building(mb, nx, ny, 3, rng, h=7.0, front=True)
    mb.ucx_enabled = False
    place(mb, roof_gable, nx * 4, 0, 21.0, rz=90, w=ny * 4, d=nx * 4, ph=10.0)
    mb.push(T(-8.0, 0, 0))
    bldg_tower_square(mb, rng, s=2, levels=7, h=6.0)   # cathedral west-front towers keep the grand storey
    mb.pop()
    mb.push(T(-8.0, ny * 4 - 8, 0))
    bldg_tower_square(mb, rng, s=2, levels=7, h=6.0)
    mb.pop()
    place(mb, portal, nx * 2 - 4, -2.4, 0, w=8.0, h=7.0, t=2.4)
    mb.cyl(ST, (nx * 4, ny * 2, 0), ny * 2, 18.0, sides=16)   # apse
    place(mb, roof_dome, nx * 4, ny * 2, 18.0, r=ny * 2)
    place(mb, spire, nx * 2, ny * 2, 31.0, r=2.6, h=18.0)


def bridge_grand(mb, rng, spans=4, span=15.0, width=8.0, deck=12.0, pier=3.5):
    for i in range(spans):
        place(mb, bridge_span, i * (span + pier), 0, 0, span=span, width=width, deck=deck, pier=pier)
    place(mb, bridge_end_pier, spans * (span + pier), 0, 0, width=width, deck=deck, pier=pier)
    total = spans * (span + pier) + pier
    # one continuous walkable deck hull (no seams between span modules)
    mb.add_ucx([(x, y, z) for x in (-6.0, total + 6.0) for y in (0.0, width) for z in (deck - 0.4, deck)], force=True)
    for x in (-6.0, total):  # end pavilions
        mb.push(T(x, -1.0, deck))
        mb.box(ST, (3.0, 5.0, -0.2), (6.0, 10.0, 0.4), collide=True)
        for (cx, cy) in ((0.4, 0.4), (5.6, 0.4), (5.6, 9.6), (0.4, 9.6)):
            column(mb, 6.0, 0.35, cx, cy, 0.0)
        mb.box(ST, (3.0, 5.0, 6.3), (6.6, 10.6, 0.6))
        place(mb, roof_dome, 3.0, 5.0, 6.6, r=3.2)
        mb.pop()
        mb.box(ST, (x + 3.0, width / 2, (deck - 22.0) / 2), (6.0, width + 2.0, deck + 22.0), collide=True)


def plaza(mb, rng, w=30.0, d=24.0, h=4.0):
    mb.box(ST, (w / 2, d / 2, h / 2 - 0.1), (w, d, h), collide=True)
    cornice(mb, 0, w, h - 0.45, y=0.0)
    place(mb, balustrade, 0, 0, h, L=w / 2 - 3)
    place(mb, balustrade, w / 2 + 3, 0, h, L=w / 2 - 3)
    place(mb, balustrade, w, 0, h, rz=90, L=d)
    place(mb, balustrade, 0.32, 0, h, rz=90, L=d)
    # front stair flight descending toward -Y
    steps = int(round(h / 0.18))
    mb.push(T(w / 2 + 3.0, -steps * 0.32, 0, rz=90))
    stairs_straight(mb, 6.0, steps, h / steps, 0.32, rails=False)
    mb.pop()
    finial(mb, w / 2 - 3.0, -0.2, h, 0.8)
    finial(mb, w / 2 + 3.0, -0.2, h, 0.8)
    mb.cyl(TR, (w / 2, d / 2, h), 2.0, 0.6, sides=16)   # fountain basin rim
    mb.cyl(GL, (w / 2, d / 2, h + 0.6), 0.5, 2.5, sides=8, r_top=0.15)


def stair_grand(mb, rng, flights=3, w=6.0):
    """Monumental stair: flights of 16 steps with landings, descending toward -X."""
    z = 0.0
    x = 0.0
    for f in range(flights):
        mb.push(T(x, 0, z))
        stairs_straight(mb, w, 16, 0.18, 0.32, rails=True)
        mb.pop()
        x += 16 * 0.32
        z += 16 * 0.18
        mb.box(ST, (x + 2.0, w / 2, z / 2 - 0.0), (4.0, w, z), collide=True)
        place(mb, balustrade, x, -0.32, z, L=4.0)
        place(mb, balustrade, x, w, z, L=4.0)
        x += 4.0
    mb.box(ST, (x / 2, w / 2, -3.0), (x, w + 1.0, 6.0))   # foundation under water


# --------------------------------------------------------------------------- build
def build(name, fn, seed, coll, **kw):
    rng = random.Random(seed)
    random.seed(seed)
    mb = C.MeshBuilder(name, MATS)
    fn(mb, rng, **kw) if kw or fn.__code__.co_varnames[:2] == ("mb", "rng") else fn(mb)
    ob, ucx = mb.finish(coll, uv_scale=0.5, recalc=True)
    C.export_asset(ob, ucx, "Architecture")
    print("BUILT", name, len(ob.data.polygons), "ucx", len(ucx))


def main():
    C.reset_scene()
    coll = C.collection("Architecture")
    only = os.environ.get("CK_ONLY")
    modules = [
        ("SM_Arch_Wall_Plain", wall_plain), ("SM_Arch_Wall_Deco", wall_deco), ("SM_Arch_Window_Rect", window_rect),
        ("SM_Arch_Window_Gothic", window_gothic), ("SM_Arch_Window_Rose", window_rose), ("SM_Arch_Portal", portal),
        ("SM_Arch_Column", column), ("SM_Arch_Capital", capital), ("SM_Arch_Stairs_Straight", stairs_straight),
        ("SM_Arch_Stairs_Curved", stairs_curved), ("SM_Arch_Balustrade", balustrade), ("SM_Arch_Balcony", balcony),
        ("SM_Arch_Bridge_Span", bridge_span), ("SM_Arch_Arcade", arcade), ("SM_Arch_Gallery", gallery),
        ("SM_Arch_Spire", spire), ("SM_Arch_Roof_Gable", roof_gable), ("SM_Arch_Roof_Cone", roof_cone),
        ("SM_Arch_Roof_Dome", roof_dome), ("SM_Arch_Deco_Finial", finial), ("SM_Arch_Deco_Pinnacle", pinnacle),
        ("SM_Arch_Deco_Crenel", crenels), ("SM_Arch_Deco_Buttress", buttress),
    ]
    composites = [
        ("SM_Bldg_Loggia", bldg_loggia), ("SM_Bldg_Hall", bldg_hall), ("SM_Bldg_TowerRound", bldg_tower_round),
        ("SM_Bldg_TowerSquare", bldg_tower_square), ("SM_Bldg_Cathedral", bldg_cathedral),
        ("SM_Bldg_House_01", bldg_house), ("SM_Bldg_House_02", bldg_house), ("SM_Bldg_House_03", bldg_house),
        ("SM_Bldg_House_04", bldg_house), ("SM_Bldg_House_05", bldg_house), ("SM_Bldg_House_06", bldg_house),
        ("SM_Bridge_Grand", bridge_grand), ("SM_Bldg_Plaza", plaza), ("SM_Bldg_StairGrand", stair_grand),
    ]
    for k, (name, fn) in enumerate(modules):
        if only and only not in name:
            continue
        rng = random.Random(10 + k)
        random.seed(10 + k)
        mb = C.MeshBuilder(name, MATS)
        fn(mb)
        ob, ucx = mb.finish(coll, uv_scale=0.5, recalc=True)
        C.export_asset(ob, ucx, "Architecture")
        print("BUILT", name, len(ob.data.polygons), "ucx", len(ucx))
    for k, (name, fn) in enumerate(composites):
        if only and only not in name:
            continue
        random.seed(200 + k)
        rng = random.Random(200 + k)
        mb = C.MeshBuilder(name, MATS)
        fn(mb, rng)
        ob, ucx = mb.finish(coll, uv_scale=0.5, recalc=True)
        C.export_asset(ob, ucx, "Architecture")
        print("BUILT", name, len(ob.data.polygons), "ucx", len(ucx))
    C.save_blend("CK_Architecture" if not only else "CK_Architecture_" + only)   # partial runs must not overwrite the full .blend


if __name__ == "__main__":
    main()
