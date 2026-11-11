"""Assemble the CK_Main level: cave, lake, rock terraces, city exterior, crystals, lighting,
atmosphere, post process, cameras and the free-fly game mode.

Re-runnable: every actor it creates lives under the "CK/..." outliner folders and is rebuilt.
CK_ARGS: stage=all|world|crystals|lighting|cameras   (default all)

World layout (meters, UE axes: X = forward from the reference camera, Y = right, Z = up).
Note: Blender->FBX mirrors Y, so building facades face local +Y and extend toward local -Y.
"""
import importlib
import math
import os
import random
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_level_common as L  # noqa: E402

importlib.reload(L)
from ck_level_common import M, rot, v  # noqa: E402

ARGS = globals().get("CK_ARGS", {})
STAGE = ARGS.get("stage", "all")
LEVEL = "/Game/CrystalKingdom/Maps/CK_Main"
MI = "/Game/CrystalKingdom/Materials/Instances/"
MASTER = "/Game/CrystalKingdom/Materials/Master/"

# exclusion zones for scatter (x, y, radius) in meters: buildings, bridge, stair, camera view lane
ZONES = [(46, -36, 24), (180, -58, 20), (178, 12, 10), (178, 30, 10), (178, -10, 10), (178, 50, 10), (190, 92, 26),
         (88, 58, 20), (380, 0, 28), (330, -75, 16), (352, 80, 16), (20, -22, 9), (100, 86, 10), (75, -48, 8),
         (13, -8, 8), (24, -20, 7)]  # last two: keep the grand-stair foot visible from CAM_Reference


def open_level():
    if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        L.LES.new_level(LEVEL)
    else:
        L.LES.load_level(LEVEL)


# --------------------------------------------------------------------------- world
def build_cave():
    for p in unreal.EditorAssetLibrary.list_assets("/Game/CrystalKingdom/Meshes/Cave", recursive=False):
        name = p.split(".")[-1]
        L.spawn_mesh(p.split(".")[0], v(0, 0, 0), folder="CK/Cave", label=name)
    print("cave ok")


def build_water():
    a = L.spawn_mesh("/Engine/BasicShapes/Plane", v(190, 0, 0), scale=(580, 420, 1), folder="CK/Water", label="CK_Lake",
                     material=MASTER + "M_Water", shadows=False)
    a.static_mesh_component.set_collision_profile_name("NoCollision")
    a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    print("water ok")


PLATEAUS = [  # mesh, x, y, yaw, scale(x,y,z)  -> walkable top z = top * sz
    ("Rocks/SM_Rock_Plateau_04", 48, -50, 10, (1.0, 1.0, 1.0)),     # west citadel terrace, top 4
    ("Rocks/SM_Rock_Plateau_06", 186, -56, 0, (1.1, 1.1, 1.0)),     # bridgehead west, top 10
    ("Rocks/SM_Rock_Plateau_01", 92, 66, 30, (1.0, 1.0, 1.0)),      # east low terrace, top 6
    ("Rocks/SM_Rock_Plateau_02", 190, 92, 0, (1.0, 1.0, 1.0)),      # east town, top 14
    ("Rocks/SM_Rock_Plateau_05", 384, 4, 0, (1.0, 1.0, 1.0)),       # far cathedral mount, top 34
    ("Rocks/SM_Rock_Plateau_03", 330, -76, 40, (1.0, 1.0, 1.0)),    # far west tower, top 24
    ("Rocks/SM_Rock_Plateau_02", 352, 82, 70, (0.75, 0.75, 1.6)),   # far east tower, top 22.4
    ("Rocks/SM_Rock_Plateau_06", 270, -40, 0, (1.2, 1.0, 2.0)),     # mid-far ledge, top 20
    ("Rocks/SM_Rock_Plateau_01", 262, 60, 0, (0.9, 0.9, 2.0)),      # mid-far east ledge, top 12
]


def build_terraces():
    for i, (mesh, x, y, yaw, s) in enumerate(PLATEAUS):
        L.spawn_mesh(mesh, v(x, y, 0), rot(yaw=yaw), s, folder="CK/Rocks/Terraces", label="Terrace_%02d" % i)
    print("terraces ok")


ARCH = [  # mesh, x, y, z, yaw, scale
    ("Architecture/SM_Bldg_Loggia", 33.5, -38.5, 4.0, 30, 1.0),
    ("Architecture/SM_Bldg_StairGrand", 14.0, -6.0, 0.0, -50, 1.0),
    ("Architecture/SM_Bldg_House_06", 70, -58, 4.0, 60, 1.0),
    ("Architecture/SM_Bldg_Hall", 176, -64, 10.0, 90, 1.0),
    ("Architecture/SM_Bldg_TowerSquare", 192, -78, 10.0, 90, 1.0),
    ("Architecture/SM_Bridge_Grand", 174, -27, 0.0, 90, 1.0),
    ("Architecture/SM_Bldg_TowerRound", 196, 100, 14.0, 0, 1.0),
    ("Architecture/SM_Bldg_House_01", 168, 104, 14.0, 180, 1.0),
    ("Architecture/SM_Bldg_House_02", 206, 78, 14.0, 135, 1.0),
    ("Architecture/SM_Bldg_House_03", 176, 76, 14.0, 155, 1.0),
    # removed: SM_Arch_Gallery (160, 70) and SM_Bldg_Plaza (76, 50) - isolated set pieces that connect nothing
    ("Architecture/SM_Bldg_House_04", 104, 84, 6.0, 165, 1.0),
    ("Architecture/SM_Bldg_House_05", 84, 92, 4.9, 120, 1.0),
    # removed: SM_Arch_Arcade (112, 60) + its curved stair (120, 52) - an arcade fragment in the open
    ("Architecture/SM_Bldg_Cathedral", 372, -20, 34.0, 90, 1.0),
    ("Architecture/SM_Bldg_TowerSquare", 326, -80, 24.0, 90, 1.0),
    ("Architecture/SM_Bldg_TowerRound", 352, 82, 22.4, 0, 1.0),
    ("Architecture/SM_Bldg_House_02", 268, -44, 20.0, 100, 1.0),
    ("Architecture/SM_Bldg_House_04", 262, 58, 12.0, 70, 1.0),
    ("Architecture/SM_Bldg_House_01", 395, 40, 17.4, 120, 1.0),
    ("Architecture/SM_Bldg_Hall", 300, 70, 6.5, 110, 1.0),
]


FAR_CITY = [  # plan step 10: denser far city in the centre of the reference view; snapped onto terrain by trace
    ("Architecture/SM_Bldg_House_05", 356, -32, 110, 1.0),
    ("Architecture/SM_Bldg_Hall", 400, -36, 90, 1.0), ("Architecture/SM_Bldg_House_02", 336, -58, 70, 1.0),
    ("Architecture/SM_Bldg_House_06", 280, -26, 95, 1.0), ("Architecture/SM_Bldg_TowerHouse", 276, -52, 0, 1.0),
    ("Architecture/SM_Bldg_House_04", 340, 62, 80, 1.0),
    ("Architecture/SM_Bldg_Manor", 412, 58, 90, 1.0), ("Architecture/SM_Bldg_Loggia", 420, 10, 90, 1.0),
]


def build_far_city():
    n = 0
    for i, (mesh, x, y, yaw, sc) in enumerate(FAR_CITY):
        gz = L.ground_z(x, y)
        if gz is None or gz < 4:
            print("  far city skip (no ground)", mesh, x, y)
            continue
        L.spawn_mesh(mesh, v(x, y, gz - 0.3), rot(yaw=yaw), sc, folder="CK/Architecture/Far", label="Far_" + mesh.split("/")[-1] + "_%02d" % i)
        n += 1
    print("far city", n)


TERRACE_TOPS = [(48, -50, 4.0), (186, -56, 10.0), (92, 66, 6.0), (190, 92, 14.0), (270, -40, 20.0), (262, 60, 12.0),
                (330, -76, 24.0), (352, 82, 22.4)]   # cathedral mount (384, 4) left out: its shaded wall read as a dark box behind the bridge


