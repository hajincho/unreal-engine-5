"""CrystalKingdom hand-placement tools (called from the 'CK 건축' toolbar, ck_toolbar.py).

Buildings placed here live in the outliner folder CK/Architecture/Manual. The build stages never clear that
folder (only stage=world wipes everything), and the map / road planner treat them like any other house.
"""
import json
import math
import os
import subprocess
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ck_level_common as L  # noqa: E402

M = 100.0
MANUAL = "CK/Architecture/Manual"
MESH_DIR = "/Game/CrystalKingdom/Meshes/Architecture/"
PROJ = os.path.dirname(os.path.dirname(HERE))
STONE = "/Game/CrystalKingdom/Materials/Instances/MI_StoneTrim"

# (mesh suffix, Korean label, group)
BUILDINGS = [
    ("House_01", "주택 01", "주택"), ("House_02", "주택 02", "주택"), ("House_03", "주택 03", "주택"),
    ("House_04", "주택 04", "주택"), ("House_05", "주택 05", "주택"), ("House_06", "주택 06", "주택"),
    ("Town_01", "타운하우스 (3층)", "주택"), ("Town_02", "타운하우스 (4층)", "주택"),
    ("TowerHouse", "원탑 주택", "주택"), ("DomeHouse", "돔 주택", "주택"), ("Gatehouse", "아치 통로 문루집", "주택"),
    ("Manor", "망사르드 저택 (대형)", "대형"), ("Courtyard", "중정 저택 (대형)", "대형"), ("Hall", "홀", "대형"),
    ("Loggia", "로지아", "대형"), ("Cathedral", "대성당", "대형"),
    ("TowerRound", "원형 첨탑", "첨탑"), ("TowerSquare", "사각 첨탑", "첨탑"),
]


def _notify(msg):
    """Log line; messages starting with '!' are problems and also pop a dialog."""
    unreal.log("[CK] " + msg)
    if msg.startswith("!"):
        unreal.EditorDialog.show_message("CK 건축", msg[1:].strip(), unreal.AppMsgType.OK)


def _selected():
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return [a for a in sub.get_selected_level_actors() if isinstance(a, unreal.StaticMeshActor)]


def _bounds_local(a):
    return a.static_mesh_component.static_mesh.get_bounding_box()


