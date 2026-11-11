"""Warm facade fill for every landmark (Loggia, Hall, Cathedral, towers, bridge, grand stair): one point light
12 m in front of the facade (local +Y), so the marble reads pale instead of a dark silhouette."""
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_level_common as L  # noqa: E402
from ck_level_common import M, v  # noqa: E402

ARGS = globals().get("CK_ARGS", {})
KEYS = ("Loggia", "Hall", "Cathedral", "TowerRound", "TowerSquare", "Bridge", "StairGrand")
E = L.EAS
for a in E.get_all_level_actors():
    if a.get_actor_label().startswith("CK_LandmarkFill"):
        E.destroy_actor(a)
n = 0
for a in E.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith("CK/Architecture") or not isinstance(a, unreal.StaticMeshActor):
        continue
    nm = a.static_mesh_component.static_mesh.get_name() if a.static_mesh_component.static_mesh else ""
    if not any(k in nm for k in KEYS):
        continue
    b = a.static_mesh_component.static_mesh.get_bounding_box()
    t = a.get_actor_transform()
    c = t.transform_location(unreal.Vector((b.min.x + b.max.x) / 2, b.max.y, 0))
    fwd = t.transform_direction(unreal.Vector(0, 1, 0))
    x, y = c.x / M + fwd.x * 12, c.y / M + fwd.y * 12
    z = a.get_actor_location().z / M + 10
    pl = L.spawn_class(unreal.PointLight, v(x, y, z), folder="CK/Lighting/BuildingFill", label="CK_LandmarkFill_%02d" % n)
    pc = pl.get_component_by_class(unreal.PointLightComponent)
    pc.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
    pc.set_editor_property("intensity", float(ARGS.get("fill", "22000")) * (1.0 + math.hypot(x, y) / 300.0))
    pc.set_editor_property("attenuation_radius", 4500.0)
    pc.set_editor_property("cast_shadows", False)
    pc.set_editor_property("light_color", unreal.Color(r=255, g=232, b=200, a=255))
    pc.set_editor_property("volumetric_scattering_intensity", 0.0)
    n += 1
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print("landmark fills", n)
