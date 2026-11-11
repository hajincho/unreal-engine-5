"""Runs automatically when the CrystalKingdom editor starts: registers the 'CK 건축' toolbar (Scripts/Unreal/ck_toolbar.py)."""
import os
import sys

import unreal

_dir = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Scripts", "Unreal")
if _dir not in sys.path:
    sys.path.insert(0, _dir)
try:
    import ck_toolbar
    ck_toolbar.register()
except Exception as e:  # a broken tool script must never stop the editor from starting
    unreal.log_warning("[CK] toolbar not registered: %s" % e)
