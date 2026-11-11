"""Orderly town layout: every house (landmarks excepted) is re-placed in straight rows along streets parallel to
the lake's long axis (X). Fronts of a row share one building line, houses stand on flat dry ground only,
a stone plinth takes up small slopes, crystals on the plot are cleared.
CK_ARGS: pitch=48 (street spacing m), gap=1.5 (between houses), seed=7, dry=0|1
"""
import json
import math
import os
import random
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import ck_level_common as L  # noqa: E402

importlib.reload(L)
from ck_level_common import M, rot, v  # noqa: E402

ARGS = globals().get("CK_ARGS", {})
E = L.EAS
PITCH = float(ARGS.get("pitch", "48"))
GAP = float(ARGS.get("gap", "1.5"))
STREET_HALF = 4.0                     # carriageway + pavement each side of the street centre line
DRY = ARGS.get("dry", "0") == "1"
STONE = "/Game/CrystalKingdom/Materials/Instances/MI_StoneTrim"
HOUSES = ("House_0", "Town_", "TowerHouse", "DomeHouse", "Gatehouse", "Manor", "Courtyard")
WEIGHTS = [("House_01", 3), ("House_02", 3), ("House_03", 3), ("House_04", 3), ("House_05", 3), ("House_06", 3),
           ("Town_01", 5), ("Town_02", 5), ("TowerHouse", 2.5), ("DomeHouse", 2.5), ("Gatehouse", 1.5), ("Manor", 1.5)]
LANDMARK_KEYS = ("Loggia", "Hall", "Cathedral", "TowerRound", "TowerSquare", "Bridge", "Stair", "Courtyard_keep")
CRYSTALS = ("CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Crystals/Landmarks", "CK/Rocks/Shore", "CK/Crystals/Foreground", "CK/Landscape")


def mesh_name(a):
    c = a.static_mesh_component if isinstance(a, unreal.StaticMeshActor) else None
    return c.static_mesh.get_name() if c and c.static_mesh else ""


# ---------------------------------------------------------------- 1. clear the old houses
removed = 0
keep_boxes = []          # landmarks + quay walls: no house may touch them
for a in E.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith("CK/Architecture") or f.startswith("CK/Architecture/Manual"):
        continue
    nm = mesh_name(a)
    if f.startswith("CK/Architecture/TerraceWalls"):
        if isinstance(a, unreal.StaticMeshActor):
            o, e = a.get_actor_bounds(False)
            keep_boxes.append((o.x / M - e.x / M, o.x / M + e.x / M, o.y / M - e.y / M, o.y / M + e.y / M))
        continue
    is_house = any(k in nm for k in HOUSES) or nm == "Cube" or f.startswith(("CK/Architecture/Streets", "CK/Architecture/Lots",
                                                                               "CK/Architecture/Fill", "CK/Architecture/Plinths"))
    if is_house:
        if not DRY:
            E.destroy_actor(a)
        removed += 1
    elif isinstance(a, unreal.StaticMeshActor):
        o, e = a.get_actor_bounds(False)
        keep_boxes.append((o.x / M - e.x / M - 3, o.x / M + e.x / M + 3, o.y / M - e.y / M - 3, o.y / M + e.y / M + 3))
for a in E.get_all_level_actors():   # warm fills that lit the old house positions
    if str(a.get_folder_path()).startswith(("CK/Lighting/Windows", "CK/Lighting/BuildingFill")) and not DRY             and not a.get_actor_label().startswith("CK_LandmarkFill"):
        E.destroy_actor(a)
print("old houses removed", removed, "landmark/wall boxes", len(keep_boxes))

# ---------------------------------------------------------------- 2. ground cache (1 m)
L.reset_terrain_cache()
_g = {}


FLOOR = [t for t in L._terrain() if "Shell" not in t[0].static_mesh.get_name()]   # cave floor + terraces, never the wall shell


