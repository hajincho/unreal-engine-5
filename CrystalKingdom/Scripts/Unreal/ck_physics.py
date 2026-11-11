"""Physical-support audit for every solid in CK_Main.
  ground objects (houses, landmarks, quay walls, floor crystals, rocks, street furniture) must rest on something
  below them; ceiling crystals / spikes must be anchored in the cave roof; wall crystals must touch the cave wall.
Support is tested by component line traces at 9 points under the footprint against the terrain and every other
solid (collision is switched to query-only for the duration so no-collision meshes still count as support).
CK_ARGS: fix=0|1   ->  Saved/physics.json / physics_fix.json
Fixes: unsupported crystals/rocks/props drop onto what is below (embedded a little); a building or wall piece with
its centre supported but edges overhanging gets a stone footing down to the ground; hung pieces are pushed up into
the roof; wall crystals are pushed into the nearest wall; anything with nothing at all below/above is removed.
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import ck_level_common as L  # noqa: E402

importlib.reload(L)
from ck_level_common import M, rot, v  # noqa: E402

ARGS = globals().get("CK_ARGS", {})
FIX = ARGS.get("fix", "0") == "1"
E = L.EAS
STONE = "/Game/CrystalKingdom/Materials/Instances/MI_StoneTrim"
TOL = 0.3            # m: contact tolerance

if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError("editor is in Play mode - run ck_endplay.py first")


def kind_of(f, bottom):
    if f.startswith(("CK/Cave", "CK/Rocks/Terraces", "CK/Water", "CK/Lighting", "CK/Cameras")):
        return None
    if f.startswith(("CK/Crystals/Ceiling", "CK/Rocks/Ceiling")):
        return "hung"
    if f.startswith("CK/Crystals/Walls"):
        return "wall"
    if f.startswith("CK/Crystals/Dense") and bottom > 35:
        return "hung"
    if f.startswith("CK/"):
        return "ground"
    return None


solids = []
restore = []
for a in E.get_all_level_actors():
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    comp = a.static_mesh_component
    if comp is None or comp.static_mesh is None:
        continue
    f = str(a.get_folder_path())
    o, e = a.get_actor_bounds(False)
    bottom, top = (o.z - e.z) / M, (o.z + e.z) / M
    k = kind_of(f, bottom)
    terrain = f.startswith(("CK/Cave", "CK/Rocks/Terraces"))
    if k is None and not terrain:
        continue
    if comp.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION:
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        restore.append(comp)
    solids.append({"a": a, "comp": comp, "f": f, "k": k, "terrain": terrain, "o": (o.x / M, o.y / M, o.z / M),
                   "e": (e.x / M, e.y / M, e.z / M), "bottom": bottom, "top": top, "label": a.get_actor_label(),
                   "mesh": comp.static_mesh.get_name()})
CELL = 20.0
grid = {}
for s in solids:
    x0, x1 = s["o"][0] - s["e"][0], s["o"][0] + s["e"][0]
    y0, y1 = s["o"][1] - s["e"][1], s["o"][1] + s["e"][1]
    for gx in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
        for gy in range(int(math.floor(y0 / CELL)), int(math.floor(y1 / CELL)) + 1):
            grid.setdefault((gx, gy), []).append(s)


def cands(x, y):
    for s in grid.get((int(math.floor(x / CELL)), int(math.floor(y / CELL))), ()):
        if s["o"][0] - s["e"][0] - 0.1 <= x <= s["o"][0] + s["e"][0] + 0.1 and s["o"][1] - s["e"][1] - 0.1 <= y <= s["o"][1] + s["e"][1] + 0.1:
            yield s


def hit_vec(comp, p0, p1):
    r = comp.line_trace_component(v(*p0), v(*p1), True, False, False)
    if isinstance(r, tuple) and r[1].length() > 0.5:
        return r[0]
    return None


def hit(comp, p0, p1):
    p = hit_vec(comp, p0, p1)
    return None if p is None else p.z / M


def hit_up(comp, p0, p1, depth=0):
    """Downward trace: height of the first upward-facing surface (a floor / a top), ignoring walls and overhangs."""
    r = comp.line_trace_component(v(*p0), v(*p1), True, False, False)
    if isinstance(r, tuple) and r[1].length() > 0.5:
        if r[1].z > 0.35:
            return r[0].z / M
        # a wall or overhang first: keep looking just below it
        z = r[0].z / M - 0.05
        if z > p1[2] and depth < 25:
            return hit_up(comp, (p0[0], p0[1], z), p1, depth + 1)
    return None


def samples(s, inset=0.6):
    ox, oy, _ = s["o"]
    ex, ey, _ = s["e"]
    return [(ox + ex * inset * i, oy + ey * inset * j) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def ground_contact(s):
    """Per sample: 0 if something supports the base there (surface between base-TOL and mid-height), else the drop
    to the highest surface below (None = nothing below)."""
    out = []
    zt = s["top"] + 1.0
    for x, y in samples(s):
        best_below = None
        ok = False
        for c in cands(x, y):
            if c is s or c["k"] == "hung":
                continue
            if not c["terrain"] and c["bottom"] > s["bottom"] + 0.3:     # a support starts at or below our base
                continue
            hz = hit_up(c["comp"], (x, y, zt), (x, y, s["bottom"] - 80))
            if hz is None:
                continue
            if hz >= s["bottom"] - TOL:     # an upward-facing surface at/above the base: resting on it, sunk into it or buried
                ok = True
                break
            if hz < s["bottom"] - TOL and (best_below is None or hz > best_below):
                best_below = hz
        out.append(0.0 if ok else (None if best_below is None else s["bottom"] - best_below))
    return out


IDX = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def stable(g):
    """Centre of mass held: the centre sample rests on something, or it is held on both sides along both axes."""
    S = {IDX[n] for n, x in enumerate(g) if x == 0.0}
    return (0, 0) in S or ({i for i, _ in S} >= {-1, 1} and {j for _, j in S} >= {-1, 1}), S


def roof_contact(s):
    out = []
    zb = s["bottom"] - 1.0
    for x, y in samples(s, 0.4)[::2]:
        best = None
        ok = False
        for c in cands(x, y):
            if not (c["terrain"] or c["f"].startswith("CK/Rocks/Ceiling")) or c is s:
                continue
            hz = hit(c["comp"], (x, y, zb), (x, y, s["top"] + 80))
            if hz is None:
                continue
            if s["bottom"] + 0.3 * (s["top"] - s["bottom"]) <= hz <= s["top"] + TOL:
                ok = True
                break
            if hz > s["top"] + TOL and (best is None or hz < best):
                best = hz
        out.append(0.0 if ok else (None if best is None else best - s["top"]))
    return out


def wall_contact(s):
    ox, oy, oz = s["o"]
    best = None
    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        reach = abs(dx) * s["e"][0] + abs(dy) * s["e"][1] + abs(dz) * s["e"][2]
        end = (ox + dx * 80, oy + dy * 80, oz + dz * 80)
        for c in solids:
            if not c["terrain"]:
                continue
            ce, co = c["e"], c["o"]
            if abs(co[0] - ox) > ce[0] + 80 or abs(co[1] - oy) > ce[1] + 80:
                continue
            p = hit_vec(c["comp"], (ox, oy, oz), end)
            if p is None:
                continue
            d = math.sqrt((p.x / M - ox) ** 2 + (p.y / M - oy) ** 2 + (p.z / M - oz) ** 2)
            if best is None or d - reach < best[0]:
                best = (d - reach, (dx, dy, dz))
    return best


report = {"fix": FIX, "ground": [], "hung": [], "wall": []}
removed = moved = footings = 0
for s in solids:
    if s["k"] == "ground":
        g = ground_contact(s)
        st, S = stable(g)
        rigid = s["f"].startswith("CK/Architecture")
        if st or (S and s["f"].startswith(("CK/Architecture/Footings", "CK/Landscape"))):
            continue
        drops = [x for x in g if x is not None and x > 0]
        report["ground"].append([s["label"], s["f"], round(s["o"][0], 1), round(s["o"][1], 1), len(S), round(min(drops), 2) if drops else None])
        if not FIX or s["f"].startswith("CK/Roads"):     # roads are rebuilt by ck_streets.py, never nudged piecemeal
            continue
        a = s["a"]
        quay = s["f"].startswith("CK/Architecture/TerraceWalls")
        if rigid and (S or quay or (drops and min(drops) > 3.0)) and drops:
            # partly held / quay wall / far above the ground: a dressed-stone footing under the whole base, never a jump
            low = s["bottom"] - max(drops)
            b = s["comp"].static_mesh.get_bounding_box()
            sc = a.get_actor_scale3d()
            t = a.get_actor_transform()
            c = t.transform_location(unreal.Vector((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, 0))
            L.spawn_mesh("/Engine/BasicShapes/Cube", v(c.x / M, c.y / M, (s["bottom"] + low) / 2), rot(yaw=a.get_actor_rotation().yaw),
                         ((b.max.x - b.min.x) / M * abs(sc.x) + 0.3, (b.max.y - b.min.y) / M * abs(sc.y) + 0.3, s["bottom"] - low + 0.6),
                         folder="CK/Architecture/Footings", material=STONE, label=s["label"] + "_Footing")
            footings += 1
        elif drops:
            emb = 0.02 if s["f"].startswith("CK/Landscape") else (0.0 if rigid else 0.35)
            a.set_actor_location(a.get_actor_location() - unreal.Vector(0, 0, (min(drops) + emb) * M), False, False)
            moved += 1
        else:
            E.destroy_actor(a)
            removed += 1
    elif s["k"] == "hung":
        up = s["a"].get_actor_transform().transform_direction(unreal.Vector(0, 0, 1))
        if up.z > 0.3 and "Spike" not in s["mesh"]:
            # an upright (tips-up) crystal up in the air: if nothing holds it from below it must hang root-first from
            # the roof - flip it 180 degrees about its own centre so the broad base faces the rock and the tips point down
            gc = ground_contact(s)
            if stable(gc)[0]:
                continue
            down = [x for x in gc if x is not None and x > 0]
            rc = [x for x in roof_contact(s) if x is not None]
            if down and (not rc or min(down) <= min(rc) + (s["top"] - s["bottom"])):
                report.setdefault("stood", []).append([s["label"], round(s["o"][0], 1), round(s["o"][1], 1), round(min(down), 1)])
                if FIX:     # the floor is nearer: let it stand on it, base sunk 0.4 m
                    s["a"].set_actor_location(s["a"].get_actor_location() - unreal.Vector(0, 0, (min(down) + 0.4) * M), False, False)
                    moved += 1
                continue
            report.setdefault("flipped", []).append([s["label"], round(s["o"][0], 1), round(s["o"][1], 1)])
            if not FIX:
                continue
            a = s["a"]
            o0, _ = a.get_actor_bounds(False)
            a.set_actor_rotation(unreal.MathLibrary.compose_rotators(unreal.Rotator(180.0, 0.0, 0.0), a.get_actor_rotation()), False)
            o1, e1 = a.get_actor_bounds(False)
            a.set_actor_location(a.get_actor_location() + (o0 - o1), False, False)
            o1, e1 = a.get_actor_bounds(False)
            s["o"], s["e"] = (o1.x / M, o1.y / M, o1.z / M), (e1.x / M, e1.y / M, e1.z / M)
            s["bottom"], s["top"] = (o1.z - e1.z) / M, (o1.z + e1.z) / M
        g = roof_contact(s)
        if any(x == 0.0 for x in g):
            continue
        ups = [x for x in g if x is not None and x > 0]
        report["hung"].append([s["label"], s["f"], round(s["o"][0], 1), round(s["o"][1], 1), round(min(ups), 2) if ups else None])
        if FIX:
            if ups:
                s["a"].set_actor_location(s["a"].get_actor_location() + unreal.Vector(0, 0, (min(ups) + 0.8) * M), False, False)
                moved += 1
            else:
                E.destroy_actor(s["a"])
                removed += 1
    elif s["k"] == "wall":
        b = wall_contact(s)
        if b is not None and b[0] <= TOL:
            continue
        report["wall"].append([s["label"], round(s["o"][0], 1), round(s["o"][1], 1), None if b is None else round(b[0], 2)])
        if FIX:
            if b is None or b[0] > 25:
                E.destroy_actor(s["a"])
                removed += 1
            else:
                dx, dy, dz = b[1]
                s["a"].set_actor_location(s["a"].get_actor_location() + unreal.Vector(dx, dy, dz) * ((b[0] + 0.6) * M), False, False)
                moved += 1

for comp in restore:                      # put the original no-collision setting back
    try:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
report["moved"], report["removed"], report["footings"] = moved, removed, footings
if FIX:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
with open(os.path.join(unreal.Paths.project_saved_dir(), "physics_fix.json" if FIX else "physics.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print("PHYSICS", "fix" if FIX else "scan", "| upright in air: flip to roof", len(report.get("flipped", [])), "stand on floor", len(report.get("stood", [])),
      "| unsupported ground", len(report["ground"]), "| unanchored hung", len(report["hung"]),
      "| loose wall crystals", len(report["wall"]), "| moved", moved, "removed", removed, "footings", footings)
