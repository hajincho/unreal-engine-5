"""Place the road bodies built by SourceArt/Blender/gen_roads.py (world-space meshes -> actors at the origin)."""
import json
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_level_common as L  # noqa: E402

with open(os.path.join(unreal.Paths.project_saved_dir(), "road_mesh.json"), encoding="utf-8") as fh:
    data = json.load(fh)
print("old roads removed", L.clear_ck("CK/Roads"))
n = 0
for rd in data["roads"]:
    path = "/Game/CrystalKingdom/Meshes/Roads/" + rd["name"]
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        print("missing", path)
        continue
    L.spawn_mesh(path, unreal.Vector(0, 0, 0), L.rot(), 1.0, folder="CK/Roads/" + rd["kind"].capitalize(), label=rd["name"], shadows=True)
    n += 1
with open(os.path.join(unreal.Paths.project_saved_dir(), "road_plan.json"), "w", encoding="utf-8") as fh:
    json.dump({"roads": [{"kind": r["kind"], "width": data["width"], "pts": r["pts"]} for r in data["roads"]], "lake_centre": [170, 5]}, fh)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print("ROADS placed", n)
