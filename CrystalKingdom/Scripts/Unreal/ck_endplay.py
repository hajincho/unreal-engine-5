"""Leave Play-In-Editor so editor scripts act on CK_Main (EditorActorSubsystem refuses to work during PIE)."""
import time

import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    les.editor_request_end_play()
    print("PIE stopped")
w = unreal.EditorLevelLibrary.get_editor_world()
print("world", w.get_path_name() if w else None)
