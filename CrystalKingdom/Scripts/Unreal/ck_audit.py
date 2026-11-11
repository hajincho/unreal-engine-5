"""Level audit for CK_Main: building overlaps, crystals inside houses, floating objects, road fragments and gaps,
road slabs through buildings, broken balustrade runs.
CK_ARGS: fix=0|1 (repair what it finds), report=Saved/audit.json
"""
import importlib
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_level_common as L  # noqa: E402

importlib.reload(L)
from ck_level_common import M, rot, v  # noqa: E402

ARGS = globals().get("CK_ARGS", {})
FIX = ARGS.get("fix", "0") == "1"
ROAD_KEYS = ("Bridge", "Stair", "Plaza", "Gallery", "Arcade")
CRYSTAL_FOLDERS = ("CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Crystals/Walls", "CK/Crystals/Landmarks",
                   "CK/Rocks/Shore", "CK/Rocks/Submerged")
REPORT = {"fix": FIX}
WORLD = L.world()
if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor() or WORLD is None:
    raise RuntimeError("editor is in Play mode - run ck_endplay.py first")


def mesh_name(a):
    c = a.static_mesh_component if isinstance(a, unreal.StaticMeshActor) else None
    return c.static_mesh.get_name() if c and c.static_mesh else ""


def footprint(a, grow=0.0):
    sm = a.static_mesh_component.static_mesh
    b = sm.get_bounding_box()
    t = a.get_actor_transform()
    pts = []
    for x, y in ((b.min.x, b.min.y), (b.max.x, b.min.y), (b.max.x, b.max.y), (b.min.x, b.max.y)):
        p = t.transform_location(unreal.Vector(x, y, 0))
        pts.append((p.x / M, p.y / M))
    if grow:
        cx = sum(p[0] for p in pts) / 4
        cy = sum(p[1] for p in pts) / 4
        out = []
        for x, y in pts:
            dx, dy = x - cx, y - cy
            dl = math.hypot(dx, dy) or 1
            out.append((x + dx / dl * grow * 1.414, y + dy / dl * grow * 1.414))
        pts = out
    return pts


def door_of(a):
    sm = a.static_mesh_component.static_mesh
    b = sm.get_bounding_box()
    p = a.get_actor_transform().transform_location(unreal.Vector((b.min.x + b.max.x) / 2, b.max.y + 250, 0))
    return (p.x / M, p.y / M)


def sat_overlap(a, b, shrink=0.5):
    for poly in (a, b):
        for k in range(len(poly)):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % len(poly)]
            ax, ay = -(y1 - y0), x1 - x0
            ln = math.hypot(ax, ay) or 1
            ax, ay = ax / ln, ay / ln
            pa = [x * ax + y * ay for x, y in a]
            pb = [x * ax + y * ay for x, y in b]
            if max(pa) - shrink <= min(pb) + shrink or max(pb) - shrink <= min(pa) + shrink:
                return False
    return True


