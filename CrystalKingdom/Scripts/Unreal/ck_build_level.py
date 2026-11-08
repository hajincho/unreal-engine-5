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
    ("Architecture/SM_Arch_Gallery", 160, 70, 14.0, 160, 1.0),
    ("Architecture/SM_Bldg_Plaza", 76, 50, 6.0, 125, 1.0),
    ("Architecture/SM_Bldg_House_04", 104, 84, 6.0, 165, 1.0),
    ("Architecture/SM_Bldg_House_05", 84, 92, 6.0, 120, 1.0),
    ("Architecture/SM_Arch_Arcade", 112, 60, 6.0, 150, 1.0),
    ("Architecture/SM_Arch_Stairs_Curved", 120, 52, 0.0, 200, 1.2),
    ("Architecture/SM_Bldg_Cathedral", 372, -20, 34.0, 90, 1.0),
    ("Architecture/SM_Bldg_TowerSquare", 326, -80, 24.0, 90, 1.1),
    ("Architecture/SM_Bldg_TowerRound", 352, 82, 22.4, 0, 0.9),
    ("Architecture/SM_Bldg_House_02", 268, -44, 20.0, 100, 1.0),
    ("Architecture/SM_Bldg_House_04", 262, 58, 12.0, 70, 1.0),
    ("Architecture/SM_Bldg_House_01", 395, 40, 34.0, 120, 0.9),
    ("Architecture/SM_Bldg_Hall", 300, 70, 8.0, 110, 0.9),
]


def build_architecture():
    for i, (mesh, x, y, z, yaw, s) in enumerate(ARCH):
        L.spawn_mesh(mesh, v(x, y, z), rot(yaw=yaw), s, folder="CK/Architecture", label=mesh.split("/")[-1] + "_%02d" % i)
    print("architecture ok")


# --------------------------------------------------------------------------- crystals
LANDMARKS = [  # mesh, x, y, z, yaw, scale, material instance (None = mesh default)
    ("SM_Crystal_ColumnMass_04", 20, -40, -3, 15, (1.0, 1.0, 1.3), None),
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
    ("SM_Crystal_FloorGiant_01", 48, 80, 0, 20, (0.8, 0.8, 0.8), None),
    ("SM_Crystal_FloorGiant_02", 150, -96, 0, 80, (1.0, 1.0, 1.0), "MI_Crystal_Violet"),
    ("SM_Crystal_FloorGiant_03", 292, 36, 4, 0, (1.1, 1.1, 1.2), None),
    ("SM_Crystal_FloorGiant_04", 422, 0, 10, 0, (1.2, 1.2, 1.4), "MI_Crystal_White"),
    ("SM_Crystal_FloorGiant_01", 98, -60, 3, 140, (0.6, 0.6, 0.7), None),
    ("SM_Crystal_FloorGiant_03", 128, 96, 5, 60, (0.7, 0.7, 0.8), "MI_Crystal_Violet"),
]


def build_crystal_landmarks():
    for i, (mesh, x, y, z, yaw, s, mi) in enumerate(LANDMARKS):
        L.spawn_mesh("Crystals/" + mesh, v(x, y, z), rot(yaw=yaw), s, folder="CK/Crystals/Landmarks",
                     label="%s_L%02d" % (mesh, i), material=(MI + mi) if mi else None)
    print("landmarks ok")


def pick(rng, base, n):
    return "Crystals/%s_%02d" % (base, rng.randint(1, n))


