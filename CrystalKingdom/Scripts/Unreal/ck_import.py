"""Import Blender FBX exports / PNG textures into the CrystalKingdom content tree.

Run inside the editor (via Tools/ue_remote.py) with CK_ARGS:
  kind=mesh  src=<folder under SourceArt/Export>  dest=/Game/CrystalKingdom/Meshes/<X>
             nanite=1  collision=ucx|complex|none  filter=<substring>
  kind=tex   (imports SourceArt/Textures/*.png into /Game/CrystalKingdom/Textures)
  kind=folders
"""
import glob
import os

import unreal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(unreal.Paths.get_project_file_path()))))
PROJ = os.path.dirname(os.path.abspath(unreal.Paths.get_project_file_path()))
ARGS = globals().get("CK_ARGS", {})

FOLDERS = ["Maps", "Meshes/Cave", "Meshes/Crystals", "Meshes/Architecture", "Meshes/Rocks", "Meshes/Props",
           "Materials/Master", "Materials/Instances", "Textures", "Blueprints", "PCG", "Lighting", "Cameras"]


def make_folders():
    for f in FOLDERS:
        unreal.EditorAssetLibrary.make_directory("/Game/CrystalKingdom/" + f)
    print("folders ok")


def pipeline(nanite, collision):
    p = unreal.InterchangeGenericAssetsPipeline()
    p.set_editor_property("use_source_name_for_asset", True)
    p.set_editor_property("asset_type_sub_folders", False)
    cm = p.get_editor_property("common_meshes_properties")
    cm.set_editor_property("vertex_color_import_option", unreal.InterchangeVertexColorImportOption.IVCIO_REPLACE)
    cm.set_editor_property("recompute_normals", False)
    cm.set_editor_property("import_lods", False)
    mp = p.get_editor_property("mesh_pipeline")
    mp.set_editor_property("import_static_meshes", True)
    mp.set_editor_property("import_skeletal_meshes", False)
    beh = getattr(unreal, "InterchangeStaticMeshCombineBehavior", None) or getattr(unreal, "InterchangeCombineStaticMeshesBehavior", None)
    if beh is not None:
        opts = [a for a in dir(beh) if a.isupper()]
        pick = next((a for a in opts if "ALL" in a and "COMBINE" in a), None) or next((a for a in opts if "COMBINE" in a or "ALL" in a), None)
        if pick:
            mp.set_editor_property("combine_static_meshes_behavior", getattr(beh, pick))
    else:
        print("combine enum not found; options:", [a for a in dir(unreal) if "Combine" in a])
    mp.set_editor_property("build_nanite", bool(nanite))
    mp.set_editor_property("generate_lightmap_u_vs", False)
    mp.set_editor_property("import_collision_according_to_mesh_name", collision == "ucx")
    mp.set_editor_property("collision", collision == "ucx")
    mat = p.get_editor_property("material_pipeline")
    mat.set_editor_property("import_materials", False)
    return p


def import_meshes():
    src = os.path.join(PROJ, "SourceArt", "Export", ARGS["src"])
    dest = ARGS["dest"]
    nanite = ARGS.get("nanite", "1") == "1"
    collision = ARGS.get("collision", "complex")
    flt = ARGS.get("filter", "")
    files = sorted(f for f in glob.glob(os.path.join(src, "*.fbx")) if flt in os.path.basename(f))
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", f)
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", False)
        t.set_editor_property("options", pipeline(nanite, collision))
        tools.import_asset_tasks([t])  # one at a time: batched Interchange tasks run async
    n = 0
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        path = dest + "/" + name
        sm = unreal.EditorAssetLibrary.load_asset(path)
        if not sm:
            print("MISSING", path)
            continue
        bs = sm.get_editor_property("body_setup")
        if bs:
            if collision == "complex":
                bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            elif collision == "none":
                bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
        n += 1
    print("imported %d / %d meshes into %s" % (n, len(files), dest))


def import_textures():
    src = os.path.join(PROJ, "SourceArt", "Textures")
    dest = "/Game/CrystalKingdom/Textures"
    files = sorted(glob.glob(os.path.join(src, "*.png")))
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", f)
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", False)
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        tex = unreal.EditorAssetLibrary.load_asset(dest + "/" + name)
        if not tex:
            print("MISSING", name)
            continue
        tex.set_editor_property("srgb", False)
        if name.endswith("_N"):
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("flip_green_channel", True)
            tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
        else:
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        unreal.EditorAssetLibrary.save_asset(dest + "/" + name, only_if_is_dirty=False)
    print("imported %d textures" % len(files))


kind = ARGS.get("kind", "mesh")
if kind == "folders":
    make_folders()
elif kind == "tex":
    import_textures()
else:
    import_meshes()
