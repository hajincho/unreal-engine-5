"""Render a CineCamera view to PNG with a SceneCapture2D (works while the editor window is in the
background). CK_ARGS: cam=<label> name=<stem> w=1920 h=1080 phase=setup|capture|export
Output: <project>/Screenshots/<name>.png
"""
import math
import os

import unreal

ARGS = globals().get("CK_ARGS", {})
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
PROJ = os.path.dirname(unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path()))
RT_PATH = "/Game/CrystalKingdom/Cameras/RT_Capture"


def actor(label):
    return next((a for a in EAS.get_all_level_actors() if a.get_actor_label() == label), None)


def get_rt(w, h):
    rt = unreal.load_asset(RT_PATH) if unreal.EditorAssetLibrary.does_asset_exist(RT_PATH) else None
    if rt is None:
        rt = unreal.AssetToolsHelpers.get_asset_tools().create_asset("RT_Capture", "/Game/CrystalKingdom/Cameras", unreal.TextureRenderTarget2D,
                                                                     unreal.TextureRenderTargetFactoryNew())
    rt.set_editor_property("size_x", w)
    rt.set_editor_property("size_y", h)
    rt.set_editor_property("render_target_format", unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    return rt


phase = ARGS.get("phase", "setup")
w, h = int(ARGS.get("w", 1920)), int(ARGS.get("h", 1080))
cam = actor(ARGS.get("cam", "CAM_Reference"))
cap = actor("CK_Capture")
if phase == "setup":
    if cap is None:
        cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, cam.get_actor_location(), cam.get_actor_rotation())
        cap.set_actor_label("CK_Capture")
        cap.set_folder_path("CK/Cameras")
    cap.set_actor_location_and_rotation(cam.get_actor_location(), cam.get_actor_rotation(), False, True)
    cc = cam.get_cine_camera_component()
    fov = 2 * math.degrees(math.atan(cc.get_editor_property("filmback").sensor_width / (2 * cc.get_editor_property("current_focal_length"))))
    sc = cap.capture_component2d
    sc.set_editor_property("fov_angle", fov)
    sc.set_editor_property("texture_target", get_rt(w, h))
    sc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR)
    sc.set_editor_property("capture_every_frame", True)
    sc.set_editor_property("always_persist_rendering_state", True)
    # reuse the level post process volume settings
    pp = actor("CK_PostProcess")
    if pp:
        sc.set_editor_property("post_process_settings", pp.settings)
        sc.set_editor_property("post_process_blend_weight", 1.0)
    print("capture ready fov=%.1f" % fov)
elif phase == "export":
    rt = unreal.load_asset(RT_PATH)
    out_dir = os.path.join(PROJ, "Screenshots")
    os.makedirs(out_dir, exist_ok=True)
    name = ARGS.get("name", "capture")
    unreal.RenderingLibrary.export_render_target(UES.get_editor_world(), rt, out_dir, name + ".png")
    print("exported", os.path.join(out_dir, name + ".png"))
