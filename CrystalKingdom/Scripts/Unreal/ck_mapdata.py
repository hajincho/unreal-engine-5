"""Export a top-view map of CK_Main to Saved/map_data.json (read by Tools/make_map.py).
Grid: downward traces every STEP metres -> ground height + what was hit (terrain / building / road / crystal / wall).
Shapes: oriented footprints of every building and road-like structure (bridge, stairs, plaza), with labels.
CK_ARGS: step=3
"""
import json
import math
import os

import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import ck_level_common as L  # noqa: E402

importlib.reload(L)

ARGS = globals().get("CK_ARGS", {})
STEP = float(ARGS.get("step", "3"))
M = 100.0
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

ROAD_KEYS = ("Bridge", "Stair", "Plaza", "Gallery", "Arcade")


def category(actor):
    if actor is None:
        return "void"
    f = str(actor.get_folder_path())
    name = actor.get_actor_label()
    if f.startswith("CK/Roads"):
        return "road"
    if f.startswith("CK/Cave"):
        return "ground"
    if f.startswith("CK/Rocks/Terraces"):
        return "terrace"
    if f.startswith("CK/Architecture/TerraceWalls"):
        return "wall"
    if f.startswith("CK/Architecture"):
        comp = actor.static_mesh_component if isinstance(actor, unreal.StaticMeshActor) else None
        if comp and comp.static_mesh and comp.static_mesh.get_name() == "Cube":
            return "plinth"          # stone plinths under hillside houses: ground, not a building with a door
        return "road" if any(k in name for k in ROAD_KEYS) else "building"
    if f.startswith("CK/Crystals"):
        return "crystal"
    if f.startswith("CK/Rocks"):
        return "rock"
    return "other"


def footprint(actor):
    """Oriented XY rectangle of the mesh's local bounds, in metres."""
    comp = actor.static_mesh_component
    sm = comp.static_mesh if comp else None
    if sm is None:
        return None
    b = sm.get_bounding_box()
    t = actor.get_actor_transform()
    pts = []
    for x, y in ((b.min.x, b.min.y), (b.max.x, b.min.y), (b.max.x, b.max.y), (b.min.x, b.max.y)):
        p = t.transform_location(unreal.Vector(x, y, 0))
        pts.append((round(p.x / M, 2), round(p.y / M, 2)))
    return pts


out = os.path.join(unreal.Paths.project_saved_dir(), "map_data.json")
SHAPES_ONLY = ARGS.get("shapes_only", "0") == "1" and os.path.exists(out)
cells = []
xs = [x * STEP for x in range(int(-60 / STEP), int(460 / STEP) + 1)]
ys = [y * STEP for y in range(int(-190 / STEP), int(190 / STEP) + 1)]
for x in ([] if SHAPES_ONLY else xs):
    row = []
    for y in ys:
        r = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x * M, y * M, 120 * M), unreal.Vector(x * M, y * M, -40 * M),
                                                   unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
        hr = r[1] if isinstance(r, tuple) else r
        t = hr.to_tuple() if hr is not None else None
        if not t or not t[0]:
            row.append(["void", None, None])
            continue
        actor = t[9] if len(t) > 9 and isinstance(t[9], unreal.Actor) else None
        if actor is None:
            for v in t:
                if isinstance(v, unreal.Actor):
                    actor = v
                    break
        gz = L.ground_z(x, y)
        row.append([category(actor), round(t[5].z / M, 1), None if gz is None else round(gz, 1)])
    cells.append(row)

shapes = []
for a in EAS.get_all_level_actors():
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    c = category(a)
    if c not in ("building", "road"):
        continue
    fp = footprint(a)
    if fp:
        p = a.get_actor_location()
        if str(a.get_folder_path()).startswith("CK/Roads"):
            continue  # road pieces are many small slabs: the grid shows them
        b = a.static_mesh_component.static_mesh.get_bounding_box()
        d = a.get_actor_transform().transform_location(unreal.Vector((b.min.x + b.max.x) / 2, b.max.y + 250.0, 0))   # facade = local +Y in UE
        shapes.append({"kind": c, "label": a.get_actor_label(), "pts": fp, "c": [round(p.x / M, 1), round(p.y / M, 1)], "z": round(p.z / M, 1),
                       "door": [round(d.x / M, 1), round(d.y / M, 1)]})

cams = []
for a in EAS.get_all_level_actors():
    if isinstance(a, unreal.CineCameraActor):
        p = a.get_actor_location()
        cams.append({"label": a.get_actor_label(), "x": p.x / M, "y": p.y / M, "yaw": a.get_actor_rotation().yaw})

if SHAPES_ONLY:
    old = json.load(open(out, encoding="utf-8"))
    cells, xs, ys = old["cells"], old["xs"], old["ys"]
with open(out, "w", encoding="utf-8") as f:
    json.dump({"step": STEP, "xs": xs, "ys": ys, "cells": cells, "shapes": shapes, "cams": cams}, f)
print("map data", out, len(xs), "x", len(ys), "shapes", len(shapes))
