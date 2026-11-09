"""Coarser Nanite fallback meshes for GPUs without Nanite (e.g. Intel Iris Xe on the D3D11/SM5 path).
On such hardware the fallback mesh IS what gets drawn: 7.2 M fallback triangles made the base pass ~85 ms.
Nanite-capable GPUs are unaffected (they render the full Nanite data).
CK_ARGS: crystal=5.0 building=2.0 other=2.5   (FallbackRelativeError per group; engine default 1.0)
"""
import unreal

ARGS = globals().get("CK_ARGS", {})
ERR = {"Crystals": float(ARGS.get("crystal", "5.0")), "Rocks": float(ARGS.get("other", "2.5")),
       "Architecture": float(ARGS.get("building", "2.0")), "Cave": float(ARGS.get("cave", "2.0")),
       "Props": float(ARGS.get("other", "2.5")), "Merged": float(ARGS.get("other", "2.5"))}
EAL = unreal.EditorAssetLibrary
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
before = after = changed = 0
for folder, err in ERR.items():
    for p in EAL.list_assets("/Game/CrystalKingdom/Meshes/" + folder, recursive=False):
        sm = unreal.load_asset(p)
        if not isinstance(sm, unreal.StaticMesh):
            continue
        ns = sm.get_editor_property("nanite_settings")
        if not ns.enabled:
            continue
        before += sm.get_num_triangles(0)
        ns.fallback_target = unreal.NaniteFallbackTarget.RELATIVE_ERROR
        ns.fallback_relative_error = err
        SUB.set_nanite_settings(sm, ns, True)   # apply_changes=True rebuilds Nanite + fallback (set_editor_property does not)
        EAL.save_loaded_asset(sm)
        after += sm.get_num_triangles(0)
        changed += 1
print("fallback: meshes changed", changed, "| per-asset fallback tris", before, "->", after)