def floor_z(x, y):
    best = None
    X, Y = x * M, y * M
    for comp, x0, x1, y0, y1 in FLOOR:
        if not (x0 <= X <= x1 and y0 <= Y <= y1):
            continue
        r = comp.line_trace_component(unreal.Vector(X, Y, 11500), unreal.Vector(X, Y, -4000), True, False, False)
        if isinstance(r, tuple) and r[1].length() > 0.5:
            z = r[0].z / M
            if z < 60 and r[1].z > 0.5 and (best is None or z > best):      # an upward-facing floor, not a wall or overhang
                best = z
    return best


def G(x, y):
    k = (round(x), round(y))
    if k not in _g:
        _g[k] = floor_z(k[0], k[1])
    return _g[k]


SIZES = {}
for mname, _ in WEIGHTS:
    sm = unreal.load_asset("/Game/CrystalKingdom/Meshes/Architecture/SM_Bldg_" + mname)
    b = sm.get_bounding_box()
    SIZES[mname] = (b.min.x / M, b.max.x / M, b.min.y / M, b.max.y / M)


def pick(rng):
    t = rng.uniform(0, sum(w for _, w in WEIGHTS))
    for m, w in WEIGHTS:
        t -= w
        if t <= 0:
            return m
    return WEIGHTS[-1][0]


def plot_ok(x0, x1, y0, y1):
    """Flat, dry, inside the cave, clear of landmarks/walls and of the camera foreground. Returns (floor, low) or None."""
    if x0 < 45 and y1 > -45 and y0 < 55:
        return None
    for b0, b1, c0, c1 in keep_boxes:
        if not (x1 < b0 or b1 < x0 or y1 < c0 or c1 < y0):
            return None
    zs = []
    nx = max(2, int((x1 - x0) / 3) + 1)
    ny = max(2, int((y1 - y0) / 3) + 1)
    for i in range(nx + 1):
        for j in range(ny + 1):
            z = G(x0 - 1 + (x1 - x0 + 2) * i / nx, y0 - 1 + (y1 - y0 + 2) * j / ny)   # 1 m margin round the plot
            if z is None or z < 0.15 or z > float(ARGS.get("max_floor", "35")):   # no houses up on the cave-wall slopes
                return None
            zs.append(z)
    if max(zs) - min(zs) > float(ARGS.get("flat", "1.2")):
        return None
    # 3 m clear of the cave wall: floor all round, and no shell overhang above the plot edge
    for x, y in ((x0 - 3, y0 - 3), (x1 + 3, y0 - 3), (x1 + 3, y1 + 3), (x0 - 3, y1 + 3),
                 ((x0 + x1) / 2, y0 - 3), ((x0 + x1) / 2, y1 + 3), (x0 - 3, (y0 + y1) / 2), (x1 + 3, (y0 + y1) / 2)):
        fz = G(x, y)
        if fz is None:
            return None
        gz = L.ground_z(x, y)
        if gz is not None and gz - fz > 0.5:
            return None
    return max(zs), min(zs)


# ---------------------------------------------------------------- 3. rows
rng = random.Random(int(ARGS.get("seed", "7")))
lake_y = 5.0
streets = [lake_y + PITCH / 2 + PITCH * k for k in range(-6, 6)]
placed = []
taken = []
for ys in streets:
    for side in (-1, 1):                         # -1: row below the street (faces +Y), +1: row above (faces -Y)
        front = ys + side * STREET_HALF          # common building line of this row
        x = -40.0
        while x < 450:
            mname = pick(rng)
            bx0, bx1, by0, by1 = SIZES[mname]
            w, d = bx1 - bx0, by1 - by0
            if side < 0:     # yaw 0: facade (local max Y) on the line, house extends to -Y
                px0, px1, py0, py1 = x, x + w, front - d, front
            else:            # yaw 180: facade toward -Y
                px0, px1, py0, py1 = x, x + w, front, front + d
            if any(not (px1 + GAP / 2 < t0 or t1 < px0 - GAP / 2 or py1 + 1 < u0 or u1 < py0 - 1) for t0, t1, u0, u1 in taken):
                x += 2.0
                continue
            ok = plot_ok(px0, px1, py0, py1)
            if ok is None:
                x += 2.0
                continue
            floor, low = ok
            placed.append((mname, side, px0, px1, py0, py1, floor, low))
            taken.append((px0, px1, py0, py1))
            x = px1 + GAP
