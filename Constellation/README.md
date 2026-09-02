# Constellation: 스마트폰 밤하늘 인식 파이프라인

스마트폰 밤하늘 사진에서 별 후보를 찾고, 사진이 실제 하늘의 어느 방향인지 계산한 뒤,
포함된 별자리와 주요 천체를 표시하는 프로젝트입니다.

이미지 모양만 분류하지 않습니다. 영상처리, 별 그래프, 천문 카탈로그, Astrometry.net
Plate Solving, WCS 검증과 YOLO 딥러닝을 함께 사용합니다. 근거가 부족하면 별자리 이름을
억지로 반환하지 않고 실패 또는 불확실 상태로 처리합니다.

## 현재 상태

2026년 9월 2일 기준입니다.

| 영역 | 현재 상태 |
|---|---|
| 사진 한 장의 규칙 기반 인식 | 별 검출 → 그래프 매칭 → WCS 검증 → 별자리 오버레이 구현 완료 |
| 로컬 Plate Solving | WSL2 Astrometry.net과 광각 인덱스 10개 사용 가능 |
| 웹 사진 수집 | Wikimedia, Openverse, Zenodo, Hugging Face 통합 수집기 구현 |
| TargetedWeb 수집 | 이미지 207장, 메타데이터 275행, 대형 데이터셋 후보 213행 |
| TargetedWeb 분류 | 스마트폰 후보 79장, 기기 불명 밤하늘 32장, 실패 후보 10장 |
| TargetedWeb WCS | 대상 111장 중 성공 1장, 실패 10장, 미처리 100장 |
| YOLO 데이터 | MobilTelesco + Openverse + AstroSmartphone, 총 1,397장 |
| 최신 YOLO 테스트 | Precision 0.832, Recall 0.828, mAP50 0.786, mAP50-95 0.293 |
| 가장 부족한 클래스 | Hassaleh, Bellatrix, Aldebaran |

현재 YOLO 모델은 88개 별자리 전체를 분류하는 모델이 아닙니다. `Pleiades`, `Jupiter`,
`Betelgeuse`, `Aldebaran`, `Zeta Tauri`, `Elnath`, `Hassaleh`, `Bellatrix`의 8개 천체를
찾는 첫 객체 검출 모델입니다. 전체 별자리 판정은 WCS와 Stellarium 기반 파이프라인이
담당하고 YOLO는 이를 보조합니다.

## 전체 흐름

```text
기준 자료: 스마트폰 사진 + HYG/Gaia + IAU 경계 + Stellarium 연결선

사진 한 장 입력
  → 03 별 후보 검출
  → 04 Delaunay 별 그래프
  → 05 Stellarium 구조 매칭
  → 07 Astrometry.net Plate Solving
  → 06 WCS·HYG·Gaia 검증
  → 08 최종 판정
  → 11 별자리 연결선 오버레이

딥러닝 데이터
  → 20 매니페스트와 세션 분할
  → 21 YOLO 데이터 생성
  → 22 YOLO11n 학습
  → 23 독립 테스트 평가
  → 24 오답 분석
  → 29~33 AstroSmartphone 보강
  → 34~36 웹 데이터 수집·분류·Plate Solving
  → 37 WCS 라벨 생성 및 재학습(다음 단계)
```

## 프로젝트 구조

```text
star-predict-system/
├─ README.md                         저장소 소개
├─ front/                            React 사용자 화면
└─ Constellation/
   ├─ .env                           API 키, Git 커밋 금지
   ├─ .env.example                   환경변수 예시
   ├─ requirements.txt               Python 패키지
   ├─ README.md                      현재 문서
   ├─ 용어설명.md                    천문·영상처리·평가 용어
   ├─ scripts/                       01~36 처리 프로그램
   ├─ data/
   │  ├─ photo/                      원본·외부 사진
   │  ├─ reference/                  별 카탈로그·경계·연결선
   │  ├─ processed/                  전처리·YOLO 데이터
   │  ├─ results/                    CSV·JSON·평가·시각화
   │  ├─ evaluation/                 정답 평가셋
   │  └─ wcs/                        .wcs·.new·.corr
   └─ HYG-Database-main/             HYG 원본
```

