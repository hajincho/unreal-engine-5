# PROGRESS — Crystal Kingdom

마지막 갱신: 2026-11-09. 브랜치 `crystal-kingdom`.

| # | 단계 | 상태 | 핵심 파일 |
|---|---|---|---|
| 1 | 개발 환경 점검 · 프로젝트 생성 | 완료 | `CrystalKingdom.uproject`, `Config/*.ini`, `Tools/ue_remote.py`, `Tools/uer.ps1` |
| 2 | 레퍼런스 분석 · 배치도 | 완료 | `PROJECT_PLAN.md` |
| 3 | 공간 배치 · 카메라 | 완료 | `Scripts/Unreal/ck_build_level.py` (`CAMERAS`, `PLATEAUS`, `ARCH`, `LANDMARKS`) |
| 4 | 동굴 기본 구조 | 완료 | `SourceArt/Blender/gen_cave.py` → 셸 32청크 + 바닥 12청크 |
| 5 | 수정 모델링 | 완료 | `SourceArt/Blender/gen_crystals.py` → 13유형 58메시 |
| 6 | 건축물 외관 | 완료 | `SourceArt/Blender/gen_architecture.py` → 모듈 23 + 완성 건물 14 |
| 7 | 호수 | 완료 | `M_Water` (Single Layer Water), `CK_Lake` |
| 8 | 재질 · 조명 | 완료 | `Scripts/Unreal/ck_materials.py`, `ck_build_level.py` (`build_lighting`) |
| 9 | 세부 장식 | 완료(기본) | `gen_props.py`, 암석·잔해·수중 암석·바닥 산포 |
| 10 | 렌더 · 원본 비교 | 완료 | `Screenshots/iter01…iter10, final_reference.png`, `compare_reference_iterations.png` |
| 11 | 품질 개선 반복 | 11회 수행 | `VALIDATION.md` 반복 기록 |
| 12 | 최적화 · 최종 검증 | 부분 완료 | 측정만 완료, PCG/ISM 전환·LOD 튜닝은 미수행 (`NEXT_STEPS.md`) |
| 13 | 재질 사실감 패스 | 완료(차이 남음) | `gen_textures.py`, `gen_crystals.py`(베벨), `ck_materials.py`, `Screenshots/mat01…mat10`, `compare_material_pass.png` |

## 작업 로그 (요약)
1. UE 5.8.4 / Blender 5.2.3 / RTX 2060 6GB 확인. 빈 블루프린트 프로젝트 생성, Lumen·Nanite·VSM·Python 원격 실행 설정.
2. Python 원격 실행 클라이언트(`Tools/ue_remote.py`) 작성 → 실행 중 에디터에 스크립트 전송.
3. Blender 헤드리스 생성기 작성: 텍스처(numpy FFT/Worley), 수정, 암석, 동굴, 건축, 소품.
   - 문제: 초타원체 매개변수가 중앙부·천장 정점을 희소하게 만들어 면이 26–64 m로 커짐 → X 균일 + 단면 호 길이 균일 샘플링으로 수정.
   - 문제: 대성당 충돌 헐 639개 → 닫힌 건물은 박스 1개, 보행 구조만 세부 UCX로 단순화.
4. FBX → UE Interchange 임포트. 문제: 일괄 작업이 비동기로 처리됨 / Play 모드에서 거부 → 파일 단위 임포트, PIE 종료.
   - 확인: Blender→FBX→UE에서 Y축 반전(UE y = −Blender y). 건물 정면은 로컬 +Y.
5. 머티리얼 생성(커스텀 HLSL 노드 포함), 메시 176개에 슬롯 이름 기준 자동 지정.
6. 레벨 조립: 레이트레이스로 천장·벽·바닥 표면에 수정 배치(재현 가능한 시드 4242).
7. 렌더 반복(뷰포트 HighResShot):
   - 에디터가 백그라운드에서 CPU를 제한 → `Config/DefaultEditorSettings.ini`로 해제.
   - 셸 뒷면 그림자 누락으로 햇빛 누수 → 암석 머티리얼 양면.
   - 원거리 VSM 누수(북쪽 벽 점선) → Directional Light 끄고 채광구 스포트라이트로 광선 구현.
   - 호수 평면 충돌 때문에 산포 레이가 수면에 맞아 수정이 떠 있던 버그 → 호수 NoCollision 후 재배치.
8. 충돌 검증 12/12, 독립 실행 성능 측정(1080p/1440p).
9. 재질 사실감 패스 (2026-11-09, 렌더 10회 반복 `mat01…mat10`):
   - 텍스처 재생성: 수정 = 도메인 워프한 열린 균열망(닫힌 보로노이 셀 제거) + 우윳빛 구름 + 오팔 패치 필드, 암석 = 능선·워프 층리·드문 균열(자갈 무늬 제거).
   - 수정 메시 58종에 베벨(인접 모서리의 7%, 2분할, Harden Normals) → 모서리 하이라이트.
   - `M_Crystal_Master` 재작성: Clear Coat, 오팔 팔레트(보라·파랑·청록·분홍·금), 시차 2층 내부, 거리 페이드, 크랙클 균열.
   - 문제: Python `MaterialProperty`에 ClearCoat 핀이 없음 → `MakeMaterialAttributes` 경유.
   - 문제: `delete_all_material_expressions`가 노드를 남겨 물에 SLW 출력 노드가 3개 쌓임 → 컴파일 실패로 수면이 사라짐. 남은 노드를 하나씩 지우도록 수정.
   - 성능 재측정: 1080p 네이티브 GPU +1.6 ms (`VALIDATION.md` 4절).
