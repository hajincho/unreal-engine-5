"""Point the active level viewport at a CineCamera (by label) and request a high-res screenshot.
CK_ARGS: cam=<label> name=<file stem> w=1920 h=1080 phase=pilot|shot
'pilot' moves the viewport to the camera (call, wait a few seconds for Lumen to settle, then 'shot').
Screenshots land in Saved/Screenshots/WindowsEditor/.
"""
import unreal

ARGS = globals().get("CK_ARGS", {})
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cam = next((a for a in EAS.get_all_level_actors() if a.get_actor_label() == ARGS.get("cam", "CAM_Reference")), None)
if cam is None:
    raise RuntimeError("camera not found")
phase = ARGS.get("phase", "pilot")
if phase == "pilot":
    LES.editor_set_game_view(True)
    try:  # already piloting another camera -> pilot_level_actor is ignored, so eject first
        LES.eject_pilot_level_actor()
    except Exception:
        pass
    LES.pilot_level_actor(cam)
    try:
        unreal.SystemLibrary.execute_console_command(None, "r.ScreenPercentage 100")
    except Exception:
        pass
    print("piloting", cam.get_actor_label())
else:
    w, h = int(ARGS.get("w", 1920)), int(ARGS.get("h", 1080))
    name = ARGS.get("name", "shot")
    ok = unreal.AutomationLibrary.take_high_res_screenshot(w, h, name + ".png", camera=cam, force_game_view=True)
    print("screenshot requested", ok, name)