def build_ceiling_crystals(rng, count=95):
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
        down = unreal.Vector(0, 0, -1)
        d = L.tilt((down * 0.78 + n * 0.22).normal(), 9, rng)
        big = rng.random() < 0.92
        mesh = pick(rng, "SM_Crystal_CeilingGiant", 5) if big else pick(rng, "SM_Crystal_Wall", 4)
        s = rng.uniform(0.5, 1.15) if big else rng.uniform(1.5, 3.0)
        loc = unreal.Vector(px * M, py * M, pz * M) - d * (550.0 * s)
        mi = rng.choice([None, None, "MI_Crystal_White", "MI_Crystal_Teal", "MI_Crystal_Violet"]) if big else None
        L.spawn_mesh(mesh, loc, L.rot_from_dir(d, rng.uniform(0, 360)), s, folder="CK/Crystals/Ceiling",
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
        hit = L.trace(v(x, y, 60), v(x, y, 400))
        if not hit or hit[0][2] > 200:
            continue
        (px, py, pz), n = hit
        L.spawn_mesh("Crystals/SM_Crystal_ColumnMass_%02d" % (i % 6 + 1), v(px, py, pz + 4), rot(pitch=180, yaw=rng.uniform(0, 360)),
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
        d = L.tilt(n, 35, rng)
        r = rng.random()
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
        elif r < 0.88:
            mesh, s = pick(rng, "SM_Crystal_Branch", 4), rng.uniform(0.5, 1.2)
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
    for i, (x, y, s) in enumerate(spots):
        hit = L.trace(v(x, y, 60), v(x, y, -40))
        z = hit[0][2] if hit else 0.5
        L.spawn_mesh(pick(rng, "SM_Crystal_Block", 5), v(x, y, z - 0.4), rot(pitch=rng.uniform(-6, 6), yaw=rng.uniform(0, 360), roll=rng.uniform(-6, 6)),
                     s, folder="CK/Crystals/Foreground", label="FG_Block_%02d" % i,
                     material=MI + rng.choice(["MI_Crystal_Block", "MI_Crystal_Block", "MI_Crystal_BlockViolet", "MI_Crystal_Opal"]))
    for i in range(10):
        x, y = rng.uniform(0, 18), rng.uniform(-16, 18)
        hit = L.trace(v(x, y, 60), v(x, y, -40))
        if hit:
            L.spawn_mesh(pick(rng, "SM_Crystal_Shard", 6), v(hit[0][0], hit[0][1], hit[0][2] - 0.1), rot(yaw=rng.uniform(0, 360)),
                         rng.uniform(1.0, 2.5), folder="CK/Crystals/Foreground")
    for i in range(26):
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
    set_props(sc, intensity=0.6, lower_hemisphere_is_black=False, lower_hemisphere_color=unreal.LinearColor(0.03, 0.10, 0.12, 1.0),
              source_type=unreal.SkyLightSourceType.SLS_CAPTURED_SCENE, real_time_capture=False)
    # Height fog with volumetric fog
    fog = L.spawn_class(unreal.ExponentialHeightFog, v(190, 0, 0), folder="CK/Lighting", label="CK_Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    set_props(fc, fog_density=0.006, fog_height_falloff=0.0016, fog_inscattering_luminance=unreal.LinearColor(0.025, 0.10, 0.13, 1.0),
              start_distance=1500.0, enable_volumetric_fog=True, volumetric_fog_scattering_distribution=0.7,
              volumetric_fog_albedo=unreal.Color(r=150, g=215, b=235, a=255), volumetric_fog_extinction_scale=0.9,
              volumetric_fog_distance=45000.0, volumetric_fog_static_lighting_scattering_intensity=1.0,
              volumetric_fog_emissive=unreal.LinearColor(0.002, 0.008, 0.011, 1.0))
    # Visible god-ray shafts under the skylight chimneys (spot lights through volumetric fog)
    for i, (p, pitch, yaw, cone, inten) in enumerate([((160, -4, 140), -80, 175, 13.0, 3200000.0), ((176, -14, 140), -84, 160, 8.0, 1600000.0), ((150, 6, 140), -76, 170, 5.0, 900000.0),
                                                       ((138, 54, 140), -78, -170, 6.0, 700000.0), ((214, 26, 140), -82, 170, 6.0, 700000.0)]):
        sp = L.spawn_class(unreal.SpotLight, v(*p), rot(pitch=pitch, yaw=yaw), folder="CK/Lighting/Shafts", label="CK_Shaft_%02d" % i)
        spc = sp.get_component_by_class(unreal.SpotLightComponent)
        set_props(spc, intensity_units=unreal.LightUnits.CANDELAS, intensity=inten, outer_cone_angle=cone, inner_cone_angle=cone * 0.4,
                  attenuation_radius=22000.0, light_color=unreal.Color(r=255, g=250, b=240, a=255), volumetric_scattering_intensity=9.0,
                  cast_shadows=True)
    # Crystal bounce: cyan/violet fills near the big masses, warm window glow near the city
    fills = [((22, -30, 30), (0.4, 0.9, 1.0), 20000, 5500), ((60, 55, 30), (0.45, 0.85, 1.0), 16000, 5000),
             ((120, -95, 40), (0.65, 0.5, 1.0), 16000, 6000), ((240, 115, 40), (0.4, 0.85, 1.0), 16000, 6000),
             ((300, -100, 40), (0.6, 0.55, 1.0), 16000, 6000), ((150, 0, 90), (0.5, 0.9, 1.0), 12000, 12000),
             ((410, 0, 60), (0.45, 0.8, 1.0), 16000, 9000)]
    for i, (p, c, inten, radius) in enumerate(fills):
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/CrystalFill", label="CK_CrystalFill_%02d" % i)
        pc = pl.get_component_by_class(unreal.PointLightComponent)
        set_props(pc, intensity=float(inten), attenuation_radius=float(radius), light_color=unreal.Color(r=int(c[0] * 255), g=int(c[1] * 255), b=int(c[2] * 255), a=255),
                  cast_shadows=False, volumetric_scattering_intensity=0.6, intensity_units=unreal.LightUnits.UNITLESS)
    for i, p in enumerate([(60, -20, 125), (130, 30, 130), (200, -40, 135), (250, 50, 130), (110, -70, 120), (300, 0, 140)]):
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/CeilingFill", label="CK_CeilingFill_%02d" % i)
        set_props(pl.get_component_by_class(unreal.PointLightComponent), intensity=45000.0, attenuation_radius=8000.0, cast_shadows=False,
                  light_color=unreal.Color(r=120, g=220, b=255, a=255), intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=0.3)
    for i, p in enumerate([(30, 5, 1.5), (60, -10, 1.5), (55, 25, 1.5), (100, 5, 1.5)]):  # light the shallows from just above the water
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/Shallows", label="CK_Shallows_%02d" % i)
        set_props(pl.get_component_by_class(unreal.PointLightComponent), intensity=9000.0, attenuation_radius=3000.0, cast_shadows=False,
                  light_color=unreal.Color(r=90, g=230, b=255, a=255), intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=0.0)
    warm = [(172, -20, 8), (172, 5, 8), (172, 30, 8), (172, 52, 8), (12, -14, 4), (20, -22, 7), (28, -30, 9), (44, -28, 12), (60, -20, 16), (38, -33, 9), (50, -27, 9), (60, -21, 9), (40, -32, 17), (55, -24, 17), (180, -50, 16), (190, 0, 16), (190, 88, 22), (84, 60, 10), (378, -4, 42), (330, -70, 32), (352, 78, 30)]
    for i, p in enumerate(warm):
        pl = L.spawn_class(unreal.PointLight, v(*p), folder="CK/Lighting/Windows", label="CK_WindowWarm_%02d" % i)
        pc = pl.get_component_by_class(unreal.PointLightComponent)
        set_props(pc, intensity=8000.0, attenuation_radius=2200.0, light_color=unreal.Color(r=255, g=170, b=90, a=255), cast_shadows=False,
                  intensity_units=unreal.LightUnits.UNITLESS, volumetric_scattering_intensity=1.0)
    # Post process (unbound)
    pp = L.spawn_class(unreal.PostProcessVolume, v(190, 0, 50), folder="CK/Lighting", label="CK_PostProcess")
    pp.set_editor_property("unbound", True)
    s = pp.settings
    over = dict(auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL, auto_exposure_bias=float(ARGS.get("ev", "2.2")),
                auto_exposure_apply_physical_camera_exposure=False, bloom_intensity=0.9, bloom_threshold=-1.0,
                vignette_intensity=0.35, color_saturation=unreal.Vector4(1.1, 1.1, 1.1, 1.0),
                color_gain_shadows=unreal.Vector4(0.92, 1.0, 1.06, 1.0), color_gain_highlights=unreal.Vector4(1.04, 1.0, 0.95, 1.0),
                color_contrast=unreal.Vector4(1.05, 1.05, 1.05, 1.0), lumen_scene_view_distance=60000.0, lumen_max_trace_distance=40000.0,
                lumen_scene_detail=2.0, lumen_scene_lighting_quality=2.0, lumen_final_gather_quality=1.5, lumen_reflection_quality=1.0,
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
    ("CAM_Reference", (0, 0, 7.5), -1.0, 0.0, 19.0),
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
    if STAGE in ("all", "lighting"):
        if STAGE == "lighting":
            L.clear_ck("CK/Lighting")
        build_lighting()
    if STAGE in ("all", "cameras"):
        if STAGE == "cameras":
            L.clear_ck("CK/Cameras")
        build_cameras()
        build_game_mode()
    L.LES.save_current_level()
    print("level saved", LEVEL)


main()