print("houses planned", len(placed), "on", len(streets), "streets")

if DRY:
    raise SystemExit

# ---------------------------------------------------------------- 4. spawn
n_pl = cleared = 0
for i, (mname, side, px0, px1, py0, py1, floor, low) in enumerate(placed):
    bx0, bx1, by0, by1 = SIZES[mname]
    if side < 0:
        yaw, lx, ly = 0.0, px0 - bx0, py1 - by1
    else:
        yaw, lx, ly = 180.0, px1 + bx0, py0 + by1
    # every house stands on a dressed-stone base course sunk 1 m below the lowest ground: no gap anywhere under the floor
    base = low - 1.0
    L.spawn_mesh("/Engine/BasicShapes/Cube", v((px0 + px1) / 2, (py0 + py1) / 2, (floor + base) / 2), rot(),
                 (px1 - px0 + 0.8, py1 - py0 + 0.8, floor - base), folder="CK/Architecture/Town", material=STONE,
                 label="Town_Plinth_%03d" % i)
    n_pl += 1
    L.spawn_mesh("Architecture/SM_Bldg_" + mname, v(lx, ly, floor), rot(yaw=yaw), 1.0, folder="CK/Architecture/Town",
                 label="Town_SM_Bldg_%s_%03d" % (mname, i))
for a in E.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith(CRYSTALS):
        continue
    o, e = a.get_actor_bounds(False)
    if (o.z - e.z) / M > 35:
        continue
    x0, x1, y0, y1 = (o.x - e.x * 0.7) / M, (o.x + e.x * 0.7) / M, (o.y - e.y * 0.7) / M, (o.y + e.y * 0.7) / M
    if any(not (x1 < t0 - 1 or t1 + 1 < x0 or y1 < u0 - 1 or u1 + 1 < y0) for t0, t1, u0, u1 in taken):
        E.destroy_actor(a)
        cleared += 1
# warm facade fills: one per 40 m of row, in the street in front of the houses
rows = {}
for mname, side, px0, px1, py0, py1, floor, low in placed:
    rows.setdefault((round(py0 if side > 0 else py1, 1), side), []).append(((px0 + px1) / 2, floor))
nl = 0
for (yline, side), hs in rows.items():
    hs.sort()
    k = 0
    while k < len(hs):
        grp = [h for h in hs if hs[k][0] <= h[0] < hs[k][0] + 40]
        cx = sum(h[0] for h in grp) / len(grp)
        cz = max(h[1] for h in grp)
        pl = L.spawn_class(unreal.PointLight, v(cx, yline - side * 6, cz + 9), folder="CK/Lighting/BuildingFill", label="CK_TownFill_%03d" % nl)
        pc = pl.get_component_by_class(unreal.PointLightComponent)
        pc.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
        pc.set_editor_property("intensity", float(ARGS.get("bfill", "16000")) * (1.0 + math.hypot(cx, yline) / 300.0))
        pc.set_editor_property("attenuation_radius", 3500.0)
        pc.set_editor_property("cast_shadows", False)
        pc.set_editor_property("light_color", unreal.Color(r=255, g=226, b=190, a=255))
        pc.set_editor_property("volumetric_scattering_intensity", 0.0)
        nl += 1
        k += len(grp)
with open(os.path.join(unreal.Paths.project_saved_dir(), "town_rows.json"), "w", encoding="utf-8") as fh:
    json.dump({"streets": streets, "street_half": STREET_HALF, "houses": placed}, fh)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print("town: houses", len(placed), "plinths", n_pl, "crystals cleared", cleared, "fills", nl)
