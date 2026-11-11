"""'CK 건축' toolbar button (level editor toolbar, User section) + 'CK 건축' main menu.
Registered at editor start by Content/Python/init_unreal.py; run this file again to re-register after edits.
All actions live in ck_tools.py (reloaded on every click, so edits there apply without a restart).
"""
import importlib
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ck_tools  # noqa: E402

OWNER = "CrystalKingdomTools"
_KEEP = []


@unreal.uclass()
class CKMenuAction(unreal.ToolMenuEntryScript):
    """One menu entry; its entry name is the command, e.g. 'place:House_01' or 'rotate:90'."""

    @unreal.ufunction(override=True)
    def execute(self, context):
        import ck_tools as T
        importlib.reload(T)
        cmd = str(self.data.name)
        verb, _, arg = cmd.partition(":")
        try:
            if verb == "place":
                T.place(arg)
            elif verb == "rotate":
                T.rotate(float(arg))
            elif verb == "audit":
                T.audit(fix=(arg == "fix"))
            else:
                getattr(T, verb)()
        except Exception as e:   # never leave the user with a silent click
            unreal.log_error("[CK] %s failed: %s" % (cmd, e))
            unreal.EditorDialog.show_message("CK 건축", "%s 실패:\n%s" % (cmd, e), unreal.AppMsgType.OK)


EDIT = [
    ("rotate:90", "왼쪽으로 90° 회전", "선택한 건물을 바닥 중심 기준으로 회전"),
    ("rotate:-90", "오른쪽으로 90° 회전", "선택한 건물을 바닥 중심 기준으로 회전"),
    ("rotate:15", "15° 회전", "미세 회전"),
    ("face_road", "정면을 가까운 도로로", "도로 계획(road_plan.json)에서 가장 가까운 도로를 향하게"),
    ("face_camera", "정면을 카메라로", "현재 뷰포트 카메라를 향하게"),
    ("snap", "지면에 맞추기 (+기단)", "지형 높이에 앉히고, 경사지면 석조 기단을 받침"),
    ("clear_crystals", "건물 자리의 수정 치우기", "선택한 건물 바닥과 겹치는 수정·바위 삭제"),
    ("duplicate_row", "옆에 한 채 더 (거리 줄)", "정면 방향 옆으로 같은 건물을 복제"),
]
LEVEL = [
    ("rebuild_roads", "도로 다시 깔기", "건물 위치 기준으로 직선 도로 재계획 + 포장 + 조경 + 결함 수정 (수 분)"),
    ("audit:scan", "결함 검사", "겹침·부유물·관통 도로·끊긴 난간·고아 구조물 개수 보기"),
    ("audit:fix", "결함 검사 + 자동 수정", "찾은 결함을 고침"),
    ("refresh_map", "지도 갱신", "톱뷰 지도(Screenshots/map_plan.svg)를 다시 그려 엶 (수 분)"),
    ("save", "레벨 저장", "변경된 레벨·애셋 저장"),
]


def _add(menu, section, name, label, tip):
    e = CKMenuAction()
    e.init_entry(OWNER, menu.menu_name, section, name, label, tip)
    menu.add_menu_entry_object(e)
    _KEEP.append(e)


def _populate(menu):
    for group, title in (("주택", "건물 배치 - 주택 (뷰포트 가운데에 놓임)"), ("대형", "건물 배치 - 대형 건물"), ("첨탑", "건물 배치 - 첨탑 (드물게)")):
        menu.add_section("CK_" + group, title)
        for mesh, label, g in ck_tools.BUILDINGS:
            if g == group:
                _add(menu, "CK_" + group, "place:" + mesh, label, "SM_Bldg_%s 를 뷰포트가 보는 지면에 배치" % mesh)
    menu.add_section("CK_Edit", "선택한 건물 편집")
    for name, label, tip in EDIT:
        _add(menu, "CK_Edit", name, label, tip)
    menu.add_section("CK_Level", "레벨")
    for name, label, tip in LEVEL:
        _add(menu, "CK_Level", name, label, tip)


def register():
    tm = unreal.ToolMenus.get()
    tm.unregister_owner_by_name(OWNER)
    _KEEP.clear()
    # toolbar combo button
    tb = tm.extend_menu("LevelEditor.LevelEditorToolBar.User")
    tb.add_section("CKTools", "CK")
    btn = unreal.ToolMenuEntry(name="CKBuild", type=unreal.MultiBlockType.TOOL_BAR_COMBO_BUTTON)
    btn.set_label("CK 건축")
    btn.set_tool_tip("Crystal Kingdom 건축물 배치·편집 도구")
    btn.set_icon("EditorStyle", "LevelEditor.Tabs.Viewports")
    tb.add_menu_entry("CKTools", btn)
    name = "LevelEditor.LevelEditorToolBar.User.CKBuild"
    sub = tm.find_menu(name) or tm.register_menu(name, "", unreal.MultiBoxType.MENU, False)
    _populate(sub)
    # main menu bar fallback
    main = tm.extend_menu("LevelEditor.MainMenu")
    mm = main.add_sub_menu(OWNER, "", "CKMenu", "CK 건축", "Crystal Kingdom 건축물 도구")
    _populate(mm)
    tm.refresh_all_widgets()
    unreal.log("[CK] 'CK 건축' 툴바·메뉴 등록 완료 (%d 항목)" % len(_KEEP))


if __name__ == "__main__":
    register()
