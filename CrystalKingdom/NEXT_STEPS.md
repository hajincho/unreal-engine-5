# NEXT_STEPS — Crystal Kingdom

## 세션 복구 방법
1. 에디터 실행: `UnrealEditor.exe "F:/언리얼/unreal-engine-5/CrystalKingdom/CrystalKingdom.uproject"` (시작 맵 CK_Main, Python 원격 실행 켜짐).
2. 원격 명령: `& Tools\uer.ps1 <script.py> key=value` 또는 `& Tools\uer.ps1 -c "<python>"`.
3. 레벨 재조립: `ck_build_level.py stage=world` (전체 삭제 후 재생성 → 이어서 `crystals`, `lighting`, `cameras` 단계를 모두 실행).
4. 렌더: `& Tools\shot.ps1 CAM_Reference <이름> 20` → `Screenshots/<이름>.png`.
5. 주의: 작업용 에디터에서 Play(PIE)를 켜 두면 임포트가 거부됩니다. Interchange 임포트는 파일 단위로 실행합니다 (일괄 처리는 비동기).
6. 머티리얼 일부만 다시 빌드: `ck_materials.py only=crystal|rock|stone|water|simple`. 빌드 직후에는 셰이더가 컴파일 중이므로 20–40초 기다린 뒤 렌더합니다. 컴파일 확인은 `MaterialEditingLibrary.get_statistics(m).num_pixel_shader_instructions` > 0 으로 합니다.

## 우선순위 높은 개선
1. **재질 사실감 (1차 패스 완료, 2026-11-09)**: 베벨, 오팔 팔레트, Clear Coat, 크랙클 균열, 시차 2층, 거리 페이드까지 반영했습니다. 남은 것은 다음과 같습니다.
   - 깊은 투명감·굴절: 지금은 불투명 셰이딩입니다. 근경 히어로 수정만 `M_Crystal_Glass` 또는 Substrate로 교체를 시험합니다 (반투명은 비Nanite이고 비용이 큼).
   - 모서리 칩·패각상 파단면 지오메트리: 베벨만 있고 깨진 자국은 없습니다.
   - 하이키 색감: 레퍼런스는 금색 반사와 흰 하이라이트가 강합니다. 조명 색온도와 노출을 함께 조정해야 합니다.
2. **수정 절벽 밀도**: 레퍼런스는 건물이 수정 절벽에 박혀 있습니다. ColumnMass를 건물 뒤·옆에 더 빽빽하게 두고, 로지아 좌우를 감싸는 맞춤 메시를 제작합니다.
3. **호수 색**: 바닥 퇴적층 색과 맑은 흡수 계수는 넣었지만, 물 몸체가 여전히 어둡습니다. SLW 산란은 사실상 햇빛(Directional)으로 밝혀지는데 이 동굴에는 햇빛이 없으므로, 호수 위 보조광을 늘리거나 얕은 물 Caustics(조명 함수)를 추가해야 합니다. 채광구 스포트가 바닥에 만드는 흰 빛 웅덩이도 원뿔·감쇠 조정이 필요합니다.
4. **천장 가독성**: 천장 암반의 형태가 보이도록 보조광과 머티리얼 대비를 높이고, 천장 수정을 더 굵고 짧게 만듭니다.
5. **구도 미세 조정**: 레퍼런스는 다리가 화면에서 더 넓습니다 (다리를 카메라 쪽으로 약 30 m 당기거나 초점거리 22–24 mm).

## 최적화 (미수행)
- 산포 액터 약 900개 → PCG 그래프 또는 HISM으로 전환 (PCG 플러그인은 이미 활성화됨). 지금은 Python 레이트레이스 배치(시드 고정) 방식입니다.
- Cinematic / Optimized 프로필: 콘솔 변수 프리셋(`r.ScreenPercentage`, Lumen 품질, 볼류메트릭 포그 그리드)을 블루프린트나 DeviceProfile로 분리.
- 그림자 비용: 스포트 광선 5개 중 그림자가 필요한 것은 주 광선뿐입니다.
- 반투명 수정은 비Nanite이므로 개수를 제한해 유지합니다.

## 캐릭터 · 실내 개발 준비
- 동선: 남쪽 기슭 → 대계단 → 로지아 1층 회랑·지붕 → 다리 서단(홀) → 다리 → 동쪽 마을 단구 → 광장 계단.
- 계단 18/32 cm, 통로·다리 폭 ≥ 4 m, 난간 1.1 m. 닫힌 건물은 박스 충돌이라 실내를 만들 때는 해당 건물의 충돌을 세부 UCX로 다시 만들어야 합니다 (`gen_architecture.box_building`).
- 호수 수면은 충돌이 없습니다. 수영이나 물 경계는 별도 볼륨(Physics/Water Volume)으로 정의합니다.
- 자유 비행 폰에 속도 조절·카메라 복귀 입력이 필요하면 Enhanced Input 기반 블루프린트나 C++ 폰을 추가합니다 (경로에 한글이 있어 C++ 빌드 전 확인 필요).
