# ASSET_MANIFEST — Crystal Kingdom

모든 3D 에셋은 이 프로젝트의 스크립트로 직접 생성했습니다. 외부 에셋은 쓰지 않았고, 엔진 기본 에셋은 `/Engine/BasicShapes/Plane`(호수 평면) 하나만 사용했습니다.
재생성: `blender --background --factory-startup --python SourceArt/Blender/<gen_*.py>` → `Tools/uer.ps1 Scripts/Unreal/ck_import.py …`

## 메시 (Content/CrystalKingdom/Meshes)
| 폴더 | 수 | 에셋 | 생성기 |
|---|---|---|---|
| Cave | 44 | `SM_Cave_Shell_00…31` (벽·천장, 채광구 3개), `SM_Cave_Floor_00…11` (호수 분지 지형) | `gen_cave.py` |
| Crystals | 58 | CeilingGiant×5, FloorGiant×4, Pillar×5, Leaning×4, Branch×4, Wall×4, FloorCluster×5, Broken×4, Glow×3(반투명·비Nanite), Opal×3, ColumnMass×6(빽빽한 기둥 군집), Block×5(전경 블록), Shard×6 | `gen_crystals.py` |
| Rocks | 27 | Boulder×6, Cliff×4, Plateau×6(평평한 보행 단구), Submerged×3, Rubble×4, CeilingSpike×4 | `gen_rocks.py` |
| Architecture (모듈) | 23 | Wall_Plain, Wall_Deco, Window_Rect, Window_Gothic, Window_Rose, Portal(닫힌 문), Column, Capital, Stairs_Straight, Stairs_Curved, Balustrade, Balcony, Bridge_Span, Arcade(회랑), Gallery(외부 복도), Spire, Roof_Gable, Roof_Cone, Roof_Dome, Deco_Finial, Deco_Pinnacle, Deco_Crenel, Deco_Buttress | `gen_architecture.py` |
| Architecture (완성 건물) | 14 | Bldg_Loggia, Bldg_Hall, Bldg_TowerRound, Bldg_TowerSquare, Bldg_Cathedral, Bldg_House_01…06, Bridge_Grand(아치 4개, 77.5 m + 정자), Bldg_Plaza, Bldg_StairGrand | `gen_architecture.py` |
| Props | 10 | ColumnBroken×3, StoneDebris×3, OrnamentBroken×2, GlowMotes×2(WPO 부유 입자, 비Nanite) | `gen_props.py` |

정점 색: R = 조각 난수, G = 성장축 0→1, B = 결정면 단위 난수(셰이더 변화용).
수정 메시는 Blender Bevel 모디파이어(인접 모서리 길이의 7%, 2분할, 28° 이상 모서리, Harden Normals)로 모서리를 깎아 하이라이트가 맺힙니다 (메시당 350–35,500 삼각형).
충돌: 건축은 FBX `UCX_` 볼록 헐(닫힌 건물 = 박스 1개, 회랑·다리·계단·광장 = 세부 헐), 동굴·암석·바닥 수정은 Complex-as-Simple, 천장 수정은 충돌 없음.

## 머티리얼 (Content/CrystalKingdom/Materials)
| 마스터 | 내용 |
|---|---|
| M_Crystal_Master | 불투명 수정, Clear Coat(우윳빛 바탕 + 유리 코팅). 오팔 팔레트 간섭색(패치 필드·결정면·조각·시야각), 크랙클 금갈색 균열, BumpOffset 시차 2층(내부 균열·내부 오팔), 거리 페이드(원경 타일 반짝임 제거), 림·내부 발광 |
| M_Crystal_Glass | 반투명 굴절(IOR 1.45) 히어로 수정. Surface 반투명 조명 |
| M_Rock_Master | 양면. 매크로 변화(월드 좌표), 균열 어둡게, 물가 젖음 띠, 수면 아래는 밝은 퇴적층 색(맑은 물로 바닥이 비침) |
| M_Stone_Master | 석조 블록 색 변화, 줄눈, 오염, 물가 청록 착색 |
| M_Water | Single Layer Water, 2층 흐르는 잔물결 노멀, 산란·흡수 계수 |
| M_WindowGlow / M_Door / M_GlowMote | 창문 발광, 닫힌 문, 가산 부유 입자 |

인스턴스 13개: MI_Crystal_Teal / White / Violet / Glow / Opal / Glass / Block / BlockViolet, MI_CaveRock, MI_Rock, MI_Stone, MI_StoneTrim, MI_Roof

## 텍스처 (Content/CrystalKingdom/Textures, 원본 SourceArt/Textures)
T_Rock_N/M(능선·워프 층리·드문 균열), T_Crystal_M(R 크랙클 균열망, G 우윳빛 구름, B 오팔 패치 필드), T_Crystal_N(패각상 물결·성장 줄무늬·균열 홈), T_Water_N, T_Stone_N/M(2 m 석조 블록 타일). 모두 numpy로 생성했고 이음매 없이 반복됩니다.

## 레벨 · 블루프린트
- `Maps/CK_Main` — 액터 약 1,030개: 동굴 44, 단구 9, 건물 23, 수정 랜드마크 18, 천장 수정 106, 벽 수정 170, 바닥 수정·암석 420, 전경 33, 천장 암석 40, 해안 암석 90, 수중 암석 21, 조명 47, 카메라 6 + PlayerStart
- `Blueprints/BP_CK_FlyGameMode`, `BP_CK_FlyPawn`(SpectatorPawn 기반, 메시 없음)
- `Cameras/RT_Capture`(SceneCapture 백업 렌더용)

## Blender 소스 (SourceArt/Blender)
`CK_Crystals.blend`, `CK_Rocks.blend`, `CK_Cave.blend`, `CK_Architecture.blend`, `CK_Props.blend` + 생성기 `ck_common.py`, `gen_*.py`, 미리보기 `preview.py`. FBX 출력은 `SourceArt/Export/<분류>/`.

## 자동화 스크립트
| 파일 | 역할 |
|---|---|
| Tools/ue_remote.py, Tools/uer.ps1 | 실행 중 에디터에 Python 전송 (Remote Execution) |
| Tools/shot.ps1 / Scripts/Unreal/ck_shot.py | 시네 카메라로 뷰포트 이동 → HighResShot |
| Scripts/Unreal/ck_capture.py | SceneCapture2D 백업 렌더 |
| Scripts/Unreal/ck_import.py | 폴더 생성, 텍스처·FBX 임포트(Nanite/충돌 옵션) |
| Scripts/Unreal/ck_materials.py | 마스터·인스턴스 생성, 슬롯 자동 지정 |
| Scripts/Unreal/ck_build_level.py, ck_level_common.py | 레벨 조립(`stage=world|crystals|lighting|cameras`) |
| Scripts/Unreal/ck_validate_collision.py | 보행 표면 충돌 검증 |
| Tools/perf.ps1, Tools/csvstats.py | 독립 실행 CSV 프로파일 측정·요약 |
| Tools/compare_sheet.ps1 | 레퍼런스·이전·이후 비교 시트(전체 + 같은 영역 확대) |
