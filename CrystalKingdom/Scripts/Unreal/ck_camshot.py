"""High-res screenshot straight from a CineCamera actor placed anywhere (no viewport piloting).
CK_ARGS: x y z (m) pitch yaw [fov=18 focal mm] name   -> Saved/Screenshots/WindowsEditor/<name>.png
"""
import unreal

ARGS = globals().get("CK_ARGS", {})
E = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cam = next((a for a in E.get_all_level_actors() if a.get_actor_label() == "CAM_Probe"), None)
if cam is None:
    cam = E.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    cam.set_actor_label("CAM_Probe")
    cam.set_folder_path("CK/Cameras")
cam.set_actor_location_and_rotation(unreal.Vector(float(ARGS["x"]) * 100, float(ARGS["y"]) * 100, float(ARGS["z"]) * 100),
                                    unreal.Rotator(0, float(ARGS.get("pitch", "0")), float(ARGS.get("yaw", "0"))), False, False)
cc = cam.get_cine_camera_component()
fs = cc.get_editor_property("focus_settings")
fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
cc.set_editor_property("focus_settings", fs)
cc.set_editor_property("current_focal_length", float(ARGS.get("fov", "18")))
print(unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, ARGS.get("name", "probe") + ".png", camera=cam, force_game_view=True))
