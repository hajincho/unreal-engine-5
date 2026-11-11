"""Road bodies for the row town: one continuous solid per straight road from Saved/road_mesh.json (ck_streets.py).
Cross-section: dressed-stone kerb band | block paving | kerb band on top, vertical stone retaining faces down to
below the ground (the embankment is part of the road, not a separate box), square end caps, closed bottom.
Long-section: level stretches and straight ramps as given; any stretch steeper than STAIR_FROM becomes a flight of
real steps (treads and risers) inside the same mesh.
Vertices are in world metres (UE x, y -> Blender x, -y), so every road actor is spawned at the origin.
usage: blender --background --factory-startup --python gen_roads.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_common as C  # noqa: E402

PAVE, KERB = "M_Stone", "M_StoneTrim"
KERB_W = 0.6
STAIR_FROM = 0.12          # grade above which a segment is built as steps
RISER = 0.17


def long_section(ts, zs):
    """(t, z) points along the road; steep segments become treads + risers (vertical pairs share one t)."""
    out = [(ts[0], zs[0])]
    for k in range(len(ts) - 1):
        t0, t1, z0, z1 = ts[k], ts[k + 1], zs[k], zs[k + 1]
        dz, dt = z1 - z0, t1 - t0
        if dt > 1e-6 and abs(dz) / dt > STAIR_FROM:
            n = max(1, int(math.ceil(abs(dz) / RISER)))
            tread = dt / n
            rh = dz / n
            for i in range(n):
                if dz > 0:     # going up: riser first, then the tread
                    out.append((t0 + i * tread, z0 + (i + 1) * rh))
                    out.append((t0 + (i + 1) * tread, z0 + (i + 1) * rh))
                else:          # going down: tread first, then the riser
                    out.append((t0 + (i + 1) * tread, z0 + i * rh))
                    out.append((t0 + (i + 1) * tread, z0 + (i + 1) * rh))
        else:
            out.append((t1, z1))
    clean = [out[0]]
    for p in out[1:]:
        if abs(p[0] - clean[-1][0]) > 1e-6 or abs(p[1] - clean[-1][1]) > 1e-6:
            clean.append(p)
    return clean


def build(rd, W):
    mb = C.MeshBuilder(rd["name"], [PAVE, KERB])
    pts, zs, lows = rd["pts"], rd["z"], rd["low"]
    n = len(pts)
    x0, y0 = pts[0]
    ux, uy = pts[-1][0] - x0, pts[-1][1] - y0
    ln = math.hypot(ux, uy) or 1
    ux, uy = ux / ln, uy / ln
    nx, ny = -uy, ux                                   # left of travel
    ts = [(p[0] - x0) * ux + (p[1] - y0) * uy for p in pts]
    bases = [min(lows[k], zs[k]) - 0.8 for k in range(n)]

    def base_at(t):
        for k in range(n - 1):
            if ts[k] - 1e-6 <= t <= ts[k + 1] + 1e-6:
                f = (t - ts[k]) / max(1e-6, ts[k + 1] - ts[k])
                return bases[k] + (bases[k + 1] - bases[k]) * f
        return bases[-1]

    def P(t, off, z):
        x = x0 + ux * t + nx * off
        y = y0 + uy * t + ny * off
        return (x, -y, z)                              # UE -> Blender (FBX import mirrors Y back)

    sec = long_section(ts, zs)
    offs = [W / 2, W / 2 - KERB_W, -(W / 2 - KERB_W), -W / 2]
    for (ta, za), (tb, zb) in zip(sec, sec[1:]):
        top_a = [P(ta, o, za) for o in offs]
        top_b = [P(tb, o, zb) for o in offs]
        for j in range(3):                               # kerb | paving | kerb (a riser when ta == tb)
            mb.face([top_a[j], top_a[j + 1], top_b[j + 1], top_b[j]], KERB if (j != 1 or abs(ta - tb) < 1e-6) else PAVE)
        if tb - ta < 1e-6:                               # a riser: its side faces are part of the neighbouring treads
            continue
        ba, bb = min(base_at(ta), za - 0.8), min(base_at(tb), zb - 0.8)
        for o in (W / 2, -W / 2):                         # retaining faces down into the ground
            mb.face([P(ta, o, za), P(tb, o, zb), P(tb, o, bb), P(ta, o, ba)], KERB)
        mb.face([P(ta, W / 2, ba), P(tb, W / 2, bb), P(tb, -W / 2, bb), P(ta, -W / 2, ba)], KERB)
    for (t, z) in (sec[0], sec[-1]):                      # square ends
        b = min(base_at(t), z - 0.8)
        mb.face([P(t, o, z) for o in offs] + [P(t, -W / 2, b), P(t, W / 2, b)], KERB)
    ob, ucx = mb.finish(C.collection("Roads"), uv_scale=0.5, recalc=True)
    C.export_asset(ob, [], "Roads")
    steps = sum(1 for (ta, za), (tb, zb) in zip(sec, sec[1:]) if abs(ta - tb) < 1e-6)
    print("BUILT", rd["name"], len(ob.data.polygons), "len", round(ln, 1), "steps", steps)


def main():
    C.reset_scene()
    src = os.path.join(C.ROOT, "Saved", "road_mesh.json")
    data = json.load(open(src, encoding="utf-8"))
    out = os.path.join(C.EXPORT, "Roads")
    if os.path.isdir(out):
        for f in os.listdir(out):
            if f.startswith("SM_Road_") and f.endswith(".fbx"):
                os.remove(os.path.join(out, f))
    for rd in data["roads"]:
        if len(rd["pts"]) >= 2:
            build(rd, rd.get("w", data["width"]))
    C.save_blend("CK_Roads")


if __name__ == "__main__":
    main()