### 데이터 폴더

| 경로 | 내용 |
|---|---|
| `data/photo/AstroSmartphoneDataset` | Pixel 기종으로 촬영한 실제 스마트폰 밤하늘 |
| `data/photo/MobilTelesco` | 8개 천체가 표시된 대규모 촬영 데이터 |
| `data/photo/smartphone` | 직접 받거나 사용 허가를 받은 스마트폰 사진 |
| `data/photo/WikimediaCommons` | 기존 Wikimedia 수집 자료 |
| `data/photo/Openverse` | 기존 Openverse 수집 자료 |
| `data/photo/TargetedWeb` | 34번 통합 수집 자료 |
| `data/photo/SWINSEG` | 하늘 영역 분할 참고 데이터 |
| `data/reference` | Gaia, 별자리 경계, Stellarium 기준 자료 |
| `data/processed` | YOLO 이미지·라벨·`dataset.yaml` |
| `data/results` | 단계별 결과와 모델 평가 |
| `data/wcs` | Plate Solving 산출물 |

대용량 데이터, 개인 사진, GPS, `.env`, WCS 산출물과 모델 가중치는 `.gitignore`로
제외합니다. GitHub에는 코드, 문서와 설정 예시만 올립니다.

## Python 파일의 역할

### 01~14: 기본 인식과 평가

| 번호 | 파일 | 역할 |
|---:|---|---|
| 01 | `01_dataset_inspection.py` | 크기, 밝기, EXIF, 결측값과 촬영 세션 조사 |
| 02 | `02_reference_validation.py` | HYG, Gaia, 경계, Stellarium 검증 |
| 03 | `03_star_detection.py` | DoG와 NMS로 별 후보 검출 |
| 04 | `04_star_graph.py` | Delaunay 삼각분할로 별 그래프 생성 |
| 05 | `05_graph_matching.py` | 관측 그래프와 Stellarium 패턴 비교 |
| 06 | `06_match_validation.py` | WCS와 HYG/Gaia 재투영으로 후보 검증 |
| 07 | `07_plate_solving.py` | 로컬 또는 Nova로 WCS 생성·캐시 |
| 08 | `08_final_recognition.py` | 성공·불확실·실패와 사유 결정 |
| 09 | `09_batch_evaluation.py` | 여러 사진 일괄 평가 |
| 10 | `10_end_to_end_pipeline.py` | 사진 한 장 전체 인식 자동 실행 |
| 11 | `11_wcs_constellation_overlay.py` | 별자리 선을 사진에 표시 |
| 12 | `12_build_ground_truth_evaluation.py` | 현재 자료로 정답 평가셋 생성 |
| 13 | `13_evaluate_ground_truth_set.py` | 정답과 예측 비교 |
| 14 | `14_error_analysis.py` | 누락·오검출·WCS 실패 분석 |

### 15~24: 새 사진과 YOLO

| 번호 | 파일 | 역할 |
|---:|---|---|
| 15 | `15_prepare_uploaded_photos.py` | 새 스마트폰 사진 EXIF·품질 조사 |
| 16 | `16_batch_label_uploaded_photos.py` | 새 사진 일괄 WCS와 자동 라벨 |
| 17 | `17_local_plate_solver.py` | WSL solver와 인덱스 설치·점검 |
| 18 | `18_collect_wikimedia_images.py` | Wikimedia 사진·출처·라이선스 수집 |
| 19 | `19_classify_wikimedia_images.py` | Wikimedia 사진 분류 |
| 20 | `20_prepare_mobiltelesco_manifest.py` | JPG/DNG, DARKS, Skymap, 중복과 세션 구분 |
| 21 | `21_prepare_yolo_dataset.py` | 세션 누수 없는 YOLO train/val/test 생성 |
| 22 | `22_train_yolo.py` | YOLO11n 전이학습과 체크포인트 저장 |
| 23 | `23_evaluate_yolo.py` | Precision, Recall, mAP 계산 |
| 24 | `24_yolo_error_analysis.py` | 사진·클래스별 TP, FP, FN 분석 |

