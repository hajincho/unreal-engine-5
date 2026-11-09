"""Shared helpers for the Crystal Kingdom level scripts (run inside the editor)."""
import math
import random

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
M = 100.0  # meters -> cm
MESH = "/Game/CrystalKingdom/Meshes/"
MATS = "/Game/CrystalKingdom/Materials/"
_cache = {}


def asset(path):
    if path not in _cache:
        _cache[path] = unreal.load_asset(path)
        if _cache[path] is None:
            raise RuntimeError("missing asset " + path)
    return _cache[path]


def world():
    return UES.get_editor_world()


def v(x, y, z):
    return unreal.Vector(x * M, y * M, z * M)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def spawn_mesh(mesh, loc, rotation=None, scale=1.0, folder="CK", label=None, material=None, shadows=True,
               collision=True, mobility_static=True):
    sm = asset(mesh if mesh.startswith("/") else MESH + mesh)
    a = EAS.spawn_actor_from_object(sm, loc, rotation or rot())
    if a is None:
        return None
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    a.set_actor_scale3d(unreal.Vector(*scale))
    a.set_folder_path(folder)
    if label:
        a.set_actor_label(label)
    comp = a.static_mesh_component
    if material is not None:
        mat = asset(material) if isinstance(material, str) else material
        for i in range(comp.get_num_materials()):
            comp.set_material(i, mat)
    if not shadows:
        comp.set_editor_property("cast_shadow", False)
    if not collision:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    a.tags = [unreal.Name("CK")]
    return a


def spawn_class(cls, loc, rotation=None, folder="CK", label=None):
    a = EAS.spawn_actor_from_class(cls, loc, rotation or rot())
    a.set_folder_path(folder)
    if label:
        a.set_actor_label(label)
    a.tags = [unreal.Name("CK")]
    return a


def trace(start, end):
    """Line trace (complex) in the editor world. Returns (point_m, normal) or None."""
    r = unreal.SystemLibrary.line_trace_single(world(), start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                               unreal.DrawDebugTrace.NONE, True)
    if r is None:
        return None
    hr = r[1] if isinstance(r, tuple) else r
    if hr is None:
        return None
    t = hr.to_tuple()
    if not t[0]:
        return None
    p = t[5]
    n = t[7]
    return (p.x / M, p.y / M, p.z / M), n


def rot_from_dir(d, spin_deg=0.0):
    """Rotator whose +Z points along vector d (unreal.Vector), with spin about d."""
    d = d.normal()
    ref = unreal.Vector(1, 0, 0) if abs(d.x) < 0.9 else unreal.Vector(0, 1, 0)
    x = ref - d * ref.dot(d)
    x = x.normal()
    if spin_deg:
        y = d.cross(x)
        a = math.radians(spin_deg)
        x = x * math.cos(a) + y * math.sin(a)
    return unreal.MathLibrary.make_rot_from_zx(d, x)


def tilt(d, max_deg, rng):
    """Random perturbation of a direction vector by up to max_deg."""
    a = math.radians(rng.uniform(0, max_deg))
    ph = rng.uniform(0, 2 * math.pi)
    ref = unreal.Vector(1, 0, 0) if abs(d.x) < 0.9 else unreal.Vector(0, 1, 0)
    x = (ref - d * ref.dot(d)).normal()
    y = d.cross(x)
    return (d * math.cos(a) + (x * math.cos(ph) + y * math.sin(ph)) * math.sin(a)).normal()


def clear_ck(prefix="CK"):
    n = 0
    for a in EAS.get_all_level_actors():
        if str(a.get_folder_path()).startswith(prefix) or (prefix == "CK" and unreal.Name("CK") in a.tags):
            EAS.destroy_actor(a)
            n += 1
    return n


def far_from(x, y, zones):
    for (cx, cy, r) in zones:
        if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
            return False
    return True