def build_terrace_walls():
    """Quay walls: one continuous run of wall + balustrade along each terrace's lake-side edge.
    Edge points are sampled every 4 degrees on the terrain only (ground_z), joined pairwise, and the run
    is broken wherever the edge jumps (> 2.5 m) so no wall fins stick out into the water."""
    L.reset_terrain_cache()
    n = 0
    for cx, cy, top in TERRACE_TOPS:
        face = math.atan2(-cy, (200 - cx) * 0.25) if cx < 300 else math.atan2(-cy * 0.3, -1.0)
        edges = []
        for k in range(-18, 19):
            ang = face + math.radians(k * 4)
            dx, dy = math.cos(ang), math.sin(ang)
            edge = None
            for r10 in range(20, 700, 5):
                r = r10 / 10.0
                g = L.ground_z(cx + dx * r, cy + dy * r)
                if g is None or g < top - 1.2:
                    edge = r - 0.4
                    break
            if edge is None or edge < 3:
                edges.append(None)
                continue
            ex, ey = cx + dx * edge, cy + dy * edge
            if math.hypot(ex - 14, ey + 6) < 18 or (ex < 45 and -45 < ey < 55):   # grand stair / camera foreground
                edges.append(None)
                continue
            edges.append((ex, ey, edge))
        # split into continuous runs
        runs, cur = [], []
        for e in edges:
            if e is None or (cur and abs(e[2] - cur[-1][2]) > 2.5):
                if len(cur) >= 3:
                    runs.append(cur)
                cur = [] if e is None else [e]
            else:
                cur.append(e)
        if len(cur) >= 3:
            runs.append(cur)
        h = top + 1.0
        rows = max(1, int(math.ceil(h / 6.0)))
        sz = h / (rows * 6.0)
        for run in runs:
            for (x0, y0, _), (x1, y1, _) in zip(run, run[1:]):
                d = math.hypot(x1 - x0, y1 - y0)
                if d < 0.3 or d > 9.0:
                    continue
                yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
                sx = (d + 0.15) / 4.0
                for row in range(rows):
                    L.spawn_mesh("Architecture/SM_Arch_Wall_Deco" if row == rows - 1 else "Architecture/SM_Arch_Wall_Plain",
                                 v(x0, y0, -1.0 + row * 6.0 * sz), rot(yaw=yaw), (sx, 1.0, sz),
                                 folder="CK/Architecture/TerraceWalls", collision=False)
                    n += 1
                L.spawn_mesh("Architecture/SM_Arch_Balustrade", v(x0, y0, top), rot(yaw=yaw), (sx, 1.0, 1.0),
                             folder="CK/Architecture/TerraceWalls", collision=False)
                n += 1
            mx, my, _ = run[len(run) // 2]      # one warm fill per run lifts the shaded face to pale marble
            pl = L.spawn_class(unreal.PointLight, v(mx + (mx - cx) * 0.15, my + (my - cy) * 0.15, top * 0.6), folder="CK/Architecture/TerraceWalls")
            pc = pl.get_component_by_class(unreal.PointLightComponent)
            pc.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
            pc.set_editor_property("intensity", float(ARGS.get("wallfill", "9000")))
            pc.set_editor_property("attenuation_radius", 2400.0)
            pc.set_editor_property("cast_shadows", False)
            pc.set_editor_property("light_color", unreal.Color(r=255, g=226, b=190, a=255))
            pc.set_editor_property("volumetric_scattering_intensity", 0.0)
    print("terrace walls", n)


# 13 house types (House_01-06 + Town_01/02, TowerHouse, DomeHouse, Gatehouse, Manor, Courtyard); spired towers ~5 %
HOUSE_WEIGHTS = [("House_01", 3), ("House_02", 3), ("House_03", 3), ("House_04", 3), ("House_05", 3), ("House_06", 3),
                 ("Town_01", 4), ("Town_02", 4), ("TowerHouse", 3), ("DomeHouse", 3), ("Gatehouse", 2),
                 ("Manor", 2.5), ("Courtyard", 1.5), ("TowerRound", 1), ("TowerSquare", 1)]
BIG_HOUSES = ("Manor", "Courtyard")


def pick_house(rng, big=True):
    pool = [(m, w) for m, w in HOUSE_WEIGHTS if big or m not in BIG_HOUSES]
    t = rng.uniform(0, sum(w for _, w in pool))
    for m, w in pool:
        t -= w
        if t <= 0:
            return m
    return pool[-1][0]


FILL_MESHES = [("Architecture/SM_Bldg_House_01", 1.0), ("Architecture/SM_Bldg_House_02", 1.0), ("Architecture/SM_Bldg_House_03", 1.0),
               ("Architecture/SM_Bldg_House_04", 1.0), ("Architecture/SM_Bldg_House_05", 1.0), ("Architecture/SM_Bldg_House_06", 1.0),
               ("Architecture/SM_Bldg_TowerRound", 1.0), ("Architecture/SM_Bldg_TowerSquare", 1.0), ("Architecture/SM_Bldg_Hall", 1.0)]


def build_city_fill(rng):
    """Plan step 6: pack the terraces with more buildings (the reference city climbs every ledge)."""
    taken = [(x, y) for _, x, y, _, _, _ in ARCH] + [(x, y) for _, x, y, _, _ in FAR_CITY]
    boxes = []   # XY bounds (m) of every standing building: pivots alone let houses spawn inside the cathedral
    for a in L.EAS.get_all_level_actors():
        f = str(a.get_folder_path())
        if f.startswith("CK/Architecture") and not f.startswith("CK/Architecture/TerraceWalls") and not f.startswith("CK/Architecture/Fill") \
                and isinstance(a, unreal.StaticMeshActor):
            o, e = a.get_actor_bounds(False)
            boxes.append((o.x / M - e.x / M, o.x / M + e.x / M, o.y / M - e.y / M, o.y / M + e.y / M))
    n = 0
    for cx, cy, top in TERRACE_TOPS + [(384, 4, 34.0)]:
        if (cx, cy) == (48, -50):  # loggia terrace: a house there hides the loggia arcade
            continue
        face = math.atan2(-cy, (200 - cx) * 0.25) if cx < 300 else math.atan2(-cy * 0.3, -1.0)
        for _ in range(40):
            ang = face + rng.uniform(-1.6, 1.6)
            r = rng.uniform(4, 40)
            x, y = cx + math.cos(ang) * r, cy + math.sin(ang) * r
            if any(math.hypot(x - tx, y - ty) < 17 for tx, ty in taken):
                continue
            if any(x0 - 9 < x < x1 + 9 and y0 - 9 < y < y1 + 9 for x0, x1, y0, y1 in boxes):
                continue
            if x < 330 and abs(math.degrees(math.atan2(y - 5, x + 8))) < 9:  # keep the bridge / far-city sight line open
                continue
            gz = L.ground_z(x, y)
            if gz is None or abs(gz - top) > 1.5:  # only on the flat terrace top
                continue
            # the footprint must also be on the terrace: probe 6 m toward the lake
            fx, fy = x + math.cos(face) * 6, y + math.sin(face) * 6
            g2 = L.ground_z(fx, fy)
            if g2 is None or abs(g2 - top) > 1.5:
                continue
            mesh, sc = "Architecture/SM_Bldg_" + pick_house(rng, big=False), 1.0
            # real-world proportions: no per-instance rescale (0.55-1.1x made identical houses look like toys or giants)
            yaw = face_yaw(x, y, math.cos(face), math.sin(face)) + rng.uniform(-25, 25)
            L.spawn_mesh(mesh, v(x, y, top - 0.3), rot(yaw=yaw), sc, folder="CK/Architecture/Fill",
                         label="Fill_" + mesh.split("/")[-1] + "_%02d" % n)
            pl = L.spawn_class(unreal.PointLight, v(x + math.cos(face) * 12, y + math.sin(face) * 12, top + 12), folder="CK/Architecture/Fill")
            pc = pl.get_component_by_class(unreal.PointLightComponent)   # plan step 4: marble facades, not dark silhouettes
            pc.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
            pc.set_editor_property("intensity", float(ARGS.get("bfill", "22000")) * (1.0 + math.hypot(x, y) / 300.0))
            pc.set_editor_property("attenuation_radius", 4500.0)
            pc.set_editor_property("cast_shadows", False)
            pc.set_editor_property("light_color", unreal.Color(r=255, g=232, b=200, a=255))
            pc.set_editor_property("volumetric_scattering_intensity", 0.0)
            taken.append((x, y))
            boxes.append((x - 8, x + 8, y - 8, y + 8))
            n += 1
    print("city fill", n)


def build_architecture():
    for i, (mesh, x, y, z, yaw, s) in enumerate(ARCH):
        L.spawn_mesh(mesh, v(x, y, z), rot(yaw=yaw), s, folder="CK/Architecture", label=mesh.split("/")[-1] + "_%02d" % i)
    print("architecture ok")


# --------------------------------------------------------------------------- crystals
LANDMARKS = [  # mesh, x, y, z, yaw, scale, material instance (None = mesh default)
    ("SM_Crystal_ColumnMass_04", 20, -40, -3, 15, (1.0, 1.0, 1.3), None),
    ("SM_Crystal_ColumnMass_01", 6, -66, 0, 0, (0.6, 0.6, 1.1), "MI_Crystal_Violet"),
    ("SM_Crystal_ColumnMass_03", 2, -50, 0, 0, (0.45, 0.45, 1.3), "MI_Crystal_Opal"),   # loggia sits between crystal columns
    ("SM_Crystal_ColumnMass_05", 58, -74, 0, 0, (0.7, 0.7, 1.25), "MI_Crystal_Opal"),
    ("SM_Crystal_ColumnMass_01", 62, -88, 0, 70, (1.1, 1.1, 1.1), None),
    ("SM_Crystal_ColumnMass_02", 112, -104, 0, 10, (1.0, 1.0, 1.0), None),
    ("SM_Crystal_ColumnMass_03", 56, 64, -2, 100, (1.0, 1.0, 1.25), None),
    ("SM_Crystal_ColumnMass_05", 132, 126, 5, 30, (1.2, 1.2, 1.1), None),
    ("SM_Crystal_ColumnMass_06", 236, 124, 8, 0, (1.2, 1.2, 1.3), None),
    ("SM_Crystal_ColumnMass_01", 300, -114, 10, 40, (1.2, 1.2, 1.2), "MI_Crystal_White"),
    ("SM_Crystal_ColumnMass_03", 412, 62, 14, 0, (1.2, 1.2, 1.3), "MI_Crystal_White"),
    ("SM_Crystal_ColumnMass_02", 430, -58, 14, 80, (1.2, 1.2, 1.3), None),
    ("SM_Crystal_ColumnMass_06", 262, -124, 5, 10, (1.0, 1.0, 1.2), None),
    ("SM_Crystal_ColumnMass_04", 240, -12, 4, 100, (0.6, 0.6, 0.55), "MI_Crystal_White"),
    ("SM_Crystal_ColumnMass_05", 350, 10, 6, 0, (0.8, 0.8, 0.8), None),
    ("SM_Crystal_ColumnMass_02", 48, 80, 0, 20, (0.8, 0.8, 0.9), "MI_Crystal_Violet"),
    ("SM_Crystal_FloorGiant_02", 150, -96, 0, 80, (1.0, 1.0, 1.0), "MI_Crystal_Violet"),
    ("SM_Crystal_FloorGiant_03", 292, 36, 4, 0, (1.1, 1.1, 1.2), None),
    ("SM_Crystal_FloorGiant_04", 422, 0, 10, 0, (1.2, 1.2, 1.4), "MI_Crystal_White"),
    ("SM_Crystal_FloorGiant_01", 98, -60, 3, 140, (0.6, 0.6, 0.7), None),
    ("SM_Crystal_FloorGiant_03", 128, 96, 5, 60, (0.7, 0.7, 0.8), "MI_Crystal_Violet"),
]


def build_crystal_landmarks():
    for i, (mesh, x, y, z, yaw, s, mi) in enumerate(LANDMARKS):
        if mesh.startswith("SM_Crystal_ColumnMass"):  # plan step 3: hex-column cliffs, low front toward the lake
            mesh = "SM_Crystal_HexCliff_%02d" % (int(mesh[-2:]) % 6 + 1)
            yaw = face_yaw(x, y, (200 - x) * 0.3, -y)
        L.spawn_mesh("Crystals/" + mesh, v(x, y, z), rot(yaw=yaw), s, folder="CK/Crystals/Landmarks",
                     label="%s_L%02d" % (mesh, i), material=(MI + mi) if mi else None)
    print("landmarks ok")


def pick(rng, base, n):
    return "Crystals/%s_%02d" % (base, rng.randint(1, n))


def build_ceiling_crystals(rng, count=int(ARGS.get("ceilcount", "170"))):
    placed = 0
    tries = 0
    while placed < count and tries < count * 6:
        tries += 1
        x = rng.uniform(20, 400)
        y = rng.uniform(-150, 150)
        # denser over the center/right of the reference view
        if rng.random() < 0.45:
            x = rng.uniform(70, 260)
            y = rng.uniform(-60, 90)
        hit = L.trace(v(x, y, 60), v(x, y, 400))
        if not hit:
            continue
        (px, py, pz), n = hit
        if pz > 200:  # skylight chimney
            continue
        if n.z > -0.55:  # sloped wall/ceiling transition: these read as sticks poking sideways, skip
            continue
        down = unreal.Vector(0, 0, -1)
        d = L.tilt(down, 4, rng)  # plan step 2: hang (near) vertically like the reference chandeliers
        mesh = pick(rng, "SM_Crystal_CeilingGiant", 5)
        s = rng.uniform(0.6, 1.2)
        loc = unreal.Vector(px * M, py * M, pz * M) - d * (550.0 * s)
        mi = rng.choice(["MI_Crystal_Opal", "MI_Crystal_Violet", "MI_Crystal_Teal", "MI_Crystal_Violet", None])
        th = rng.uniform(1.5, 2.1)  # thicker, chunkier columns
        L.spawn_mesh(mesh, loc, L.rot_from_dir(d, rng.uniform(0, 360)), (s * th, s * th, s), folder="CK/Crystals/Ceiling",
                     material=(MI + mi) if mi else None, collision=False)
        placed += 1
    for i in range(40):  # rock stalactites between crystals
        x, y = rng.uniform(-40, 430), rng.uniform(-160, 160)
        hit = L.trace(v(x, y, 60), v(x, y, 400))
        if hit and hit[0][2] < 200:
            (px, py, pz), n = hit
            d = L.tilt(n, 8, rng)
            L.spawn_mesh("Rocks/SM_Rock_CeilingSpike_%02d" % rng.randint(1, 4), unreal.Vector(px * M, py * M, pz * M) - d * 150.0,
                         L.rot_from_dir(d, rng.uniform(0, 360)), rng.uniform(0.8, 2.0), folder="CK/Rocks/Ceiling", collision=False)
    # inverted packed column masses: the dense "chandelier" hanging crystals of the reference
    for i, (x, y, s, mi) in enumerate([(70, -25, 0.5, "MI_Crystal_White"), (105, 25, 0.55, None), (140, -45, 0.6, "MI_Crystal_White"),
                                       (150, 40, 0.5, "MI_Crystal_Violet"), (200, 10, 0.55, "MI_Crystal_White"), (95, -70, 0.5, None),
                                       (230, -60, 0.5, None), (250, 60, 0.55, "MI_Crystal_White"), (45, 30, 0.45, None),
                                       (120, 75, 0.5, "MI_Crystal_White"), (300, 20, 0.6, None), (60, -60, 0.45, "MI_Crystal_Violet")]):
        if x < 70:  # near the reference camera these fill the top corner of the frame
            continue
        hit = L.trace(v(x, y, 60), v(x, y, 400))
        if not hit or hit[0][2] > 200:
            continue
        (px, py, pz), n = hit
        L.spawn_mesh("Crystals/SM_Crystal_HexCliff_%02d" % (i % 6 + 1), v(px, py, pz + 4), rot(pitch=180, yaw=rng.uniform(0, 360)),
                     (s, s, s * rng.uniform(0.55, 0.8)), folder="CK/Crystals/Ceiling", label="CeilingMass_%02d" % i,
                     material=(MI + mi) if mi else None, collision=False)
    print("ceiling crystals", placed)


def build_wall_crystals(rng, count=170):
    placed = 0
    for _ in range(count * 3):
        if placed >= count:
            break
        x = rng.uniform(-40, 430)
        z = rng.uniform(3, 135)
        if x < 90 and z > 45:
            continue
        side = rng.choice([-1, 1])
        if rng.random() < 0.2:  # end walls
            hit = L.trace(v(200, rng.uniform(-150, 150), z), v(200 + side * 400, rng.uniform(-150, 150), z))
        else:
            hit = L.trace(v(x, 0, z), v(x, side * 260, z))
        if not hit:
            continue
        (px, py, pz), n = hit
        if abs(py) < 110 and px < 380:  # only the real cave walls, never terrace sides / buildings
            continue
        if pz > 70:  # upper walls: diagonal sticks look like floating debris from the reference camera
            continue
        d = L.tilt((unreal.Vector(0, 0, 1) * 0.85 + n * 0.15).normal(), 8, rng)   # upright packed columns (reference)
        r = rng.random() * 0.6 + 0.4 if rng.random() < 0.7 else rng.random()   # favour pillars over leaning/branch shards
        if r < 0.35:
            mesh, s = pick(rng, "SM_Crystal_Wall", 4), rng.uniform(1.2, 3.0)
        elif r < 0.6:
            mesh, s = pick(rng, "SM_Crystal_Leaning", 4), rng.uniform(1.2, 3.0)
        elif r < 0.8:
            mesh, s = pick(rng, "SM_Crystal_Branch", 4), rng.uniform(1.0, 2.5)
        else:
            mesh, s = pick(rng, "SM_Crystal_Pillar", 5), rng.uniform(1.5, 3.5)
        mi = rng.choice([None, None, None, "MI_Crystal_White", "MI_Crystal_Violet", None])
        L.spawn_mesh(mesh, unreal.Vector(px * M, py * M, pz * M) - d * 80.0, L.rot_from_dir(d, rng.uniform(0, 360)), s,
                     folder="CK/Crystals/Walls", material=(MI + mi) if mi else None, collision=pz < 30)
        placed += 1
    print("wall crystals", placed)

def face_yaw(px, py, dx, dy):
    """Yaw that turns a HexCliff's low front (local +Y in UE, Blender -Y mirrored by FBX) toward (dx, dy)."""
    return math.degrees(math.atan2(-dx, dy))


def build_dense_masses(rng):
    """Plan step 2: reference-like crystal cliffs. Packed column masses on banks/terrace backs/walls + thick hanging masses."""
    placed = 0
    tries = 0
    want = int(ARGS.get("dense", "110"))
    while placed < want and tries < want * 12:
        tries += 1
        x = rng.uniform(-30, 440)
        y = rng.uniform(-175, 175)
        if not L.far_from(x, y, [(zx, zy, zr * 0.55) for zx, zy, zr in ZONES]):
            continue
        if 5 < x < 330 and abs(y) < 52:  # keep the lake / view lane open
            continue
        if x < 330 and abs(math.degrees(math.atan2(y, max(x, 1.0)))) < 38:  # never block the reference view cone (town, bridge, far city)
            continue
        if abs(math.degrees(math.atan2(y, max(x, 1.0)))) < 16:  # far wall behind the city: keep the centre open for depth
            continue
        if x < 35 and y > -45:  # beside the camera these ~100 m masses fill a quarter of the frame
            continue
        hit = L.trace(v(x, y, 150), v(x, y, -40))
        if not hit:
            continue
        (px, py, pz), n = hit
        if pz < -1.0 or n.z < 0.3:
            continue
        sc = rng.uniform(0.5, 1.8) if rng.random() < 0.5 else rng.uniform(0.8, 1.2)   # plan: big and small columns, not a barcode
        mesh = "Crystals/SM_Crystal_HexCliff_%02d" % rng.randint(1, 6)   # plan step 3: stepped hex-column cliffs
        mi = rng.choice(["MI_Crystal_Violet", "MI_Crystal_Violet", "MI_Crystal_Opal", "MI_Crystal_BlockViolet", "MI_Crystal_Block", None])
        L.spawn_mesh(mesh, v(px, py, pz - 1.5), rot(yaw=face_yaw(px, py, (200 - px) * 0.3, -py) + rng.uniform(-20, 20)),
                     (sc, sc, sc * rng.uniform(0.6, 1.6)), folder="CK/Crystals/Dense",
                     material=MI + ("MI_Crystal_Teal" if px > 280 else mi) if (mi or px > 280) else None, collision=False)
        placed += 1
    print("dense masses", placed)
    skirt = 0
    rng_main, rng = rng, random.Random(991)  # separate stream so skirts never reshuffle the rest
    extra = []   # houses added by the street / lot / fill stages also stand in front of crystal cliffs
    for a_ in L.EAS.get_all_level_actors():
        if str(a_.get_folder_path()).startswith(("CK/Architecture/Streets", "CK/Architecture/Lots", "CK/Architecture/Fill"))                 and isinstance(a_, unreal.StaticMeshActor) and a_.static_mesh_component.static_mesh                 and a_.static_mesh_component.static_mesh.get_name() != "Cube":
            p_ = a_.get_actor_location() / M
            extra.append(("", p_.x, p_.y, max(p_.z, 5.5), 0, 1.0))
    for mesh, bx, by, bz, yaw, sc in ARCH + [(m, x, y, 30.0, yw, sc) for m, x, y, yw, sc in FAR_CITY] + extra:
        if bz < 5:
            continue
        if bx < 150 and by > 30:  # low east terrace sits in front of the east town: its skirts would hide it
            continue
        for k in range(rng.randint(4, 6)):
            ang = math.radians(rng.choice([-70, -45, 0, 45, 70, 20, -25]))
            dist = rng.uniform(14, 26)
            ox, oy = bx + math.cos(ang) * dist, by + math.sin(ang) * dist
            ox = bx + 26 + abs(ox - bx)  # always behind the building (away from camera), never in front of the facade
            hit = L.trace(v(ox, oy, bz + 60), v(ox, oy, bz - 25))
            if not hit:
                continue
            (px, py, pz), n = hit
            if pz < bz - 6:
                pz = bz - 2
            ss = rng.uniform(0.3, 0.55)
            L.spawn_mesh("Crystals/SM_Crystal_HexCliff_%02d" % rng.randint(1, 6), v(px, py, pz - 1.0),
                         rot(yaw=face_yaw(px, py, -px, -py) + rng.uniform(-15, 15)),   # low front toward the camera
                         (ss, ss, ss * rng.uniform(0.9, 1.4)), folder="CK/Crystals/Dense", collision=False,
                         material=MI + rng.choice(["MI_Crystal_Violet", "MI_Crystal_Opal", "MI_Crystal_Block"]))
            skirt += 1
    print("building skirts", skirt)
    rng = rng_main
    hung = 0
    tries = 0
    while hung < int(ARGS.get("hang", "115")) and tries < 800:
        tries += 1
        x, y = rng.uniform(-20, 420), rng.uniform(-165, 165)
        hit = L.trace(v(x, y, 60), v(x, y, 400))
        if not hit or hit[0][2] > 200:
            continue
        (px, py, pz), n = hit
        if 120 < px < 330 and abs(y) < 40:  # leave the light shaft / far city readable
            continue
        if px > 200 and abs(math.degrees(math.atan2(py, px))) < 16:  # no hanging curtain in front of the far city
            continue
        if px < 70 or pz < 120:  # low ceiling / near the camera: a close chandelier fills the top corner of the frame
            continue
        if px < 330 and 12 < abs(math.degrees(math.atan2(y, max(px, 1.0)))) < 40 and px > 40:  # keep the town / loggia sectors unblocked
            continue
        sc = rng.uniform(0.35, 0.8)
        mi = rng.choice([None, None, "MI_Crystal_White", "MI_Crystal_Teal", "MI_Crystal_Violet"])
        # hex-column chandeliers: HexCliff fallback ~1.4 k tris vs 20-35 k for ColumnMass (non-Nanite GPUs draw the fallback)
        L.spawn_mesh("Crystals/SM_Crystal_HexCliff_%02d" % rng.randint(1, 6), v(px, py, pz + 4), rot(pitch=180, yaw=rng.uniform(0, 360)),
                     (sc * 1.4, sc * 1.4, sc * rng.uniform(0.6, 1.1)), folder="CK/Crystals/Dense",
                     material=(MI + mi) if mi else None, collision=False)
        hung += 1
    print("hanging masses", hung)
    build_shore_blocks(random.Random(int(ARGS.get("shoreseed", "515"))))


def build_shore_blocks(rng):
    """Plan step 5: stepped crystal blocks hugging terrace sides and banks at the waterline (reference shores)."""
    placed = 0
    want = int(ARGS.get("shore", "190"))
    tries = 0
    while placed < want and tries < want * 10:
        tries += 1
        x = rng.uniform(16, 400)
        if 164 < x < 186:  # bridge piers
            continue
        z = rng.uniform(-0.6, 9.0)
        side = rng.choice([-1, 1])
        hit = L.trace(v(x, side * 4, z), v(x, side * 220, z))
        if not hit:
            continue
        (px, py, pz), n = hit
        if abs(n.z) > 0.75:
            continue
        if px < 40 and abs(py) < 30:  # reference camera foreground
            continue
        if math.hypot(px - 14, py + 6) < 22 or math.hypot(px - 34, py + 38) < 20:  # grand stair / loggia front
            continue
        r = rng.random()
        if r < 0.55:
            mesh, sc = pick(rng, "SM_Crystal_Block", 5), rng.uniform(1.0, 2.4)
        elif r < 0.8:
            mesh, sc = pick(rng, "SM_Crystal_FloorCluster", 5), rng.uniform(0.8, 1.8)
        else:
            mesh, sc = pick(rng, "SM_Crystal_Pillar", 5), rng.uniform(0.6, 1.3)
        # sit on the waterline/face: mostly upright, leaning out of the face a little
        d = L.tilt(unreal.Vector(0, 0, 1), 3, rng)   # upright, stepped like the reference shore
        base_z = min(pz, rng.uniform(-0.8, 0.5)) if rng.random() < 0.6 else pz - 1.0
        mi = rng.choice(["MI_Crystal_Block", "MI_Crystal_Block", "MI_Crystal_BlockViolet", "MI_Crystal_Opal", None])
        L.spawn_mesh(mesh, v(px + n.x * 1.0, py + n.y * 1.0, base_z), L.rot_from_dir(d, rng.uniform(0, 360)), sc,
                     folder="CK/Crystals/Dense", material=(MI + mi) if mi else None, collision=False)
        placed += 1
    print("shore blocks", placed)


def build_floor_scatter(rng, count=420):
    placed = 0
    for _ in range(count * 4):
        if placed >= count:
            break
        x = rng.uniform(-50, 440)
        y = rng.uniform(-165, 165)
        if not L.far_from(x, y, ZONES):
            continue
        hit = L.trace(v(x, y, 120), v(x, y, -40))
        if not hit:
            continue
        (px, py, pz), n = hit
        if pz < -1.0:  # keep the open lake clear; only shallows and banks
            continue
        if 20 < px < 300 and abs(py) < 45:
            continue
        if n.z < 0.45:
            continue
        if math.hypot(px + 8, py - 5) < 14 or ("Boulder" in mesh_name_hint if False else False):  # only the camera's feet stay clean
            continue
        d = L.tilt(unreal.Vector(0, 0, 1) * 0.6 + n * 0.4, 18, rng)
        r = rng.random()
        if r < 0.28:
            mesh, s = pick(rng, "SM_Crystal_FloorCluster", 5), rng.uniform(0.8, 2.2)
        elif r < 0.45:
            mesh, s = pick(rng, "SM_Crystal_Pillar", 5), rng.uniform(0.5, 1.4)
        elif r < 0.58:
            mesh, s = pick(rng, "SM_Crystal_Broken", 4), rng.uniform(0.8, 2.0)
        elif r < 0.7:
            mesh, s = pick(rng, "SM_Crystal_Block", 5), rng.uniform(0.8, 2.0)
        elif r < 0.8:
            mesh, s = pick(rng, "SM_Crystal_Opal", 3), rng.uniform(0.6, 1.4)
        elif r < 0.88:  # branching shards read as debris; the reference shores are upright prisms
            mesh, s = pick(rng, "SM_Crystal_Pillar", 5), rng.uniform(0.5, 1.2)
        else:
            mesh, s = pick(rng, "SM_Rock_Boulder", 6).replace("Crystals/", "Rocks/"), rng.uniform(0.6, 2.0)
        mi = rng.choice([None, None, None, "MI_Crystal_Violet", "MI_Crystal_White", "MI_Crystal_Glow"]) if "Crystal" in mesh else None
        L.spawn_mesh(mesh, unreal.Vector(px * M, py * M, pz * M - 30), L.rot_from_dir(d, rng.uniform(0, 360)), s,
                     folder="CK/Crystals/Floor", material=(MI + mi) if mi else None)
        placed += 1
    print("floor scatter", placed)


def build_foreground(rng):
    """Chunky crystal blocks under/around the reference camera and submerged rocks in the shallows."""
    # kept below the eye line (camera z=7.5): bottom ~quarter of the frame like the reference
    spots = [(6, -5, 1.2), (7, 3, 1.3), (5, 9, 1.1), (10, -9, 1.1), (11, 7, 1.0), (9, 13, 1.2), (12, -2, 0.8), (5, -12, 1.1),
             (13, 11, 0.9), (6, 16, 1.1), (14, -12, 0.9), (4, 2, 1.0), (4, -7, 1.0), (10, 1, 0.75), (15, 4, 0.8), (8, -15, 1.0),
             (3, 12, 1.2), (12, 16, 0.9), (8, 8, 0.7), (9, -3, 0.9), (3, -2, 1.1), (15, -6, 0.7), (16, 14, 0.8)]
    spots = [(7, -3, 1.8), (10, 9, 2.0), (8, 20, 1.6)]   # plan: 3-4 large upright stumps framing the bottom edge
    for i, (x, y, s) in enumerate(spots):
        gz = L.ground_z(x, y)
        z = gz if gz is not None else 0.5
        L.spawn_mesh(pick(rng, "SM_Crystal_Block", 5), v(x, y, z - 0.4), rot(pitch=rng.uniform(-2, 2), yaw=rng.uniform(0, 360), roll=rng.uniform(-2, 2)),
                     s, folder="CK/Crystals/Foreground", label="FG_Block_%02d" % i,
                     material=MI + rng.choice(["MI_Crystal_Block", "MI_Crystal_Block", "MI_Crystal_BlockViolet", "MI_Crystal_Opal"]))
    for i in range(3):
        x, y = rng.uniform(0, 18), rng.uniform(-16, 18)
        hit = L.trace(v(x, y, 60), v(x, y, -40))
        if hit:
            L.spawn_mesh(pick(rng, "SM_Crystal_Shard", 6), v(hit[0][0], hit[0][1], hit[0][2] - 0.1), rot(yaw=rng.uniform(0, 360)),
                         rng.uniform(1.0, 2.5), folder="CK/Crystals/Foreground")
    for i in range(0):  # dark submerged rocks read as holes between the stumps
        x, y = rng.uniform(18, 75), rng.uniform(-22, 34)
        hit = L.trace(v(x, y, 60), v(x, y, -40))
        if hit and -6 < hit[0][2] < -0.3:
            L.spawn_mesh("Rocks/SM_Rock_Submerged_%02d" % rng.randint(1, 3), v(hit[0][0], hit[0][1], hit[0][2] - 0.6),
                         rot(yaw=rng.uniform(0, 360)), rng.uniform(0.3, 0.9), folder="CK/Rocks/Submerged")
    print("foreground ok")


def build_shore_rocks(rng, count=90):
    placed = 0
    for _ in range(count * 4):
        if placed >= count:
            break
        x, y = rng.uniform(-50, 440), rng.uniform(-170, 170)
        if not L.far_from(x, y, ZONES):
            continue
        hit = L.trace(v(x, y, 120), v(x, y, -40))
        if not hit or hit[0][2] < -3 or hit[0][2] > 30:
            continue
        if hit[0][0] < 34 and abs(hit[0][1]) < 34:  # nothing big right in front of the reference camera
            continue
        cliff_ok = abs(y) > 120 or x > 330
        mesh = rng.choice(["Rocks/SM_Rock_Boulder_%02d" % rng.randint(1, 6), "Rocks/SM_Rock_Rubble_%02d" % rng.randint(1, 4),
                           "Rocks/SM_Rock_Cliff_%02d" % rng.randint(1, 4) if cliff_ok else "Rocks/SM_Rock_Rubble_01"])
        L.spawn_mesh(mesh, v(hit[0][0], hit[0][1], hit[0][2] - 0.5), rot(yaw=rng.uniform(0, 360)), rng.uniform(0.6, 1.6),
                     folder="CK/Rocks/Shore")
        placed += 1
    print("shore rocks", placed)


# --------------------------------------------------------------------------- lighting
def set_props(obj, **kw):
    for k, val in kw.items():
        try:
            obj.set_editor_property(k, val)
        except Exception as e:  # noqa: BLE001
            print("  prop skip", type(obj).__name__, k, str(e)[:80])


# plan step 8: quality profiles. optimized = game default; cinematic = stills (old values)
PROFILE = ARGS.get("profile", "optimized")
LQ = {"cinematic": {"detail": 2.0, "lighting": 2.0, "gather": 1.5},
      "optimized": {"detail": 1.0, "lighting": 1.0, "gather": 1.0}}[PROFILE]


def build_lighting():
    # Sun through the skylight chimneys -> volumetric shafts
    sun = L.spawn_class(unreal.DirectionalLight, v(178, -12, 260), rot(pitch=-70, yaw=-150), folder="CK/Lighting", label="CK_SunShafts")
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    # sun disabled: VSM coverage ends ~200 m out and leaked light onto the far walls; shafts come from the spots below
    set_props(lc, intensity=0.0, light_color=unreal.Color(r=255, g=246, b=232, a=255), volumetric_scattering_intensity=6.0,
              cast_shadows=True, use_temperature=False, atmosphere_sun_light=False)
    # Skylight: dim teal ambient (cave has no sky; Lumen does the rest)
    sky = L.spawn_class(unreal.SkyLight, v(190, 0, 60), folder="CK/Lighting", label="CK_SkyFill")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    set_props(sc, intensity=float(ARGS.get("sky","1.3")), lower_hemisphere_is_black=False, lower_hemisphere_color=unreal.LinearColor(0.16, 0.19, 0.20, 1.0),
              source_type=unreal.SkyLightSourceType.SLS_CAPTURED_SCENE, real_time_capture=False)
    # Height fog with volumetric fog
    fog = L.spawn_class(unreal.ExponentialHeightFog, v(190, 0, 0), folder="CK/Lighting", label="CK_Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    set_props(fc, fog_density=float(ARGS.get("fog", "0.011")), fog_height_falloff=float(ARGS.get("fogfall", "0.004")),
              fog_inscattering_luminance=unreal.LinearColor(0.07, 0.12, 0.16, 1.0),   # plan: far crystals fade into blue haze
              start_distance=float(ARGS.get("fogstart", "4000")), enable_volumetric_fog=True, volumetric_fog_scattering_distribution=0.7,
              volumetric_fog_albedo=unreal.Color(r=200, g=218, b=225, a=255), volumetric_fog_extinction_scale=0.9,
              volumetric_fog_distance=45000.0, volumetric_fog_static_lighting_scattering_intensity=1.0,
              volumetric_fog_emissive=unreal.LinearColor(0.006, 0.014, 0.018, 1.0))
    # Visible god-ray shafts under the skylight chimneys (spot lights through volumetric fog)
    # plan step 3: a fan of broad beams leaning toward the camera; strong fog scattering, weak surface hit (no white puddle)
    shafts = [((160, -4, 140), -80, 175, 11.0, 1.0), ((176, -14, 140), -74, 172, 7.0, 0.7), ((150, 6, 140), -72, 178, 6.0, 0.6),
              ((190, 18, 140), -70, 185, 6.5, 0.6), ((205, -28, 140), -73, 168, 5.5, 0.5), ((168, 30, 140), -76, 190, 5.0, 0.45),
              ((138, 54, 140), -78, -170, 6.0, 0.4), ((214, 26, 140), -82, 170, 6.0, 0.4)]
    sz = float(ARGS.get("shaftz", "185"))   # plan step 2: start inside the skylight chimneys, above the hanging crystals
    shafts = [((x, y + 18, sz), pt + 6, yw + 14, c * 1.1, 0.42 if i < 5 else 0.12)   # plan: slanted from the upper right
              for i, ((x, y, _), pt, yw, c, k) in enumerate(shafts)]   # plan: 3 thick beams like the reference
    base = float(ARGS.get("shaft", "2200000"))
    vol = float(ARGS.get("shaftvol", "18"))
    cmul = float(ARGS.get("shaftcone", "0.3"))
    for i, (p, pitch, yaw, cone, k) in enumerate(shafts):
        cone *= cmul
        sp = L.spawn_class(unreal.SpotLight, v(*p), rot(pitch=pitch, yaw=yaw), folder="CK/Lighting/Shafts", label="CK_Shaft_%02d" % i)
        spc = sp.get_component_by_class(unreal.SpotLightComponent)
        set_props(spc, intensity_units=unreal.LightUnits.CANDELAS, intensity=base * k, outer_cone_angle=cone, inner_cone_angle=cone * 0.85,
                  attenuation_radius=22000.0, light_color=unreal.Color(r=255, g=250, b=240, a=255), volumetric_scattering_intensity=vol,
                  cast_shadows=(i == 0), diffuse_scale=float(ARGS.get("shaftdiff", "0.35")), specular_scale=0.5)
    # Crystal bounce: cyan/violet fills near the big masses, warm window glow near the city
    fills = [((22, -30, 30), (1.0, 0.78, 0.45), 20000, 5500), ((60, 55, 30), (0.45, 0.85, 1.0), 16000, 5000),
             ((120, -95, 40), (1.0, 0.75, 0.45), 16000, 6000), ((240, 115, 40), (1.0, 0.8, 0.5), 16000, 6000),
             ((300, -100, 40), (0.6, 0.55, 1.0), 16000, 6000), ((150, 0, 90), (0.5, 0.9, 1.0), 12000, 12000),
             ((410, 0, 60), (1.0, 0.82, 0.55), 16000, 9000), ((35, 20, 20), (1.0, 0.75, 0.4), 14000, 4500),
             ((90, -60, 25), (1.0, 0.8, 0.5), 14000, 5000)]   # plan step 8: gold bounce like the reference
    for i, (p, c, inten, radius) in enumerate(fills):
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/CrystalFill", label="CK_CrystalFill_%02d" % i)
        pc = pl.get_component_by_class(unreal.PointLightComponent)
        set_props(pc, intensity=float(inten), attenuation_radius=float(radius), light_color=unreal.Color(r=int(c[0] * 255), g=int(c[1] * 255), b=int(c[2] * 255), a=255),
                  cast_shadows=False, volumetric_scattering_intensity=0.0, intensity_units=unreal.LightUnits.UNITLESS)
    for i, p in enumerate([(60, -20, 125), (130, 30, 130), (200, -40, 135), (250, 50, 130), (110, -70, 120), (300, 0, 140)]):
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/CeilingFill", label="CK_CeilingFill_%02d" % i)
        set_props(pl.get_component_by_class(unreal.PointLightComponent), intensity=float(ARGS.get("ceil","220000")), attenuation_radius=12000.0, cast_shadows=False,
                  light_color=unreal.Color(r=250, g=242, b=232, a=255), intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=0.0)
    # Reference ceiling reads as lit grey-brown rock: wide warm-grey spots aimed straight up, no fog cones
    k = 0
    for gx in (40, 120, 200, 280, 360):
        for gy in (-90, 0, 90):
            sp = L.spawn_class(unreal.SpotLight, v(gx, gy, 60), rot(pitch=90), folder="CK/Lighting/CeilingFill", label="CK_CeilingUp_%02d" % k)
            set_props(sp.get_component_by_class(unreal.SpotLightComponent), intensity_units=unreal.LightUnits.CANDELAS,
                      intensity=float(ARGS.get("ceilup", "6500")), outer_cone_angle=70.0, inner_cone_angle=40.0, attenuation_radius=20000.0,
                      light_color=unreal.Color(r=255, g=236, b=214, a=255), cast_shadows=False, volumetric_scattering_intensity=0.0)
            k += 1
    for i, p in enumerate([(30, 5, 1.5), (60, -10, 1.5), (55, 25, 1.5), (100, 5, 1.5)]):  # light the shallows from just above the water
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/Shallows", label="CK_Shallows_%02d" % i)
        set_props(pl.get_component_by_class(unreal.PointLightComponent), intensity=float(ARGS.get("shallow","20000")), attenuation_radius=6000.0, cast_shadows=False,
                  light_color=unreal.Color(r=170, g=230, b=240, a=255), intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=0.0)
    warm = [(172, -20, 8), (172, 5, 8), (172, 30, 8), (172, 52, 8), (12, -14, 4), (20, -22, 7), (28, -30, 9), (44, -28, 12), (60, -20, 16), (38, -33, 9), (50, -27, 9), (60, -21, 9), (40, -32, 17), (55, -24, 17), (180, -50, 16), (190, 0, 16), (190, 88, 22), (84, 60, 10), (378, -4, 42), (330, -70, 32), (352, 78, 30)]
    for i, p in enumerate(warm):
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/Windows", label="CK_WindowWarm_%02d" % i)
        pc = pl.get_component_by_class(unreal.PointLightComponent)
        set_props(pc, intensity=8000.0, attenuation_radius=2200.0, light_color=unreal.Color(r=255, g=170, b=90, a=255), cast_shadows=False,
                  intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=0.0)   # local lights in volumetric fog cost ~1 ms each on iGPU
    # Building fills: soft cool-white light in front of every building so facades read like the reference
    for i, (mesh, bx, by, bz, yaw, sc) in enumerate(ARCH):
        d = math.hypot(bx, by) or 1.0
        px, py = bx - bx / d * 14.0, by - by / d * 14.0  # pulled toward the camera
        pl = L.spawn_class(unreal.PointLight, v(px, py, bz + 14), folder="CK/Lighting/BuildingFill", label="CK_BldgFill_%02d" % i)
        set_props(pl.get_component_by_class(unreal.PointLightComponent), intensity=float(ARGS.get("bfill", "22000")) * (1.0 + d / 300.0),
                  attenuation_radius=5000.0, cast_shadows=False, light_color=unreal.Color(r=255, g=225, b=190, a=255),
                  intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=0.0)
    # Post process (unbound)
    pp = L.spawn_class(unreal.PostProcessVolume, v(190, 0, 50), folder="CK/Lighting", label="CK_PostProcess")
    pp.set_editor_property("unbound", True)
    s = pp.settings
    over = dict(auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL, auto_exposure_bias=float(ARGS.get("ev", "2.2")),
                auto_exposure_apply_physical_camera_exposure=False, bloom_intensity=0.45, bloom_threshold=-1.0,
                vignette_intensity=0.35, color_saturation=unreal.Vector4(1.1, 1.1, 1.1, 1.0),
                color_gain_shadows=unreal.Vector4(0.92, 1.0, 1.06, 1.0), color_gain_highlights=unreal.Vector4(1.08, 1.0, 0.88, 1.0),
                color_contrast=unreal.Vector4(1.18, 1.18, 1.18, 1.0), lumen_scene_view_distance=60000.0, lumen_max_trace_distance=40000.0,
                lumen_scene_detail=LQ["detail"], lumen_scene_lighting_quality=LQ["lighting"], lumen_final_gather_quality=LQ["gather"],
                lumen_reflection_quality=1.0,
                lumen_surface_cache_resolution=1.0, film_toe=0.5, scene_fringe_intensity=0.4)
    for k, val in over.items():
        try:
            s.set_editor_property(k, val)
            s.set_editor_property("override_" + k, True)
        except Exception as e:  # noqa: BLE001
            print("  pp skip", k, str(e)[:80])
    pp.set_editor_property("settings", s)
    print("lighting ok")


# --------------------------------------------------------------------------- cameras / game mode
CAMERAS = [  # label, loc(m), pitch, yaw, focal(mm)
    ("CAM_Reference", (-8, 5, 8.5), -1.5, -1.0, 18.0),   # back/right: loggia reads smaller like the reference
    ("CAM_CaveOverview", (-25, 5, 95), -17.0, 2.0, 15.0),
    ("CAM_GiantCrystals", (60, -10, 25), 28.0, -40.0, 20.0),
    ("CAM_Architecture", (78, 2, 9), 5.0, -128.0, 24.0),
    ("CAM_Lake", (120, 30, 3), -4.0, 20.0, 18.0),
    ("CAM_DetailCloseup", (30, -18, 9), -6.0, -60.0, 35.0),
]


def build_cameras():
    for label, p, pitch, yaw, focal in CAMERAS:
        cam = L.spawn_class(unreal.CineCameraActor, v(*p), rot(pitch=pitch, yaw=yaw), folder="CK/Cameras", label=label)
        cc = cam.get_cine_camera_component()
        fb = cc.get_editor_property("filmback")
        fb.set_editor_property("sensor_width", 36.0)
        fb.set_editor_property("sensor_height", 20.25)
        cc.set_editor_property("filmback", fb)
        cc.set_editor_property("current_focal_length", focal)
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        cc.set_editor_property("focus_settings", fs)
    L.spawn_class(unreal.PlayerStart, v(0, 0, 7.5), rot(yaw=0), folder="CK/Cameras", label="CK_PlayerStart")
    print("cameras ok")


def build_game_mode():
    path = "/Game/CrystalKingdom/Blueprints"
    at = unreal.AssetToolsHelpers.get_asset_tools()
    pawn_path = path + "/BP_CK_FlyPawn"
    if not unreal.EditorAssetLibrary.does_asset_exist(pawn_path):
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.SpectatorPawn)
        at.create_asset("BP_CK_FlyPawn", path, unreal.Blueprint, f)
    pawn = unreal.load_asset(pawn_path)
    unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
    gm_path = path + "/BP_CK_FlyGameMode"
    if not unreal.EditorAssetLibrary.does_asset_exist(gm_path):
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.GameModeBase)
        at.create_asset("BP_CK_FlyGameMode", path, unreal.Blueprint, f)
    gm = unreal.load_asset(gm_path)
    cdo = unreal.get_default_object(gm.generated_class())
    cdo.set_editor_property("default_pawn_class", pawn.generated_class())
    unreal.BlueprintEditorLibrary.compile_blueprint(gm)
    unreal.EditorAssetLibrary.save_loaded_asset(pawn)
    unreal.EditorAssetLibrary.save_loaded_asset(gm)
    ws = L.world().get_world_settings()
    ws.set_editor_property("default_game_mode", gm.generated_class())
    print("game mode ok")