def poly_dist(poly, x, y):
    """Signed distance from (x, y) to a convex polygon (negative inside)."""
    n = len(poly)
    area = sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n))
    sgn = 1 if area > 0 else -1
    inside = True
    best = 1e9
    for k in range(n):
        x0, y0 = poly[k]
        x1, y1 = poly[(k + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        ln2 = ex * ex + ey * ey or 1
        t = max(0.0, min(1.0, ((x - x0) * ex + (y - y0) * ey) / ln2))
        best = min(best, math.hypot(x - (x0 + ex * t), y - (y0 + ey * t)))
        if sgn * (ex * (y - y0) - ey * (x - x0)) < 0:
            inside = False
    return -best if inside else best


def rank(folder):
    if folder.startswith(("CK/Architecture/Streets", "CK/Architecture/Lots", "CK/Architecture/Fill")):
        return 0
    if folder.startswith("CK/Architecture/Far"):
        return 1
    return 2


def support_z(x, y, z_from, ignore):
    """Highest surface below (x, y, z_from) in metres, ignoring `ignore` actors (anything: terrain, roads, plinths)."""
    r = unreal.SystemLibrary.line_trace_single(WORLD, v(x, y, z_from), v(x, y, z_from - 60), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               True, ignore, unreal.DrawDebugTrace.NONE, True)
    hr = r[1] if isinstance(r, tuple) else r
    best = None
    if hr is not None:
        t = hr.to_tuple()
        if t[0]:
            best = t[5].z / M
    g = L.ground_z(x, y)             # terrain (cave shell, terraces) is not on the visibility channel: trace it per component
    if g is not None and g <= z_from + 0.5 and (best is None or g > best):
        best = g
    elif g is not None and g > z_from + 0.5:
        best = z_from                # buried under an overhang / terrace lip: embedded, not floating
    return best


L.reset_terrain_cache()
actors = L.EAS.get_all_level_actors()

# ------------------------------------------------------------------ buildings
blds = []
for a in actors:
    f = str(a.get_folder_path())
    if not f.startswith("CK/Architecture") or f.startswith("CK/Architecture/TerraceWalls") or not isinstance(a, unreal.StaticMeshActor):
        continue
    nm = mesh_name(a)
    if not nm or nm == "Cube" or any(k in nm for k in ROAD_KEYS):
        continue
    fp = footprint(a)
    area = abs(sum(fp[k][0] * fp[(k + 1) % 4][1] - fp[(k + 1) % 4][0] * fp[k][1] for k in range(4))) / 2
    blds.append({"a": a, "f": f, "fp": fp, "rank": rank(f), "area": area, "label": a.get_actor_label(), "alive": True})

overlaps = []
for i in range(len(blds)):
    for j in range(i + 1, len(blds)):
        A, B = blds[i], blds[j]
        if not (A["alive"] and B["alive"]):
            continue
        if sat_overlap(A["fp"], B["fp"], shrink=0.4):
            loser = A if (A["rank"], A["area"]) < (B["rank"], B["area"]) else B
            overlaps.append([A["label"], B["label"], loser["label"]])
            if FIX and loser["rank"] < 2:
                loser["alive"] = False
REPORT["overlaps"] = overlaps

if FIX:
    for b in blds:
        if not b["alive"]:
            fp = footprint(b["a"])
            for a in L.EAS.get_all_level_actors():           # its stone plinth goes with it
                if str(a.get_folder_path()).startswith("CK/Architecture") and mesh_name(a) == "Cube":
                    p = a.get_actor_location() / M
                    if poly_dist(fp, p.x, p.y) < 0:
                        L.EAS.destroy_actor(a)
            L.EAS.destroy_actor(b["a"])
    blds = [b for b in blds if b["alive"]]

# ------------------------------------------------------------------ crystals / rocks inside houses
intr = []
houses = [(b, footprint(b["a"])) for b in blds]
for a in L.EAS.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith(CRYSTAL_FOLDERS):
        continue
    o, e = a.get_actor_bounds(False)
    if (o.z - e.z) / M > 35:
        continue
    x, y = o.x / M, o.y / M
    r = min(e.x, e.y) / M * 0.55
    for b, fp in houses:
        bx = [p[0] for p in fp]
        by = [p[1] for p in fp]
        if not (min(bx) - r - 2 < x < max(bx) + r + 2 and min(by) - r - 2 < y < max(by) + r + 2):
            continue
        if poly_dist(fp, x, y) < r + 0.3:
            intr.append([a.get_actor_label(), b["label"], round(x, 1), round(y, 1)])
            if FIX:
                L.EAS.destroy_actor(a)
            break
REPORT["crystals_in_buildings"] = intr

# ------------------------------------------------------------------ road slabs running through buildings
thru = []
for a in L.EAS.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith(("CK/Roads/Ring", "CK/Roads/Spur", "CK/Roads/Lane", "CK/Roads/Street", "CK/Roads/Cross", "CK/Roads/Link", "CK/Roads/Pads", "CK/Roads/Embankment")):
        continue
    p = a.get_actor_location() / M
    for b, fp in houses:
        if poly_dist(fp, p.x, p.y) < -1.0:
            thru.append([a.get_actor_label(), b["label"], round(p.x, 1), round(p.y, 1)])
            if FIX:
                L.EAS.destroy_actor(a)
            break
REPORT["roads_in_buildings"] = thru

# ------------------------------------------------------------------ floating objects
floating = []
FLOAT_FOLDERS = ("CK/Landscape", "CK/Roads/Pads", "CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Rocks/Shore")
for a in L.EAS.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith(FLOAT_FOLDERS) or not isinstance(a, unreal.StaticMeshActor):
        continue
    o, e = a.get_actor_bounds(False)
    bottom = (o.z - e.z) / M
    if bottom > 35:
        continue
    zs = [support_z(o.x / M + dx, o.y / M + dy, bottom + 0.5, [a]) for dx, dy in ((0, 0), (e.x / M * 0.4, 0), (-e.x / M * 0.4, 0),
                                                                                   (0, e.y / M * 0.4), (0, -e.y / M * 0.4))]
    zs = [z for z in zs if z is not None]
    sup = max(zs) if zs else None
    gap = bottom - sup if sup is not None else 99.0
    lim = 0.25 if f.startswith(("CK/Landscape", "CK/Roads")) else 0.8
    if gap > lim:
        floating.append([a.get_actor_label(), f, round(o.x / M, 1), round(o.y / M, 1), round(gap, 2)])
        if FIX:
            if sup is None or gap > (6.0 if f.startswith("CK/Crystals") or f.startswith("CK/Rocks") else 1.5) or f.startswith("CK/Roads/Pads"):
                L.EAS.destroy_actor(a)
            else:
                a.set_actor_location(a.get_actor_location() - unreal.Vector(0, 0, (gap + (0.02 if f.startswith("CK/Landscape") else 0.3)) * M), False, False)

# buildings: whole building above its support -> lower it; one side over a drop -> stone plinth under the footprint
bfloat = []
for b in blds:
    a = b["a"]
    o, e = a.get_actor_bounds(False)
    base = a.get_actor_location().z / M
    fp = b["fp"]
    cx = sum(p[0] for p in fp) / 4
    cy = sum(p[1] for p in fp) / 4
    samples = [(cx, cy)] + [(cx + (x - cx) * 0.8, cy + (y - cy) * 0.8) for x, y in fp]
    zs = [support_z(x, y, base + 0.4, [a]) for x, y in samples]
    if any(z is None for z in zs):
        continue
    gaps = [base - z for z in zs]
    if min(gaps) > 0.5:
        bfloat.append([b["label"], round(cx, 1), round(cy, 1), "whole", round(min(gaps), 2)])
        if FIX:
            a.set_actor_location(a.get_actor_location() - unreal.Vector(0, 0, (min(gaps) + 0.2) * M), False, False)
    elif 0.8 < max(gaps) < 15.0:
        bfloat.append([b["label"], round(cx, 1), round(cy, 1), "edge", round(max(gaps), 2)])
        if FIX:
            low = base - max(gaps)
            side = math.hypot(fp[1][0] - fp[0][0], fp[1][1] - fp[0][1])
            depth = math.hypot(fp[2][0] - fp[1][0], fp[2][1] - fp[1][1])
            yaw = math.degrees(math.atan2(fp[1][1] - fp[0][1], fp[1][0] - fp[0][0]))
            L.spawn_mesh("/Engine/BasicShapes/Cube", v(cx, cy, (base + low) / 2 - 0.3), rot(yaw=yaw), (side + 1.0, depth + 1.0, base - low + 0.6),
                         folder="CK/Architecture/Plinths", material="/Game/CrystalKingdom/Materials/Instances/MI_StoneTrim")
REPORT["floating"] = floating
REPORT["floating_buildings"] = bfloat

# ------------------------------------------------------------------ road network: fragments (connected components)
slabs = []
for a in L.EAS.get_all_level_actors():
    f = str(a.get_folder_path())
    if f.startswith(("CK/Roads/Ring", "CK/Roads/Spur", "CK/Roads/Lane", "CK/Roads/Street", "CK/Roads/Cross", "CK/Roads/Link")) and mesh_name(a) == "Cube":
        p = a.get_actor_location() / M
        yaw = math.radians(a.get_actor_rotation().yaw)
        s = a.get_actor_scale3d()
        hl = s.x / 2
        slabs.append({"a": a, "p": (p.x, p.y), "e": ((p.x - math.cos(yaw) * hl, p.y - math.sin(yaw) * hl),
                                                     (p.x + math.cos(yaw) * hl, p.y + math.sin(yaw) * hl)),
                      "w": s.y, "len": s.x})
parent = list(range(len(slabs)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


grid = {}
for i, s_ in enumerate(slabs):
    grid.setdefault((int(s_["p"][0] // 8), int(s_["p"][1] // 8)), []).append(i)


def seg_dist(p, a, b):
    ex, ey = b[0] - a[0], b[1] - a[1]
    l2 = ex * ex + ey * ey or 1
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / l2))
    return math.hypot(p[0] - a[0] - ex * t, p[1] - a[1] - ey * t)


for i, s_ in enumerate(slabs):
    gx, gy = int(s_["p"][0] // 8), int(s_["p"][1] // 8)
    for ax_ in (gx - 1, gx, gx + 1):
        for ay_ in (gy - 1, gy, gy + 1):
            for j in grid.get((ax_, ay_), ()):
                if j <= i:
                    continue
                t = slabs[j]
                d = min(seg_dist(s_["e"][0], *t["e"]), seg_dist(s_["e"][1], *t["e"]), seg_dist(t["e"][0], *s_["e"]), seg_dist(t["e"][1], *s_["e"]))
                if d < (s_["w"] + t["w"]) / 2 + 0.6:
                    parent[find(i)] = find(j)
comps = {}
for i in range(len(slabs)):
    comps.setdefault(find(i), []).append(i)
doors = [door_of(b["a"]) for b in blds]
frags = []
main = max(comps.values(), key=len) if comps else []
for root, idxs in comps.items():
    if idxs is main:
        continue
    length = sum(slabs[i]["len"] for i in idxs)
    serves = any(math.hypot(slabs[i]["p"][0] - dx, slabs[i]["p"][1] - dy) < 6 for i in idxs for dx, dy in doors)
    cxs = sum(slabs[i]["p"][0] for i in idxs) / len(idxs)
    cys = sum(slabs[i]["p"][1] for i in idxs) / len(idxs)
    frags.append([round(cxs, 1), round(cys, 1), round(length, 1), len(idxs), serves])
    if FIX and (length < 25 or not serves):
        for i in idxs:
            L.EAS.destroy_actor(slabs[i]["a"])
REPORT["road_components"] = len(comps)
REPORT["road_fragments"] = frags

# ------------------------------------------------------------------ balustrade runs (causeway + quay walls)
bal = []
for a in L.EAS.get_all_level_actors():
    f = str(a.get_folder_path())
    if mesh_name(a) == "SM_Arch_Balustrade" and f.startswith(("CK/Roads", "CK/Architecture/TerraceWalls")):
        p = a.get_actor_location() / M
        yaw = math.radians(a.get_actor_rotation().yaw)
        ln = 4.0 * a.get_actor_scale3d().x
        bal.append({"a": a, "s": (p.x, p.y), "e": (p.x + math.cos(yaw) * ln, p.y + math.sin(yaw) * ln), "z": p.z})
bp = list(range(len(bal)))


def bfind(i):
    while bp[i] != i:
        bp[i] = bp[bp[i]]
        i = bp[i]
    return i


bgrid = {}
for i, b in enumerate(bal):
    for q in (b["s"], b["e"]):
        bgrid.setdefault((int(q[0] // 4), int(q[1] // 4)), []).append(i)
for i, b in enumerate(bal):
    for q in (b["s"], b["e"]):
        gx, gy = int(q[0] // 4), int(q[1] // 4)
        for ax_ in (gx - 1, gx, gx + 1):
            for ay_ in (gy - 1, gy, gy + 1):
                for j in bgrid.get((ax_, ay_), ()):
                    if j != i and min(math.hypot(q[0] - bal[j]["s"][0], q[1] - bal[j]["s"][1]),
                                      math.hypot(q[0] - bal[j]["e"][0], q[1] - bal[j]["e"][1])) < 1.0 and abs(bal[j]["z"] - b["z"]) < 300:
                        bp[bfind(i)] = bfind(j)
runs = {}
for i in range(len(bal)):
    runs.setdefault(bfind(i), []).append(i)
short = [[round(bal[idxs[0]]["s"][0], 1), round(bal[idxs[0]]["s"][1], 1), len(idxs)] for idxs in runs.values() if len(idxs) <= 2]
if FIX:
    for idxs in runs.values():
        if len(idxs) <= 2:
            for i in idxs:
                L.EAS.destroy_actor(bal[i]["a"])
REPORT["balustrade_runs"] = len(runs)
REPORT["balustrade_fragments"] = short

# ------------------------------------------------------------------ orphans / set pieces that serve nothing
SET_PIECES = ARGS.get("set_pieces", "SM_Bldg_Plaza,SM_Arch_Gallery,SM_Arch_Arcade,SM_Arch_Stairs_Curved").split(",")
live = [x for x in L.EAS.get_all_level_actors() if isinstance(x, unreal.StaticMeshActor)]
road_sl = [x for x in live if str(x.get_folder_path()).startswith(("CK/Roads/Ring", "CK/Roads/Spur", "CK/Roads/Lane", "CK/Roads/Street", "CK/Roads/Cross", "CK/Roads/Link"))]
rgrid = {}
for x in road_sl:
    p = x.get_actor_location() / M
    rgrid.setdefault((int(p.x // 8), int(p.y // 8)), []).append((p.x, p.y, p.z, x.get_actor_scale3d().y, x.get_actor_scale3d().x))


def near_road(x, y, r):
    for gx in (int(x // 8) - 1, int(x // 8), int(x // 8) + 1):
        for gy in (int(y // 8) - 1, int(y // 8), int(y // 8) + 1):
            for px, py, pz, w, ln in rgrid.get((gx, gy), ()):
                if math.hypot(px - x, py - y) < r + max(w, ln) / 2:
                    return (px, py, pz)
    return None


house_fps = [footprint(b["a"]) for b in blds if b["a"] is not None]
orph = []
for x in live:
    f = str(x.get_folder_path())
    nm = mesh_name(x)
    p = x.get_actor_location() / M
    why = None
    if f.startswith("CK/Architecture") and any(nm.startswith(sp) for sp in SET_PIECES):
        why = "set piece"
    elif f.startswith("CK/Architecture") and not f.startswith(("CK/Architecture/Footings", "CK/Architecture/Town/Steps")) and nm == "Cube"             and not any(poly_dist(fp, p.x, p.y) < 0.5 for fp in house_fps):
        why = "plinth without house"
    elif f.startswith("CK/Roads/Pads") and near_road(p.x, p.y, 1.0) is None:
        why = "pad without road"
    elif f.startswith(("CK/Roads/Causeway", "CK/Roads/Embankment")) and near_road(p.x, p.y, 1.5) is None:
        why = "support without road"
    elif f.startswith("CK/Landscape") and near_road(p.x, p.y, 6.0) is None:
        why = "street furniture away from streets"
    if why:
        orph.append([x.get_actor_label(), why, round(p.x, 1), round(p.y, 1)])
        if FIX:
            L.EAS.destroy_actor(x)
REPORT["orphans"] = orph

if FIX:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
out = os.path.join(unreal.Paths.project_saved_dir(), "audit_fix.json" if FIX else "audit.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(REPORT, fh, ensure_ascii=False, indent=1)
print("AUDIT", "fix" if FIX else "scan", {k: (len(v_) if isinstance(v_, list) else v_) for k, v_ in REPORT.items()})