### 25~36: 데이터 확장

| 번호 | 파일 | 역할 |
|---:|---|---|
| 25 | `25_convert_sidd_mat_to_png.py` | SIDD `.mat`을 PNG로 변환 |
| 26 | `26_classify_openverse_images.py` | Openverse 품질·기기·중복 분류 |
| 27 | `27_label_openverse_with_wcs.py` | WCS 기반 Openverse YOLO 라벨 후보 |
| 28 | `28_merge_openverse_yolo_dataset.py` | Openverse 라벨 병합 |
| 29 | `29_inventory_existing_target_coverage.py` | AstroSmartphone 대표 세션과 천체 후보 조사 |
| 30 | `30_batch_plate_solve_sessions.py` | 대표 사진 재시작 가능 Plate Solving |
| 31 | `31_analyze_target_coverage.py` | WCS로 천체 포함 여부 계산 |
| 32 | `32_review_target_labels.py` | 천체 라벨 검토 CSV와 contact sheet |
| 33 | `33_merge_astro_smartphone_yolo_dataset.py` | 승인 라벨·음성을 YOLO에 병합 |
| 34 | `34_collect_targeted_web_images.py` | 네 공급처 통합 수집 |
| 35 | `35_classify_targeted_web_images.py` | 통합 웹 사진 기기·품질·중복 분류 |
| 36 | `36_plate_solve_targeted_images.py` | 유효 웹 사진 로컬 Plate Solving |

`convert_gaia_votable.py`와 `convert_vizier_boundaries.py`는 받은 VOTable/TSV를 CSV로
바꿉니다. `scripts/lib`에는 CSV·JSON·WSL 공통 기능이 있습니다.

## 사진 인식 원리

1. **별 검출:** 서로 다른 Gaussian blur의 차이인 DoG로 작은 점광원을 강조하고,
   MAD로 배경 노이즈를 추정하며 NMS로 중복점을 줄입니다.
2. **그래프:** Delaunay 삼각형의 변 길이 비율과 각도를 만들어 회전·크기 변화에 강한
   별 배치 특징을 얻습니다.
3. **후보 매칭:** HYG 좌표와 Stellarium HIP 연결선을 합친 기준 그래프와 비교합니다.
   이 결과는 후보일 뿐 최종 확정이 아닙니다.
4. **Plate Solving:** Astrometry.net 인덱스로 중심 RA/DEC, 화각, 회전, 픽셀 스케일과
   WCS를 구합니다. 성공 결과는 캐시합니다.
5. **검증·표시:** Gaia/HYG를 사진에 재투영해 오차를 확인하고, 통과하면 Stellarium
   연결선을 사진 위에 표시합니다. 광각 사진은 여러 별자리를 반환할 수 있습니다.

## 데이터 정리 원칙

- 필수 좌표·경로·클래스가 없으면 해당 계산에서 제외합니다.
- GPS·촬영시간·EXIF가 없다고 임의의 값으로 채우지 않습니다.
- EXIF가 없는 사진은 `device_unknown`으로 분리합니다.
- SHA-256으로 완전 중복, perceptual hash로 유사 이미지를 검사합니다.
- 연속 촬영은 같은 세션으로 묶고 같은 세션이 train과 test에 섞이지 않게 합니다.
- 외부 사진은 원본 URL, 저작자와 라이선스를 CSV에 보존합니다.
- 대형 ZIP은 자동으로 받지 않고 후보 CSV에서 먼저 검토합니다.
- API Secret과 GPS는 GitHub에 올리지 않습니다.

## 데이터 출처