def build_lot_houses(rng, keep_existing=False):
    """Plan step 5: put a house on every free lot from the map (Saved/lots.json, Tools/make_map.py), door to the road."""
    import json
    path = os.path.join(unreal.Paths.project_saved_dir(), "lots.json")
    if not os.path.exists(path):
        print("no lots.json - run Tools/make_map.py with a road plan first")
        return
    lots = json.load(open(path, encoding="utf-8"))
    n = 0
    for lot in lots:
        x, y = lot["x"], lot["y"]
        if x < 25 and abs(y - 5) < 40:      # P9/P10 sit in the reference camera's foreground: keep them empty
            continue
        if keep_existing:
            busy = False
            for a in L.EAS.get_all_level_actors():
                f = str(a.get_folder_path())
                if f.startswith("CK/Architecture") and not f.startswith("CK/Architecture/TerraceWalls") and isinstance(a, unreal.StaticMeshActor):
                    o, e = a.get_actor_bounds(False)
                    if o.x / M - e.x / M - 4 < x < o.x / M + e.x / M + 4 and o.y / M - e.y / M - 4 < y < o.y / M + e.y / M + 4:
                        busy = True
                        break
            if busy:
                continue
        gz = L.ground_z(x, y)
        if gz is None:
            continue
        rx, ry = lot["road"]
        mesh = pick_house(rng, big=False)
        sm = unreal.load_asset("/Game/CrystalKingdom/Meshes/Architecture/SM_Bldg_" + mesh)
        b = sm.get_bounding_box()
        yaw = face_yaw(x, y, rx - x, ry - y)                       # facade (+Y) toward the road
        # centre the footprint on the lot (pivot is the front-left corner of the mesh)
        cxl, cyl = (b.min.x + b.max.x) / 2 / M, (b.min.y + b.max.y) / 2 / M
        a_ = math.radians(yaw)
        ox = cxl * math.cos(a_) - cyl * math.sin(a_)
        oy = cxl * math.sin(a_) + cyl * math.cos(a_)
        L.spawn_mesh("Architecture/SM_Bldg_" + mesh, v(x - ox, y - oy, gz - 0.3), rot(yaw=yaw), 1.0, folder="CK/Architecture/Lots",
                     label="Lot_SM_Bldg_%s_%02d" % (mesh, n))
        n += 1
    print("lot houses", n)


