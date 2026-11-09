"""The cave itself: a noise-displaced superellipsoid shell (walls + ceiling with three
skylight chimneys) and a lake-basin floor heightfield. Both are split into chunks so that
Nanite culling and Lumen mesh distance fields stay effective.

World layout (meters, UE axes after import: X forward, Z up):
  cave X -60..440, Y -175..175, ceiling 125..175, water level Z=0
run: blender --background --factory-startup --python gen_cave.py
"""
import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep + "Blender")
import ck_common as C  # noqa: E402

MAT = "M_CaveRock"
XC, A = 190.0, 250.0          # center / half length along X
B = 178.0                      # half width
BOTTOM = -45.0
E1, E2 = 0.30, 0.42            # superellipsoid exponents (ends, cross-section)
SKYLIGHTS = [  # (x, y, radius, rise)
    (178.0, 12.0, 34.0, 75.0),
    (140.0, 58.0, 17.0, 50.0),
    (222.0, -28.0, 21.0, 55.0),
]


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def top_height(x, y):
    return 150.0 + 18.0 * math.sin((x - 40) / 500 * math.pi) + 10.0 * C.fbm(Vector((x * 0.004, y * 0.004, 7.0)), 3)


END_P = 6.0  # end-cap flatness


def u_samples(nu):
    """Uniform along X in the body, denser on the two end walls."""
    ne = max(6, nu // 14)
    nb = nu - 2 * ne
    body = [-0.96 + 1.92 * i / nb for i in range(nb + 1)]
    end = [0.96 + 0.04 * math.sin(0.5 * math.pi * k / ne) for k in range(1, ne + 1)]
    return [-e for e in reversed(end)] + body + end


def arc_uniform_oms(nw, dense=40000):
    """Angles of the superellipse cross-section spaced uniformly by arc length."""
    cz = (155.0 - BOTTOM) * 0.5
    ws = [-math.pi + 2 * math.pi * k / dense for k in range(dense + 1)]
    pts = [(B * spow(math.cos(w), E2), cz * spow(math.sin(w), E2)) for w in ws]
    cum = [0.0]
    for k in range(1, len(pts)):
        cum.append(cum[-1] + math.dist(pts[k], pts[k - 1]))
    total = cum[-1]
    out, k = [], 0
    for j in range(nw):
        target = total * j / nw
        while cum[k + 1] < target:
            k += 1
        t = (target - cum[k]) / max(cum[k + 1] - cum[k], 1e-9)
        out.append(ws[k] + (ws[k + 1] - ws[k]) * t)
    return out


def base_point(u, om):
    x = XC + A * u
    r = max(0.0, 1.0 - abs(u) ** END_P) ** (1.0 / END_P)
    ce, se = spow(math.cos(om), E2), spow(math.sin(om), E2)
    y = B * r * ce
    top = top_height(x, y)
    zc = (top + BOTTOM) * 0.5
    cz = (top - BOTTOM) * 0.5
    z = zc + cz * r * se
    return Vector((x, y, z))


def shell_point(eta, om):
    p = base_point(eta, om)
    h = 1e-3
    du = base_point(eta + h, om) - base_point(eta - h, om)
    dv = base_point(eta, om + h) - base_point(eta, om - h)
    n = du.cross(dv)
    if n.length < 1e-9:
        n = Vector((XC, 0, 60)) - p
    n.normalize()
    axis = Vector((p.x, 0, 60.0))
    if n.dot(axis - p) < 0:
        n = -n  # point inward
    s = p * 0.01
    d = 16.0 * C.fbm(p * 0.006, 4) + 7.0 * (C.ridged(p * 0.02, 3) - 1.0) + 2.0 * C.fbm(p * 0.09, 3)
    d += 2.0 * math.sin(p.z * 0.35 + 3.0 * C.fbm(s * 3, 2))  # strata on walls
    if n.z < -0.4:  # ceiling: hanging rock masses
        d += 14.0 * max(0.0, C.fbm(p * 0.012 + Vector((5, 5, 5)), 3)) ** 1.5
    q = p + n * d
    if n.z < -0.2:
        for (cx, cy, R, H) in SKYLIGHTS:
            dd = math.hypot(q.x - cx, q.y - cy)
            if dd < R:
                q.z += H * (1 - (dd / R) ** 2) ** 2
    q.z = max(q.z, -30.0)
    return q


def in_hole(p):
    for (cx, cy, R, H) in SKYLIGHTS:
        if math.hypot(p.x - cx, p.y - cy) < R * 0.32 and p.z > 120:
            return True
    return False


def build_shell(coll, nu=300, nw=560, cu=4, cw=8):
    etas = u_samples(nu)
    nu = len(etas) - 1
    oms = arc_uniform_oms(nw)
    grid = [[shell_point(e, o) for o in oms] for e in etas]
    print("shell grid done")
    names = []
    for bu in range(cu):
        for bw in range(cw):
            name = "SM_Cave_Shell_%02d" % (bu * cw + bw)
            mb = C.MeshBuilder(name, [MAT])
            i0, i1 = bu * nu // cu, (bu + 1) * nu // cu
            j0, j1 = bw * nw // cw, (bw + 1) * nw // cw
            for i in range(i0, i1):
                for j in range(j0, j1):
                    jn = (j + 1) % nw
                    a, b, c, d = grid[i][j], grid[i + 1][j], grid[i + 1][jn], grid[i][jn]
                    if all(in_hole(p) for p in (a, b, c, d)):
                        continue
                    quad = [a, d, c, b]
                    nrm = (quad[1] - quad[0]).cross(quad[3] - quad[0])
                    cen = (a + b + c + d) * 0.25
                    if nrm.dot(Vector((cen.x, 0.0, 60.0)) - cen) < 0:
                        quad = list(reversed(quad))
                    g = [min(1.0, max(0.0, p.z / 180.0)) for p in quad]
                    mb.face([tuple(p) for p in quad], MAT, smooth=True, g=g)
            if not mb.bm.faces:
                mb.bm.free()
                continue
            ob, ucx = mb.finish(coll, uv_scale=0.25)
            C.export_asset(ob, ucx, "Cave")
            names.append(name)
            print("BUILT", name, len(ob.data.polygons))
    return names


# ------------------------------------------------------------------ floor
def lake_sdf(x, y):
    """Positive inside the lake (meters)."""
    w = 72.0 + 22.0 * C.fbm(Vector((x * 0.012, 3.3, 0)), 3) + 18.0 * math.sin(x / 90.0)
    side = w - abs(y - 6.0 * math.sin(x / 60.0))
    south = x - 16.0 - 6.0 * C.fbm(Vector((y * 0.03, 1.1, 0)), 2)
    north = 335.0 - x
    return min(side, south, north)


def floor_h(x, y):
    p = Vector((x, y, 0))
    s = lake_sdf(x, y)
    if s > 0:
        depth = C.lerp(0.6, 17.0, C.smoothstep(0.0, 55.0, s))
        if x < 70:  # shallow clear water near the camera (submerged rocks visible)
            depth = min(depth, C.lerp(0.6, 5.0, C.smoothstep(16, 70, x)))
        h = -depth + 1.2 * C.fbm(p * 0.05, 3)
    else:
        h = 0.9 + 3.5 * C.smoothstep(0.0, 35.0, -s) + 1.4 * C.fbm(p * 0.04, 3)
        h += 28.0 * C.smoothstep(120.0, 175.0, abs(y))        # rises into the walls
        h += 16.0 * C.smoothstep(330.0, 430.0, x)              # northern terraces
    h += 0.35 * C.fbm(p * 0.35, 2)
    return h


def build_floor(coll, x0=-70, x1=450, y0=-190, y1=190, step=1.5, cx=4, cy=3):
    nx = int((x1 - x0) / step)
    ny = int((y1 - y0) / step)
    H = [[floor_h(x0 + i * step, y0 + j * step) for j in range(ny + 1)] for i in range(nx + 1)]
    print("floor grid done")
    for bx in range(cx):
        for by in range(cy):
            name = "SM_Cave_Floor_%02d" % (bx * cy + by)
            mb = C.MeshBuilder(name, [MAT])
            for i in range(bx * nx // cx, (bx + 1) * nx // cx):
                for j in range(by * ny // cy, (by + 1) * ny // cy):
                    P = lambda a, b: (x0 + a * step, y0 + b * step, H[a][b])
                    pts = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]
                    g = [min(1.0, max(0.0, (p[2] + 18) / 40.0)) for p in pts]
                    mb.face(pts, MAT, smooth=True, g=g)
            ob, ucx = mb.finish(coll, uv_scale=0.25)
            C.export_asset(ob, ucx, "Cave")
            print("BUILT", name, len(ob.data.polygons))


def main():
    C.reset_scene()
    coll = C.collection("Cave")
    build_floor(coll)
    build_shell(coll)
    C.save_blend("CK_Cave")


if __name__ == "__main__":
    main()