| 자료 | 의미와 용도 |
|---|---|
| [AstroSmartphoneDataset](https://github.com/oparisot/AstroSmartphoneDataset) | Pixel 스마트폰 실제 밤하늘, WCS·평가 보강 |
| MobilTelesco | 반복 촬영된 하늘과 8개 천체 라벨, YOLO 기본 학습 |
| [Wikimedia Commons](https://commons.wikimedia.org/) | CC/퍼블릭 도메인 환경·음성 사진 |
| [Openverse](https://openverse.org/) | 공개 플랫폼의 오픈 라이선스 검색 인덱스 |
| [Zenodo](https://zenodo.org/) | 공개 연구 데이터와 개별 이미지 |
| [Hugging Face Datasets](https://huggingface.co/datasets) | 추가 ML 데이터셋 후보 |
| SWINSEG | 낮·밤 하늘 segmentation 참고 |
| SIDD / LICAM | 스마트폰 저조도·노이즈 전처리 참고 |
| [HYG](https://github.com/astronexus/HYG-Database) | HIP 연결선과 밝은 별 좌표 |
| [Gaia DR3](https://www.cosmos.esa.int/web/gaia/data-access) | 고정밀 별 위치·밝기·색상, WCS 검증 |
| [VizieR VI/49](https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=VI%2F49) | J2000 IAU 별자리 경계 |
| [Stellarium Sky Cultures](https://github.com/Stellarium/stellarium-skycultures) | Western 연결선과 오버레이 |
| [Astrometry.net](https://astrometry.net/) | 별 배열 기반 WCS 생성 |

## YOLO 최신 결과

33번 병합 후 데이터는 train 954장, validation 200장, test 243장으로 총 1,397장입니다.
AstroSmartphone 양성 19장과 WCS 음성 182장을 추가했고 세션 분할 누수는 0건입니다.

최신 모델은 `mobiltelesco_openverse_astro8_yolo11n/weights/best.pt`이며 GTX 1050 Ti에서
학습했습니다. 최대 30 epoch 중 Early Stopping으로 11 epoch에서 종료됐습니다.

| 지표 | 243장 테스트 |
|---|---:|
| Precision | 0.832 |
| Recall | 0.828 |
| mAP50 | 0.786 |
| mAP50-95 | 0.293 |

기존 199장 테스트에서도 새 모델은 Precision 0.832, Recall 0.831, mAP50 0.789,
mAP50-95 0.294로 이전 모델보다 개선됐습니다. 오답 분석은 TP 1,346, FP 875, FN
243입니다.

- Hassaleh: Recall 약 0.53, FN 92건으로 가장 부족
- Bellatrix: FP 143건
- Aldebaran: FP 149건
- mAP50-95가 낮아 정확한 박스 위치가 약함
- 독립 스마트폰 테스트의 양성 수가 적어 일반화 검증이 부족

## 34~36 웹 보강 현황

34번은 Wikimedia·Openverse의 허용 라이선스 이미지와 Zenodo·Hugging Face 후보를
수집합니다. SHA-256 중복검사를 하고 `TargetedWeb/metadata/sources.csv`에 출처를
보존합니다. 현재 이미지 207장과 메타데이터 275행입니다. 실패·라이선스 제외 기록도
남기기 때문에 메타데이터 행이 더 많습니다.

35번 분류 결과:

| 분류 | 수량 |
|---|---:|
| 스마트폰 밤하늘 후보 | 79 |
| 기기 불명 밤하늘 후보 | 32 |
| 실패·음성 후보 | 10 |
| 전문 카메라 | 19 |
| 망원경·심우주 | 6 |
| 저해상도 | 41 |
| 중복 | 19 |
| 무관 | 1 |

자동 분류는 학습 확정 라벨이 아닙니다. contact sheet를 보고 `review_label`을 입력해야
합니다.

36번은 유효 후보 111장을 외부 업로드 없이 로컬에서 풉니다. 현재 성공 1장, 실패
10장, 미처리 100장입니다. 웹 축소본은 별 신호가 약해 원본보다 성공률이 낮습니다.

## 설치

```powershell
cd D:\dev\star-predict-system\Constellation
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

```dotenv
ASTROMETRY_NET_API_KEY=Nova를_사용할_때만_입력
WIKIMEDIA_USER_AGENT=ConstellationResearch/1.0 (contact: your-email@example.com)
OPENVERSE_CLIENT_ID=발급받은_ID
OPENVERSE_CLIENT_SECRET=발급받은_SECRET
HF_TOKEN=필요한_경우만_입력
```

## 주요 실행 명령

로컬 solver 확인:

```powershell
.\.venv\Scripts\python.exe .\scripts\17_local_plate_solver.py --check
```

사진 한 장 전체 인식:

```powershell
.\.venv\Scripts\python.exe .\scripts\10_end_to_end_pipeline.py ".\data\photo\smartphone\사진.jpg"
```

YOLO 학습·평가:

```powershell
.\.venv\Scripts\python.exe .\scripts\22_train_yolo.py
.\.venv\Scripts\python.exe .\scripts\23_evaluate_yolo.py
.\.venv\Scripts\python.exe .\scripts\24_yolo_error_analysis.py
```

네 공급처 통합 수집:

```powershell
.\.venv\Scripts\python.exe .\scripts\34_collect_targeted_web_images.py --provider wikimedia --provider openverse --provider zenodo --provider huggingface --limit-per-provider 100 --results-per-query 30 --pause-seconds 2
```

수집 사진 분류:

```powershell
.\.venv\Scripts\python.exe .\scripts\35_classify_targeted_web_images.py
```

36번 빠른 1차 처리:

```powershell
.\.venv\Scripts\python.exe .\scripts\36_plate_solve_targeted_images.py --timeout-seconds 90
```

실패 재시도:

```powershell
.\.venv\Scripts\python.exe .\scripts\36_plate_solve_targeted_images.py --retry-failed --timeout-seconds 180 --no-position-hints
```

## 주요 상태와 변수

| 항목 | 의미 |
|---|---|
| `recognized` | WCS와 카탈로그 검증을 통과한 확정 결과 |
| `ambiguous` | 후보는 있지만 확정 근거 부족 |
| `too_few_stars` | 별 후보가 너무 적음 |
| `cloudy` | 구름·낮은 대비로 구조가 불충분 |
| `plate_solve_failed` | 제한 시간 안에 WCS를 찾지 못함 |
| `ra`, `dec` | 천구의 적경·적위 |
| `latitude`, `longitude` | 지구의 촬영 위도·경도 |
| `WCS` | 픽셀과 천구 좌표의 변환식 |
| `pixscale` | 픽셀 하나의 하늘 각도, arcsec/pixel |
| `orientation` | 천구 기준 사진 회전각 |
| `Precision` | 예측 객체 중 정답 비율 |
| `Recall` | 실제 정답 중 검출한 비율 |
| `mAP50` | IoU 0.5 기준 평균 검출 성능 |
| `mAP50-95` | 더 엄격한 여러 IoU 기준 평균 |

자세한 정의는 [용어설명.md](용어설명.md)를 참고합니다.

## 한계와 다음 작업

현재 규칙 기반 MVP와 8개 천체 YOLO는 동작하지만 범용 별자리 인식기의 완성 상태는
아닙니다.

1. 36번 미처리 웹 후보 100장 Plate Solving
2. 성공 WCS로 8개 천체를 투영하는 `37_prepare_targeted_yolo_dataset.py` 구현
3. 오버레이를 검토하고 승인된 라벨만 병합
4. Hassaleh, Bellatrix, Aldebaran 양성과 음성 사진 보강
5. 촬영자·세션·출처가 분리된 스마트폰 Test 100~300장 확보
6. 고정 박스 대신 화각과 천체 특성에 따른 박스 계산
7. 기존 테스트와 새 독립 Test에서 보강 모델 비교
8. 최종 모델을 사진 한 장 파이프라인과 프론트에 연결

Plate Solving 성공, 점광원 검증, 라이선스와 사람의 오버레이 검토를 모두 통과한 자료만
정답 라벨로 사용합니다.