def _center(a):
    b = _bounds_local(a)
    p = a.get_actor_transform().transform_location(unreal.Vector((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, 0))
    return p.x / M, p.y / M


def _footprint(a, inset=0.0):
    b = _bounds_local(a)
    t = a.get_actor_transform()
    out = []
    for x, y in ((b.min.x, b.min.y), (b.max.x, b.min.y), (b.max.x, b.max.y), (b.min.x, b.max.y)):
        p = t.transform_location(unreal.Vector(x, y, 0))
        out.append((p.x / M, p.y / M))
    if inset:
        cx = sum(p[0] for p in out) / 4
        cy = sum(p[1] for p in out) / 4
        out = [(cx + (x - cx) * (1 - inset), cy + (y - cy) * (1 - inset)) for x, y in out]
    return out


def _set_center_yaw(a, cx, cy, z, yaw):
    """Place so the footprint centre lands on (cx, cy) - the mesh pivot is its front-left corner."""
    b = _bounds_local(a)
    lx, ly = (b.min.x + b.max.x) / 2 / M, (b.min.y + b.max.y) / 2 / M
    r = math.radians(yaw)
    ox = lx * math.cos(r) - ly * math.sin(r)
    oy = lx * math.sin(r) + ly * math.cos(r)
    a.set_actor_location_and_rotation(unreal.Vector((cx - ox) * M, (cy - oy) * M, z * M), unreal.Rotator(0, 0, yaw), False, False)


def _face_yaw(px, py, dx, dy):
    return math.degrees(math.atan2(-dx, dy))       # facade (+Y local) toward (dx, dy)


def _view_hit():
    """Where the middle of the active viewport looks at the cave floor / terraces (metres), plus the camera xy."""
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    loc, rot = ues.get_level_viewport_camera_info()
    fwd = rot.get_forward_vector()
    L.reset_terrain_cache()
    best = None
    end = loc + fwd * 60000.0
    for comp, *_ in L._terrain():
        r = comp.line_trace_component(loc, end, True, False, False)
        if isinstance(r, tuple) and r[1].length() > 0.5:
            d = (r[0] - loc).length()
            if best is None or d < best[0]:
                best = (d, r[0])
    if best is None:
        p = loc + fwd * 3000.0
        g = L.ground_z(p.x / M, p.y / M)
        return (p.x / M, p.y / M, g if g is not None else p.z / M), (loc.x / M, loc.y / M)
    p = best[1]
    return (p.x / M, p.y / M, p.z / M), (loc.x / M, loc.y / M)


def _ground_under(a):
    pts = [_center(a)] + _footprint(a, inset=0.2)
    return [L.ground_z(x, y) for x, y in pts]


def _snap(a, plinth=True):
    """Floor on the highest ground under the footprint; a dressed-stone plinth fills the low side of a slope."""
    L.reset_terrain_cache()
    gs = [g for g in _ground_under(a) if g is not None]
    if not gs:
        return "no ground"
    hi, lo = max(gs), min(gs)
    floor = hi if hi - lo > 0.6 else (hi + lo) / 2
    loc = a.get_actor_location()
    a.set_actor_location(unreal.Vector(loc.x, loc.y, (floor - 0.3) * M), False, False)
    lab = a.get_actor_label()
    for o in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if o.get_actor_label() == lab + "_Plinth":
            unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(o)
    if hi - lo > 4.0:     # a terrace edge / the lake shore: a tall plinth reads as a stone tower - ask for a flatter spot
        return "! 바닥 단차 %.1f m - 기단을 만들지 않았습니다. 평평한 곳으로 옮긴 뒤 '지면에 맞추기'를 다시 누르세요" % (hi - lo)
    if plinth and hi - lo > 0.6:
        fp = _footprint(a)
        cx = sum(p[0] for p in fp) / 4
        cy = sum(p[1] for p in fp) / 4
        side = math.hypot(fp[1][0] - fp[0][0], fp[1][1] - fp[0][1])
        depth = math.hypot(fp[2][0] - fp[1][0], fp[2][1] - fp[1][1])
        yaw = math.degrees(math.atan2(fp[1][1] - fp[0][1], fp[1][0] - fp[0][0]))
        p = L.spawn_mesh("/Engine/BasicShapes/Cube", L.v(cx, cy, (floor + max(lo, -0.6)) / 2 - 0.4), L.rot(yaw=yaw),
                         (side + 1.0, depth + 1.0, floor - max(lo, -0.6) + 0.8), folder=str(a.get_folder_path()),
                         label=lab + "_Plinth", material=STONE)
        return "plinth %.1f m" % (floor - lo)
    return "ok"


# ------------------------------------------------------------------ actions
def place(mesh):
    sm = unreal.load_asset(MESH_DIR + "SM_Bldg_" + mesh)
    if sm is None:
        _notify("! 메시를 찾을 수 없습니다: SM_Bldg_" + mesh)
        return
    (hx, hy, hz), (camx, camy) = _view_hit()
    n = sum(1 for o in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if str(o.get_folder_path()) == MANUAL)
    with unreal.ScopedEditorTransaction("CK: 건물 배치 " + mesh):
        a = L.spawn_mesh("Architecture/SM_Bldg_" + mesh, L.v(hx, hy, hz), L.rot(), 1.0, folder=MANUAL,
                         label="Manual_SM_Bldg_%s_%02d" % (mesh, n))
        yaw = _face_yaw(hx, hy, camx - hx, camy - hy)
        _set_center_yaw(a, hx, hy, hz - 0.3, yaw)
        res = _snap(a)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors([a])
    if res.startswith("!") or hz < -0.3:
        _notify("! %s 배치됨 (%.0f, %.0f). %s" % (mesh, hx, hy, res.lstrip("! ") if res.startswith("!") else "호수 위입니다 - 땅으로 옮겨 주세요."))
    else:
        _notify("배치: %s at (%.0f, %.0f) - %s. 이동 기즈모로 옮긴 뒤 '지면에 맞추기'를 누르세요." % (mesh, hx, hy, res))


def rotate(deg):
    with unreal.ScopedEditorTransaction("CK: 회전"):
        for a in _selected():
            cx, cy = _center(a)
            _set_center_yaw(a, cx, cy, a.get_actor_location().z / M, a.get_actor_rotation().yaw + deg)


def face_road():
    path = os.path.join(unreal.Paths.project_saved_dir(), "road_plan.json")
    if not os.path.exists(path):
        _notify("! road_plan.json 이 없습니다. 먼저 '도로 다시 깔기'를 실행하세요.")
        return
    with open(path, encoding="utf-8") as fh:
        pts = [p for r in json.load(fh)["roads"] for p in r["pts"]]
    with unreal.ScopedEditorTransaction("CK: 도로 향하기"):
        for a in _selected():
            cx, cy = _center(a)
            px, py = min(pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
            _set_center_yaw(a, cx, cy, a.get_actor_location().z / M, _face_yaw(cx, cy, px - cx, py - cy))


def face_camera():
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    loc, _ = ues.get_level_viewport_camera_info()
    with unreal.ScopedEditorTransaction("CK: 카메라 향하기"):
        for a in _selected():
            cx, cy = _center(a)
            _set_center_yaw(a, cx, cy, a.get_actor_location().z / M, _face_yaw(cx, cy, loc.x / M - cx, loc.y / M - cy))


def snap():
    out = []
    with unreal.ScopedEditorTransaction("CK: 지면에 맞추기"):
        for a in _selected():
            out.append("%s: %s" % (a.get_actor_label(), _snap(a).lstrip("! ")))
    _notify(("! " if any("단차" in o for o in out) else "") + "지면 맞춤 - " + ", ".join(out))


def clear_crystals():
    n = 0
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    fps = [_footprint(a) for a in _selected()]
    with unreal.ScopedEditorTransaction("CK: 수정 치우기"):
        for o in sub.get_all_level_actors():
            f = str(o.get_folder_path())
            if not f.startswith(("CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Crystals/Walls", "CK/Crystals/Landmarks", "CK/Rocks/Shore")):
                continue
            ob, e = o.get_actor_bounds(False)
            if (ob.z - e.z) / M > 35:
                continue
            x, y, r = ob.x / M, ob.y / M, min(e.x, e.y) / M * 0.55
            for fp in fps:
                xs = [p[0] for p in fp]
                ys = [p[1] for p in fp]
                if min(xs) - r - 1 < x < max(xs) + r + 1 and min(ys) - r - 1 < y < max(ys) + r + 1:
                    sub.destroy_actor(o)
                    n += 1
                    break
    _notify("수정·바위 %d개 치움" % n)


def duplicate_row(gap=2.0):
    """Copy the selected building beside itself along its facade (street row)."""
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    new = []
    with unreal.ScopedEditorTransaction("CK: 옆에 복제"):
        for a in _selected():
            fp = _footprint(a)
            w = math.hypot(fp[1][0] - fp[0][0], fp[1][1] - fp[0][1])
            yaw = a.get_actor_rotation().yaw
            cx, cy = _center(a)
            r = math.radians(yaw)
            nx, ny = cx + math.cos(r) * (w + gap), cy + math.sin(r) * (w + gap)
            mesh = a.static_mesh_component.static_mesh.get_name().replace("SM_Bldg_", "")
            b = L.spawn_mesh("Architecture/SM_Bldg_" + mesh, L.v(nx, ny, 0), L.rot(), 1.0, folder=MANUAL,
                             label=a.get_actor_label() + "_r")
            _set_center_yaw(b, nx, ny, a.get_actor_location().z / M, yaw)
            _snap(b)
            new.append(b)
    if new:
        sub.set_selected_level_actors(new)


def _run(script, **args):
    path = os.path.join(HERE, script)
    src = open(path, encoding="utf-8").read()
    exec(compile(src, path, "exec"), {"__name__": "__main__", "CK_ARGS": {k: str(v) for k, v in args.items()}, "__file__": path})


def _python():
    eng = unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_dir())
    return os.path.join(eng, "Binaries", "ThirdParty", "Python3", "Win64", "python.exe")


def rebuild_roads():
    """Map shapes -> straight road plan -> paving, embankments, street furniture -> audit repair."""
    with unreal.ScopedSlowTask(5, "CK: 도로 다시 깔기") as t:
        t.make_dialog(True)
        t.enter_progress_frame(1, "건물 윤곽 읽기")
        _run("ck_mapdata.py", shapes_only=1)
        t.enter_progress_frame(1, "직선 도로 계획")
        saved = os.path.join(PROJ, "Saved")
        r = subprocess.run([_python(), "-I", os.path.join(PROJ, "Tools", "plan_roads.py"), os.path.join(saved, "map_data.json"),
                            os.path.join(saved, "road_plan.json")], capture_output=True, text=True, encoding="utf-8")
        unreal.log(r.stdout[-2000:] + r.stderr[-2000:])
        t.enter_progress_frame(1, "포장·축대")
        _run("ck_build_level.py", stage="roads")
        t.enter_progress_frame(1, "가로 조경")
        _run("ck_build_level.py", stage="landscape")
        t.enter_progress_frame(1, "결함 감사·수정")
        _run("ck_audit.py", fix=1)
    _notify("도로 다시 깔기 완료 (Output Log 참고)")


def audit(fix=False):
    _run("ck_audit.py", fix=1 if fix else 0)
    p = os.path.join(unreal.Paths.project_saved_dir(), "audit_fix.json" if fix else "audit.json")
    with open(p, encoding="utf-8") as fh:
        r = json.load(fh)
    keys = {"overlaps": "겹침", "crystals_in_buildings": "집 안 수정", "roads_in_buildings": "건물 관통 도로", "floating": "떠 있는 물체",
            "floating_buildings": "떠 있는 건물", "road_fragments": "분리된 도로", "balustrade_fragments": "끊긴 난간", "orphans": "고아 구조물"}
    lines = ["%s: %d" % (v, len(r.get(k, []))) for k, v in keys.items()]
    unreal.EditorDialog.show_message("CK 감사" + (" + 수정" if fix else ""), "\n".join(lines), unreal.AppMsgType.OK)


def refresh_map():
    with unreal.ScopedSlowTask(2, "CK: 지도 갱신") as t:
        t.make_dialog(True)
        t.enter_progress_frame(1, "지형 샘플링")
        _run("ck_mapdata.py", step=3)
        t.enter_progress_frame(1, "지도 그리기")
        saved = os.path.join(PROJ, "Saved")
        svg = os.path.join(PROJ, "Screenshots", "map_plan.svg")
        subprocess.run([_python(), "-I", os.path.join(PROJ, "Tools", "make_map.py"), os.path.join(saved, "map_data.json"), svg,
                        os.path.join(saved, "road_plan.json")], capture_output=True, text=True, encoding="utf-8")
    os.startfile(svg)


def save():
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