CRYSTAL_FOLDERS = ("CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Crystals/Walls", "CK/Crystals/Landmarks",
                   "CK/Rocks/Shore", "CK/Rocks/Submerged")


def clear_crystals(hit_fn, shrink=0.8):
    """Destroy ground crystals / rocks whose XY footprint (actor bounds, shrunk a little because rotated
    prisms over-fill their AABB) satisfies hit_fn(x0, x1, y0, y1) in metres. Hanging crystals are kept."""
    n = 0
    for a in L.EAS.get_all_level_actors():
        f = str(a.get_folder_path())
        if not f.startswith(CRYSTAL_FOLDERS):
            continue
        o, e = a.get_actor_bounds(False)
        if (o.z - e.z) / M > 35:          # chandeliers hanging from the ceiling never touch a street
            continue
        ex, ey = e.x / M * shrink, e.y / M * shrink
        if hit_fn(o.x / M - ex, o.x / M + ex, o.y / M - ey, o.y / M + ey):
            L.EAS.destroy_actor(a)
            n += 1
    return n


def _road_hash(plan, cell=10.0):
    grid = {}
    for r in plan["roads"]:
        for x, y in r["pts"]:
            grid.setdefault((int(x // cell), int(y // cell)), []).append((x, y, r["width"]))
    return grid


def _road_hits(grid, x0, x1, y0, y1, margin=1.0, cell=10.0):
    for gx in range(int((x0 - 6) // cell), int((x1 + 6) // cell) + 1):
        for gy in range(int((y0 - 6) // cell), int((y1 + 6) // cell) + 1):
            for x, y, w in grid.get((gx, gy), ()):
                r = w / 2 + margin
                if x0 - r <= x <= x1 + r and y0 - r <= y <= y1 + r:
                    return True
    return False


def build_streets(rng):
    """Buildings first, like the reference: houses line both sides of every road (~16 m apart), doors to the
    street with a short walk; crystals on the plot are cleared. Only flat dry ground, never over the camera's foreground."""
    import json
    plan = json.load(open(os.path.join(unreal.Paths.project_saved_dir(), "road_plan.json"), encoding="utf-8"))
    L.reset_terrain_cache()
    grid = _road_hash(plan)
    boxes = []
    for a in L.EAS.get_all_level_actors():
        f = str(a.get_folder_path())
        if f.startswith("CK/Architecture") and not f.startswith("CK/Architecture/TerraceWalls") and isinstance(a, unreal.StaticMeshActor):
            o, e = a.get_actor_bounds(False)
            boxes.append((o.x / M - e.x / M, o.x / M + e.x / M, o.y / M - e.y / M, o.y / M + e.y / M))
    spacing = float(ARGS.get("street_gap", "13"))
    n = cleared = spires = 0
    from collections import Counter
    why = Counter()
    for r in plan["roads"]:
        pts, w = r["pts"], r["width"]
        acc = spacing * 0.5
        for k in range(1, len(pts)):
            (x0, y0), (x1, y1) = pts[k - 1], pts[k]
            seg = math.hypot(x1 - x0, y1 - y0)
            acc += seg
            if acc < spacing or seg < 0.1:
                continue
            acc = 0.0
            ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
            for side, row in ((-1, 0), (1, 0), (-1, 1), (1, 1)):   # two rows deep on both sides -> city blocks
              first = pick_house(rng)
              while first in ("TowerRound", "TowerSquare") and spires >= int(ARGS.get("max_spires", "2")):
                  first = pick_house(rng)
              for mesh in (first, "Town_01"):   # big plot pick, else a narrow town house
                  sm = unreal.load_asset("/Game/CrystalKingdom/Meshes/Architecture/SM_Bldg_" + mesh)
                  b = sm.get_bounding_box()
                  hd = (b.max.y - b.min.y) / 2 / M          # half depth (facade -> back)
                  hw = (b.max.x - b.min.x) / 2 / M
                  rad = max(hd, hw) + 1.0
                  off = w / 2 + 1.5 + rad + row * (2 * rad + 4.0)   # row 1 sits behind row 0 with a 4 m lane
                  cx, cy = x1 - uy * side * off, y1 + ux * side * off
                  if cx < 50 and -45 < cy < 55:
                      why["camera"] += 1
                      continue
                  # centre + back must stand on land; the street-side edge may dip toward the water (a stone plinth fills it)
                  bkx, bky = cx - (x1 - cx) / off * rad, cy - (y1 - cy) / off * rad
                  core = [L.ground_z(cx, cy), L.ground_z(bkx, bky)]
                  if any(g is None or g < -0.05 for g in core):
                      why["water/void"] += 1
                      continue
                  gzs = core + [L.ground_z(cx + dx, cy + dy) for dx, dy in ((rad, 0), (-rad, 0), (0, rad), (0, -rad))]
                  gzs = [g if g is not None else -0.5 for g in gzs]
                  if max(gzs) - min(gzs) > float(ARGS.get("street_slope", "7.0")):
                      why["slope"] += 1
                      continue
                  bx = (cx - rad, cx + rad, cy - rad, cy + rad)
                  if any(not (bx[1] + 2 < o[0] or o[1] < bx[0] - 2 or bx[3] + 2 < o[2] or o[3] < bx[2] - 2) for o in boxes):
                      why["building"] += 1
                      continue
                  if _road_hits(grid, bx[0] + 0.5, bx[1] - 0.5, bx[2] + 0.5, bx[3] - 0.5, margin=0.5):
                      why["road"] += 1
                      continue
                  gz = max(gzs) if max(gzs) - min(gzs) > 0.6 else max(min(gzs), 0.1)   # sloped plot: floor at the high side
                  low = max(min(gzs), -0.6)
                  if gz - low > 0.6:   # dressed-stone plinth terraced into the slope
                      L.spawn_mesh("/Engine/BasicShapes/Cube", v(cx, cy, (gz + low) / 2 - 0.4), rot(yaw=face_yaw(cx, cy, x1 - cx, y1 - cy)),
                                   (rad * 2.0 + 1.0, rad * 2.0 + 1.0, gz - low + 0.8), folder="CK/Architecture/Streets", material=MI + "MI_StoneTrim")
                  yaw = face_yaw(cx, cy, x1 - cx, y1 - cy)        # facade (+Y) toward the street
                  a_ = math.radians(yaw)
                  cxl, cyl = (b.min.x + b.max.x) / 2 / M, (b.min.y + b.max.y) / 2 / M
                  ox = cxl * math.cos(a_) - cyl * math.sin(a_)
                  oy = cxl * math.sin(a_) + cyl * math.cos(a_)
                  cleared += clear_crystals(lambda a0, a1, b0, b1: not (a1 < bx[0] - 1 or bx[1] + 1 < a0 or b1 < bx[2] - 1 or bx[3] + 1 < b0))
                  L.spawn_mesh("Architecture/SM_Bldg_" + mesh, v(cx - ox, cy - oy, gz - 0.3), rot(yaw=yaw), 1.0, folder="CK/Architecture/Streets",
                               label="Street_SM_Bldg_%s_%03d" % (mesh, n))
                  boxes.append(bx)
                  # front walk: door (facade middle) to the carriageway edge
                  dx_, dy_ = x1 - cx, y1 - cy
                  dl = math.hypot(dx_, dy_) or 1
                  sx_, sy_ = cx + dx_ / dl * hd, cy + dy_ / dl * hd
                  ex_, ey_ = x1 - dx_ / dl * (w / 2 - 0.5), y1 - dy_ / dl * (w / 2 - 0.5)
                  wl = math.hypot(ex_ - sx_, ey_ - sy_)
                  if wl > 0.3 and row == 0:
                      rz = L.ground_z(ex_, ey_)
                      rz = 0.15 if rz is None else max(rz, 0.15)
                      L.spawn_mesh("/Engine/BasicShapes/Cube", v((sx_ + ex_) / 2, (sy_ + ey_) / 2, (gz + rz) / 2 + 0.08),
                                   rot(pitch=math.degrees(math.atan2(rz - gz, wl)), yaw=math.degrees(math.atan2(ey_ - sy_, ex_ - sx_))),
                                   (math.hypot(wl, rz - gz) + 0.4, 2.2, 0.3), folder="CK/Roads/Walk", material=MI + "MI_StoneTrim", shadows=False)
                  n += 1
                  spires += mesh in ("TowerRound", "TowerSquare")
                  break
    print("street houses", n, "crystals cleared for plots", cleared, "| rejected:", dict(why))


def build_landscape(rng):
    """Street landscaping along the road network: long stone planters, wrought-iron lamps, benches and
    round planters at road ends. Never on water, on another road, against a building or over a doorway."""
    import json
    plan = json.load(open(os.path.join(unreal.Paths.project_saved_dir(), "road_plan.json"), encoding="utf-8"))
    L.reset_terrain_cache()
    grid = _road_hash(plan)
    boxes = []
    for a in L.EAS.get_all_level_actors():
        f = str(a.get_folder_path())
        if f.startswith("CK/Architecture") and not f.startswith("CK/Architecture/TerraceWalls") and isinstance(a, unreal.StaticMeshActor):
            o, e = a.get_actor_bounds(False)
            boxes.append((o.x / M - e.x / M, o.x / M + e.x / M, o.y / M - e.y / M, o.y / M + e.y / M))
    doors = [r["pts"][0] for r in plan["roads"] if r["kind"] == "spur"] + \
            [p for r in plan["roads"] if r["kind"] == "lane" for p in (r["pts"][0], r["pts"][-1])]
    placed = []

    def free(x, y, rad):
        if x < 48 and -48 < y < 58:
            return False
        g = L.ground_z(x, y)
        if g is None or g < -0.05:
            return False
        if any(b0 - rad < x < b1 + rad and c0 - rad < y < c1 + rad for b0, b1, c0, c1 in boxes):
            return False
        if _road_hits(grid, x - rad * 0.4, x + rad * 0.4, y - rad * 0.4, y + rad * 0.4, margin=0.0):
            return False
        if any(math.hypot(x - dx, y - dy) < 5.0 for dx, dy in doors):
            return False
        if any(math.hypot(x - px_, y - py_) < 3.0 for px_, py_ in placed):
            return False
        return True

    counts = {"planter": 0, "lamp": 0, "bench": 0, "round": 0}
    for r in plan["roads"]:
        pts, w = r["pts"], r["width"]
        length = 0.0
        nxt = {"planter": 9.0, "lamp": 4.0, "bench": 30.0}
        gap = {"planter": 24.0, "lamp": 19.0, "bench": 70.0 if r["kind"] == "ring" else 1e9}
        side_flip = 1
        for k in range(1, len(pts)):
            (x0, y0), (x1, y1) = pts[k - 1], pts[k]
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg < 0.05:
                continue
            length += seg
            ux, uy = (x1 - x0) / seg, (y1 - y0) / seg
            for kind in ("planter", "lamp", "bench"):
                if length < nxt[kind]:
                    continue
                nxt[kind] = length + gap[kind]
                side_flip = -side_flip
                for side in (side_flip, -side_flip):
                    nx_, ny_ = -uy * side, ux * side          # unit normal toward this side
                    if kind == "planter":
                        off = w / 2 + 1.0
                        cx, cy = x1 + nx_ * off, y1 + ny_ * off
                        if not all(free(cx + ux * t, cy + uy * t, 0.9) for t in (-2.6, 0.0, 2.6)):
                            continue
                        g = L.ground_z(cx, cy)
                        L.spawn_mesh("Props/SM_Prop_PlanterLong_%02d" % rng.randint(1, 3), v(cx, cy, g - 0.05),
                                     rot(yaw=math.degrees(math.atan2(uy, ux))), 1.0, folder="CK/Landscape/Planters")
                    elif kind == "lamp":
                        off = w / 2 + 0.6
                        cx, cy = x1 + nx_ * off, y1 + ny_ * off
                        if not free(cx, cy, 0.6):
                            continue
                        g = L.ground_z(cx, cy)
                        L.spawn_mesh("Props/SM_Prop_StreetLamp_01", v(cx, cy, g - 0.05),
                                     rot(yaw=math.degrees(math.atan2(-ny_, -nx_))), 1.0, folder="CK/Landscape/Lamps")   # arm over the road
                    else:
                        off = w / 2 + 1.1
                        cx, cy = x1 + nx_ * off, y1 + ny_ * off
                        if not free(cx, cy, 1.4):
                            continue
                        g = L.ground_z(cx, cy)
                        L.spawn_mesh("Props/SM_Prop_Bench_01", v(cx, cy, g - 0.02),
                                     rot(yaw=math.degrees(math.atan2(-nx_, ny_))), 1.0, folder="CK/Landscape/Benches")   # seat faces the road
                    placed.append((cx, cy))
                    counts[kind] += 1
                    break
        # round planter beside each lane / spur end
        if r["kind"] in ("lane", "spur") and len(pts) > 3:
            (ex, ey), (px_, py_) = pts[-1], pts[-3]
            dx, dy = ex - px_, ey - py_
            dl = math.hypot(dx, dy) or 1
            cx, cy = ex - dy / dl * (w / 2 + 1.6), ey + dx / dl * (w / 2 + 1.6)
            if free(cx, cy, 1.2):
                g = L.ground_z(cx, cy)
                L.spawn_mesh("Props/SM_Prop_PlanterRound_%02d" % rng.randint(1, 2), v(cx, cy, g - 0.05), rot(yaw=rng.uniform(0, 360)), 1.0,
                             folder="CK/Landscape/Planters")
                placed.append((cx, cy))
                counts["round"] += 1
    print("landscape", counts)


def build_roads():
    """Spawn the planned road network (Tools/plan_roads.py -> Saved/road_plan.json) as paved slabs that follow
    the terrain; water crossings become low causeways. Scatter crystals / rocks on the carriageway are removed."""
    import json
    plan = json.load(open(os.path.join(unreal.Paths.project_saved_dir(), "road_plan.json"), encoding="utf-8"))
    L.reset_terrain_cache()
    pave = MI + "MI_StoneTrim"   # pale dressed stone (MI_Stone stretched on a cube read as a dark slab)
    n = emb = 0
    road_pts = []
    max_grade = math.tan(math.radians(float(ARGS.get("max_grade", "16"))))

    def in_fg(x, y):
        return x < 45 and -45 < y < 55          # reference camera foreground: open water, no quay road

    def pad(ex, ey, w, kind, fg_ok=False):
        gz = L.ground_z(ex, ey)
        if gz is None or gz < -0.3 or (in_fg(ex, ey) and not fg_ok):
            return 0
        zoff = {"ring": 0.06, "spur": 0.09, "lane": 0.12}.get(kind, 0.06)
        L.spawn_mesh("/Engine/BasicShapes/Cylinder", v(ex, ey, max(gz, 0.15) + zoff + 0.01), rot(), (w * 1.25, w * 1.25, 0.35),
                     folder="CK/Roads/Pads", material=pave, shadows=False)
        return 1

    for r in plan["roads"]:
        w = r["width"]
        pts = r["pts"]
        kind = r["kind"]
        gzs = [L.ground_z(x, y) for x, y in pts]
        wet = [g is None or g < -0.3 for g in gzs]
        zs = [(0.15 if in_fg(x, y) else 1.4) if wet[k] else max(gzs[k], 0.15) for k, (x, y) in enumerate(pts)]
        for _ in range(3):   # wide smoothing: no saw-tooth ramps where the probe flickers between ledge and water
            zs = [(zs[max(k - 2, 0)] + zs[max(k - 1, 0)] + 2 * zs[k] + zs[min(k + 1, len(zs) - 1)] + zs[min(k + 2, len(zs) - 1)]) / 6
                  for k in range(len(zs))]
        # grade limit: never a gap at a terrace edge - the low side is raised onto a dressed-stone embankment instead
        seglen = [math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1)]
        for _ in range(2):
            for k in range(1, len(zs)):
                zs[k] = max(zs[k], zs[k - 1] - max_grade * seglen[k - 1])
            for k in range(len(zs) - 2, -1, -1):
                zs[k] = max(zs[k], zs[k + 1] - max_grade * seglen[k])
        nseg = len(pts) - 1
        skip = [False] * nseg
        if kind == "ring":
            for k in range(nseg):
                skip[k] = in_fg((pts[k][0] + pts[k + 1][0]) / 2, (pts[k][1] + pts[k + 1][1]) / 2)
            # never end over water: grow the open stretch through adjacent causeway segments to the shore
            changed = True
            while changed:
                changed = False
                for k in range(nseg):
                    if not skip[k] and (wet[k] or wet[k + 1]) and (skip[k - 1] or skip[(k + 1) % nseg]):
                        skip[k] = changed = True
        # causeway runs: contiguous wet segments, short dry gaps (<= 2) bridged, only runs >= 4 segments get railings
        seg_wet = [wet[k] and wet[k + 1] for k in range(nseg)]
        for k in range(nseg):
            if not seg_wet[k]:
                lo = next((j for j in range(k - 1, max(k - 3, -1), -1) if seg_wet[j]), None)
                hi = next((j for j in range(k + 1, min(k + 3, nseg)) if seg_wet[j]), None)
                if lo is not None and hi is not None:
                    seg_wet[k] = True
        rail = [False] * nseg
        k = 0
        while k < nseg:
            if seg_wet[k] and not skip[k]:
                j = k
                while j < nseg and seg_wet[j] and not skip[j]:
                    j += 1
                if j - k >= 4:
                    for q in range(k, j):
                        rail[q] = True
                k = j
            else:
                k += 1
        zoff = {"ring": 0.06, "spur": 0.09, "lane": 0.12}.get(kind, 0.06)   # stacked, never coplanar
        for k in range(nseg):
            if skip[k]:
                continue
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            z0, z1 = zs[k], zs[k + 1]
            L2 = seglen[k]
            if L2 < 0.2:
                continue
            yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
            pitch = math.degrees(math.atan2(z1 - z0, L2))
            mx_, my_, mz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
            L.spawn_mesh("/Engine/BasicShapes/Cube", v(mx_, my_, mz + zoff), rot(pitch=pitch, yaw=yaw),
                         ((L2 + 0.35) / 1.0, w, 0.35), folder="CK/Roads/" + kind.capitalize(), material=pave, shadows=False)
            n += 1
            gmid = L.ground_z(mx_, my_)
            gl = [g for g in (gzs[k], gmid, gzs[k + 1]) if g is not None]
            glow = sorted(gl)[len(gl) // 2] if gl else None             # median: one sample over a cliff edge must not drag a tower down it
            if glow is not None and glow > -0.3 and mz - glow > 0.3:     # raised over land: low embankment, never a floating slab
                hb = min(mz - glow + 0.5, 3.0)
                L.spawn_mesh("/Engine/BasicShapes/Cube", v(mx_, my_, mz + 0.25 - hb / 2), rot(yaw=yaw),
                             (L2 + 0.4, w + 0.4, hb), folder="CK/Roads/Embankment", material=pave, shadows=False)
                emb += 1
            elif (glow is None or glow <= -0.3) and not rail[k] and k % 2 == 0:   # short wet stretch: piers under the deck
                gb = glow if glow is not None else -3.0
                for sd in (-1, 1):
                    L.spawn_mesh("/Engine/BasicShapes/Cylinder", v(mx_ - math.sin(math.radians(yaw)) * sd * (w / 2 - 0.6),
                                                                  my_ + math.cos(math.radians(yaw)) * sd * (w / 2 - 0.6), (gb + mz) / 2),
                                 rot(), (1.0, 1.0, max(0.5, mz - gb)), folder="CK/Roads/Causeway", material=pave, shadows=False)
            if rail[k]:
                ux, uy = (x1 - x0) / L2, (y1 - y0) / L2
                nx_, ny_ = -uy, ux
                gbed = gmid if gmid is not None else -2.0
                if k % 3 == 0:
                    for sd in (-1, 1):
                        L.spawn_mesh("/Engine/BasicShapes/Cylinder", v(x0 + nx_ * sd * (w / 2 - 0.5), y0 + ny_ * sd * (w / 2 - 0.5), (gbed + z0) / 2),
                                     rot(), (1.0, 1.0, max(0.5, (z0 - gbed) / 1.0)), folder="CK/Roads/Causeway", material=pave, shadows=False)
                for sd in (-1, 1):
                    L.spawn_mesh("Architecture/SM_Arch_Balustrade", v(x0 + nx_ * sd * (w / 2), y0 + ny_ * sd * (w / 2), z0 + 0.2),
                                 rot(pitch=pitch, yaw=yaw), ((L2 + 0.05) / 4.0, 1.0, 1.0), folder="CK/Roads/Causeway", collision=False)
        road_pts += [(x, y, w) for x, y in pts]
        # rounded paving pads where a road ends (or the ring opens for the camera): no ragged slab corners
        if kind != "ring":
            n += pad(pts[0][0], pts[0][1], w, kind) + pad(pts[-1][0], pts[-1][1], w, kind)
        else:
            for k in range(nseg):
                if skip[k] != skip[(k + 1) % nseg]:
                    q = pts[k + 1]
                    n += pad(q[0], q[1], w, kind, fg_ok=True)
    print("embankments", emb)
    removed = clear_crystals(lambda x0, x1, y0, y1: _road_hits(_road_hash(plan), x0, x1, y0, y1, margin=0.5))
    bboxes = []
    for a in L.EAS.get_all_level_actors():
        f = str(a.get_folder_path())
        # only houses: AABBs of rotated landmarks (bridge 77 m, plaza, loggia) swallowed whole crystal cliffs
        if f.startswith(("CK/Architecture/Streets", "CK/Architecture/Lots", "CK/Architecture/Fill")) and isinstance(a, unreal.StaticMeshActor)                 and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name() != "Cube":
            o, e = a.get_actor_bounds(False)
            bboxes.append((o.x / M - e.x / M, o.x / M + e.x / M, o.y / M - e.y / M, o.y / M + e.y / M))
    removed += clear_crystals(lambda x0, x1, y0, y1: any(not (x1 < b0 or b1 < x0 or y1 < c0 or c1 < y0) for b0, b1, c0, c1 in bboxes), shrink=0.6)
    print("roads: slabs", n, "crystals cleared off the carriageway (footprint test)", removed)
    return
    # (old centre-distance test kept below for reference, no longer reached)
    grid = {}
    for x, y, w in road_pts:
        grid.setdefault((int(x // 10), int(y // 10)), []).append((x, y, w))
    removed = 0
    for a in L.EAS.get_all_level_actors():
        f = str(a.get_folder_path())
        if not (f.startswith("CK/Crystals/Floor") or f.startswith("CK/Crystals/Dense") or f.startswith("CK/Crystals/Walls")
                or f.startswith("CK/Rocks/Shore")):
            continue
        p = a.get_actor_location() / M
        big = "HexCliff" in a.get_actor_label()
        hit = False
        for gx in (-1, 0, 1):
            for gy in (-1, 0, 1):
                for x, y, w in grid.get((int(p.x // 10) + gx, int(p.y // 10) + gy), ()):
                    if math.hypot(p.x - x, p.y - y) < (5.0 if big else w / 2 + 1.5):
                        hit = True
                        break
                if hit:
                    break
            if hit:
                break
        if hit:
            L.EAS.destroy_actor(a)
            removed += 1
    print("roads: slabs", n, "scatter removed", removed)


MERGE_FOLDERS = ["CK/Architecture/TerraceWalls", "CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Crystals/Walls", "CK/Crystals/Ceiling",
                 "CK/Rocks/Shore", "CK/Rocks/Ceiling", "CK/Architecture/Fill", "CK/Architecture/Far"]
MERGED = "/Game/CrystalKingdom/Meshes/Merged"


def optimize_level():
    """Plan step 8: collapse ~2,300 scatter StaticMeshActors into per-folder 60 m grid chunks (Nanite kept).
    Chunks stay small so each merged mesh keeps a usable Lumen distance field / mesh cards."""
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    cell = float(ARGS.get("cell", "60")) * M
    before = len(L.EAS.get_all_level_actors())
    made = 0
    for folder in MERGE_FOLDERS:
        groups = {}
        for a in L.EAS.get_all_level_actors():
            if str(a.get_folder_path()) != folder or not isinstance(a, unreal.StaticMeshActor):
                continue
            p = a.get_actor_location()
            groups.setdefault((int(p.x // cell), int(p.y // cell)), []).append(a)
        tag = folder.replace("CK/", "").replace("/", "_")
        for (gx, gy), acts in groups.items():
            if len(acts) < 2:
                continue
            name = "SM_Merged_%s_%d_%d" % (tag, gx, gy)
            if unreal.EditorAssetLibrary.does_asset_exist(MERGED + "/" + name):
                unreal.EditorAssetLibrary.delete_asset(MERGED + "/" + name)
            ms = unreal.MeshMergingSettings()
            ms.set_editor_property("merge_materials", False)
            ms.set_editor_property("merge_physics_data", True)
            ms.set_editor_property("generate_light_map_uv", False)
            ns = ms.get_editor_property("nanite_settings")
            ns.enabled = True
            ms.set_editor_property("nanite_settings", ns)
            opt = unreal.MergeStaticMeshActorsOptions()
            opt.set_editor_property("destroy_source_actors", True)
            opt.set_editor_property("spawn_merged_actor", True)
            opt.set_editor_property("base_package_name", MERGED + "/" + name)
            opt.set_editor_property("new_actor_label", name)
            opt.set_editor_property("mesh_merging_settings", ms)
            merged = sub.merge_static_mesh_actors(acts, opt)
            if merged:
                merged.set_folder_path(folder)
                made += 1
    print("optimize: merged chunks", made, "actors", before, "->", len(L.EAS.get_all_level_actors()))


def main():
    open_level()
    rng = random.Random(4242)
    if STAGE in ("all", "world"):
        print("cleared", L.clear_ck("CK"))
        build_cave()
        build_water()
        build_terraces()
        build_architecture()
    if STAGE in ("all", "crystals"):
        for f in ("CK/Crystals", "CK/Rocks/Ceiling", "CK/Rocks/Submerged", "CK/Rocks/Shore"):
            if STAGE == "crystals":
                L.clear_ck(f)
        build_crystal_landmarks()
        build_foreground(rng)
        build_ceiling_crystals(rng)
        build_wall_crystals(rng)
        build_floor_scatter(rng)
        build_shore_rocks(rng)
        build_dense_masses(random.Random(777))
    if STAGE in ("all", "world", "farcity"):
        L.clear_ck("CK/Architecture/Far")
        build_far_city()
    if STAGE in ("all", "world", "fill"):
        L.clear_ck("CK/Architecture/Fill")
        build_city_fill(random.Random(int(ARGS.get("fillseed", "61"))))
    if STAGE in ("all", "world", "walls"):
        L.clear_ck("CK/Architecture/TerraceWalls")
        build_terrace_walls()
    if STAGE == "dense":
        L.clear_ck("CK/Crystals/Dense")
        build_dense_masses(random.Random(int(ARGS.get("seed", "777"))))
    if STAGE in ("all", "lighting"):
        if STAGE == "lighting":
            L.clear_ck("CK/Lighting")
        build_lighting()
    if STAGE in ("all", "cameras"):
        if STAGE == "cameras":
            L.clear_ck("CK/Cameras")
        build_cameras()
        build_game_mode()
    if STAGE == "lots":
        L.clear_ck("CK/Architecture/Lots")
        build_lot_houses(random.Random(int(ARGS.get("lotseed", "88"))))
    if STAGE == "streets":
        L.clear_ck("CK/Architecture/Streets")
        L.clear_ck("CK/Roads/Walk")
        build_streets(random.Random(int(ARGS.get("streetseed", "21"))))
    if STAGE == "lotsadd":
        build_lot_houses(random.Random(int(ARGS.get("lotseed", "89"))), keep_existing=True)
    if STAGE == "landscape":
        L.clear_ck("CK/Landscape")
        build_landscape(random.Random(int(ARGS.get("landseed", "33"))))
    if STAGE == "roads":
        L.clear_ck("CK/Roads")
        build_roads()
    if STAGE == "optimize":
        optimize_level()
        unreal.EditorAssetLibrary.save_directory(MERGED, only_if_is_dirty=True)
    L.LES.save_current_level()
    print("level saved", LEVEL)


main()
