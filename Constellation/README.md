# Constellation Recognition Pipeline

스마트폰으로 촬영한 밤하늘 사진에서 별 후보를 찾고, 별 사이의 기하 구조와 실제 천문
카탈로그를 비교한 뒤, Plate Solving으로 얻은 WCS를 사용해 사진에 포함된 별자리를
검증하고 표시하는 프로젝트입니다.

현재 구현은 학습된 딥러닝 모델 하나가 사진을 직접 분류하는 방식이 아닙니다. OpenCV
영상처리, Delaunay 그래프, Stellarium 별자리 연결선, HYG/Gaia 별 카탈로그,
Astrometry.net Plate Solving을 결합한 설명 가능한 인식 파이프라인입니다. 이후 실제
스마트폰 사진이 충분히 확보되면 별 검출과 실패 사진 판정 부분에 머신러닝·딥러닝
모델을 추가할 계획입니다.

## 1. 프로젝트 구조

```text
Constellation/
├─ .env                         Nova Astrometry.net API 키(커밋 금지)
├─ .env.example                 API 키 설정 예시
├─ .gitignore                   GitHub에서 제외할 데이터와 비밀정보 규칙
├─ requirements.txt             Python 패키지 목록
├─ README.md                    프로젝트 설명서
├─ HYG-Database-main/           HYG 별 카탈로그
├─ data/
│  ├─ photo/                    사진 데이터셋 통합 보관 위치
│  │  ├─ AstroSmartphoneDataset/
│  │  ├─ MobilTelesco/
│  │  ├─ smartphone/            직접 업로드한 스마트폰 원본 사진
│  │  ├─ WikimediaCommons/
│  │  └─ ConstellationDataset/
│  ├─ reference/                변환·정리한 천문 기준 데이터
│  │  ├─ gaia_dr3_g10.csv       Gaia DR3의 밝은 별 목록
│  │  ├─ constellation_boundaries_j2000.csv
│  │  └─ stellarium/western/    Western 별자리 연결선과 설명
│  ├─ sample/                   재현 가능한 분석 표본 목록
│  ├─ processed/                전처리된 중간 데이터
│  ├─ evaluation/               정답 평가셋 매니페스트
│  ├─ results/                  단계별 CSV·JSON·시각화 결과
│  └─ wcs/                      Plate Solving 결과 파일
├─ notebooks/                   탐색 분석용 노트북 공간
└─ scripts/                     변환·분석·인식·평가 프로그램
```

대용량 원본 데이터, 개인 사진, GPS가 포함될 수 있는 평가 자료, 재생성 가능한 결과는
Git에 올리지 않습니다. GitHub에는 코드, 문서, 설정 예시만 올리는 것이 기본 원칙입니다.

### `data/` 하위 폴더의 의미

| 폴더 | 의미 |
|---|---|
| `data/photo` | 외부 데이터셋, 사용자가 받은 사진, Wikimedia 사진을 한곳에 보관 |
| `data/photo/smartphone` | 사용자가 촬영하거나 사용 허가를 받은 원본 사진 |
| `data/reference` | Gaia, VizieR, Stellarium 등에서 받은 기준 자료를 프로그램용으로 정리한 위치 |
| `data/results/star_detection` | 별 후보 좌표, 점수, 마스크, 주석 이미지 |
| `data/results/star_graph` | Delaunay 간선·삼각형과 그래프 이미지 |
| `data/results/graph_matching` | Stellarium 패턴 후보 순위와 선택 근거 |
| `data/results/match_validation` | WCS·HYG·Gaia 및 관측 조건 검증 결과 |
| `data/results/final_recognition` | 최종 상태, 별자리, 실패 코드 |
| `data/results/wcs_constellation_overlay` | 실제 천구 좌표로 투영한 별자리 오버레이 |
| `data/results/pipeline` | 사진 한 장의 전체 실행 로그와 요약 |
| `data/evaluation` | 정답 라벨, 장면 ID, 학습/검증/평가 분할 정보 |
| `data/wcs` | `.wcs`, `.new`, `.corr` 등 Astrometry.net 산출물 |

### Python 파일의 역할

| 파일 | 역할 |
|---|---|
| `01_dataset_inspection.py` | 스마트폰 데이터셋에서 층화 표본을 선택하고 크기·밝기·EXIF·결측 현황을 분석 |
| `02_reference_validation.py` | HYG, Gaia, 별자리 경계, Stellarium 파일의 존재·열·중복·결측값을 검사 |
| `03_star_detection.py` | DoG와 연결요소 분석으로 점 형태의 별 후보를 검출하고 근접 중복 후보 제거 |
| `04_star_graph.py` | 검출점 상위 후보를 Delaunay 삼각분할로 연결하고 지나치게 긴 간선을 제거 |
| `05_graph_matching.py` | 관측 그래프의 길이비·각도·연결 구조를 Stellarium Western 패턴과 비교 |
| `06_match_validation.py` | 구조 점수, EXIF 관측 조건, HYG/Gaia 좌표, WCS 재투영 오차로 후보 검증 |
| `07_plate_solving.py` | WSL 로컬 `solve-field` 또는 Nova API로 WCS를 생성하고 결과를 캐시 |
| `08_final_recognition.py` | 05·06단계 결과를 합쳐 확정·후보·실패 상태와 실패 코드를 생성 |
| `09_batch_evaluation.py` | 여러 매칭 결과를 일괄 검증하고 정답이 있으면 정확도 지표 계산 |
| `10_end_to_end_pipeline.py` | 사진 한 장으로 03→04→05→07→08→11을 자동 실행 |
| `11_wcs_constellation_overlay.py` | Stellarium 연결선을 WCS로 사진 위에 투영하여 복수 별자리를 인식·표시 |
| `12_build_ground_truth_evaluation.py` | 기존 스마트폰 데이터에서 강한 천문 검증을 통과한 정답 평가셋 생성 |
| `13_evaluate_ground_truth_set.py` | 정답 평가셋 전체를 실행하고 다중 라벨 Precision·Recall·F1 등을 계산 |
| `14_error_analysis.py` | 누락·과검출·Plate Solving 실패·라벨 충돌 등 오답 원인을 분류 |
| `15_prepare_uploaded_photos.py` | 새 스마트폰 사진의 EXIF·품질·별 개수를 조사하고 검토용 매니페스트 생성 |
| `16_batch_label_uploaded_photos.py` | 검토된 사진을 일괄 Plate Solving하여 재시작 가능한 자동 라벨셋 생성 |
| `17_local_plate_solver.py` | WSL Astrometry.net 설치 상태와 인덱스를 확인하고 로컬 풀이를 시험 |
| `18_collect_wikimedia_images.py` | Commons에서 스마트폰 사진을 검색·필터링·다운로드하고 출처 CSV 생성 |
| `19_classify_wikimedia_images.py` | Wikimedia 사진을 밤하늘·실패·비관련 대상으로 분류하고 검토용 시트를 생성 |
| `20_prepare_mobiltelesco_manifest.py` | MobilTelesco의 중복·JPG/DNG·라벨·세션을 분석하고 누수 없는 학습 분할 CSV를 생성 |
| `21_prepare_yolo_dataset.py` | 8클래스 매니페스트를 YOLO 폴더·라벨·dataset.yaml로 구성하고 클래스 분포와 누수를 검증 |
| `22_train_yolo.py` | CUDA/CPU 환경을 자동 선택해 YOLO11n을 학습하고 가중치·학습 지표·환경 정보를 저장 |
| `23_evaluate_yolo.py` | 보류한 테스트셋으로 전체·클래스별 Precision, Recall, mAP와 혼동행렬을 계산하고 보강 우선 클래스를 기록 |
| `24_yolo_error_analysis.py` | 테스트 사진별 미검출·오검출·클래스 혼동·위치 오차를 분해하고 오류 순위표와 시각화 이미지를 생성 |
| `convert_gaia_votable.py` | Gaia `.vot.gz` 조회 결과를 UTF-8 CSV로 변환 |
| `convert_vizier_boundaries.py` | VizieR 별자리 경계 TSV/VOTable을 일반 CSV로 변환 |
| `scripts/lib/io_utils.py` | CSV·JSON 읽기/쓰기 공통 함수 |
| `scripts/lib/wsl.py` | Windows 경로 변환과 WSL 명령 실행 공통 함수 |

## 2. 데이터 준비와 인식 작업 순서

### 2.1 데이터 수집

프로젝트는 서로 역할이 다른 데이터를 사용합니다.

1. 실제 스마트폰 밤하늘 사진을 수집합니다.
2. HYG와 Gaia에서 실제 별의 천구 좌표와 밝기를 준비합니다.
3. Stellarium에서 사람이 화면에 그리는 별자리 연결선 정보를 준비합니다.
4. VizieR/IAU 자료에서 별자리가 차지하는 공식 하늘 경계를 준비합니다.
5. Plate Solving과 카탈로그 검증으로 사진의 정답 라벨을 자동 생성합니다.
6. 구름, 흔들림, 광공해, 별 부족 사진도 실패 데이터로 보관합니다.

### 2.2 데이터 검사와 정리

`01_dataset_inspection.py`는 전체 이미지를 무작정 분석하지 않고 기기·해상도 폴더가
한쪽으로 치우치지 않도록 층화 표본을 만듭니다. 이미지별로 다음을 검사합니다.

- 파일을 정상적으로 열 수 있는지
- 가로·세로 픽셀과 색상 모드
- 파일 크기와 밝기 통계
- `DateTimeOriginal`, GPS, 제조사, 카메라 모델 등 EXIF 존재 여부
- 촬영 시간 또는 파일명으로 묶을 수 있는 연속 촬영 세션

`02_reference_validation.py`는 기준 CSV/JSON에 필요한 열이 있는지 확인하고 숫자 열을
숫자로 변환할 수 없는 값, 결측값, 범위를 벗어난 RA/DEC, 중복된 HIP/Gaia ID를
보고합니다. 결측값을 임의 평균으로 채우지 않습니다. 좌표나 ID처럼 핵심 정보가 없는
행은 매칭에서 제외하고, 선택 정보는 결측 상태로 유지해 데이터 왜곡을 막습니다.

이미지 중복은 두 종류로 다룹니다.

- `03`단계에서는 NMS와 최소 거리 조건으로 같은 별 주위의 중복 검출점을 제거합니다.
- 평가에서는 연속 촬영 프레임에 같은 `scene_id`를 부여합니다. 같은 장면이 학습셋과
  테스트셋에 동시에 들어가 성능이 부풀려지지 않도록 장면 단위로 분할해야 합니다.

완전히 동일하거나 리사이즈된 외부 사진을 찾는 perceptual hash 기반 중복 제거는 향후
외부 데이터 수집기에 추가해야 합니다.

### 2.3 현재 별자리 인식 알고리즘

```text
스마트폰 밤하늘 사진
  → 03 별 후보 검출
  → 04 Delaunay 별 그래프 생성
  → 05 HYG·Stellarium 구조 후보 매칭
  → 07 Astrometry.net Plate Solving 및 WCS 생성
  → 06 HYG·Gaia 재투영 검증
  → 08 최종 상태·실패 사유 결정
  → 11 사진 위 실제 별자리 연결선 표시
```

#### 별 후보 검출

사진을 회색조로 변환하고 서로 다른 크기의 Gaussian blur 차이인 DoG
(Difference of Gaussians)를 계산합니다. 주변보다 밝은 점을 연결요소로 묶고 면적,
밝기 대비, 모양, 최소 거리로 별 후보를 골라냅니다. 별 후보가 너무 많으면 점수가 높은
순서로 제한합니다.

#### Delaunay 그래프

별 사진은 회전·확대·축소될 수 있으므로 픽셀 좌표 자체보다 별 사이의 상대 구조를
사용합니다. Delaunay 삼각분할은 주변 별을 삼각형과 간선으로 연결합니다. 너무 긴
간선은 제거하고 삼각형 변의 길이비와 각도처럼 크기 변화에 비교적 강한 특징을 만듭니다.

#### HYG·Stellarium 패턴 매칭

Stellarium Western 데이터의 HIP 번호를 HYG 좌표와 결합하여 기준 별자리 그래프를
만듭니다. 관측 그래프와 기준 그래프의 삼각형 비율, 연결 관계, 추가 검증점 일치 수,
밝기 순서 등을 종합해 후보를 정합니다. 이 결과만으로는 우연히 비슷한 패턴을 찾을 수
있으므로 최종 확정에는 사용하지 않습니다.

#### Plate Solving과 WCS 검증

Astrometry.net은 사진 속 별 배열을 색인과 비교해 사진 중심 RA/DEC, 픽셀 스케일,
회전, 화각과 WCS 변환식을 구합니다. `07`단계는 WSL 로컬 `solve-field`를 먼저 사용하고
로컬 풀이가 실패할 때만 Nova 웹 API를 사용할 수 있습니다. 이미 해결한 결과는 캐시하여
불필요한 재업로드를 막습니다.

`06`단계는 후보 별만 검사하지 않고 HYG/Gaia 별을 사진 전체에 재투영합니다. 실제
검출점과의 일치 개수, 중앙값 및 P90 픽셀 오차, 화면 여러 영역에서의 공간 분포가 기준을
통과해야 WCS가 유효하다고 판단합니다.

#### 최종 예측

WCS가 유효하면 `11`단계가 Stellarium의 88개 별자리 연결선을 사진 좌표로 변환합니다.
화면 안에 들어오고 실제 검출점과 충분히 일치하는 별자리를 복수로 반환합니다. 광각
사진에는 여러 별자리가 함께 있으므로 단일 클래스가 아닌 다중 라벨 결과입니다.

실패한 경우에도 무리하게 별자리 이름을 반환하지 않고 다음과 같은 실패 코드를 기록합니다.

| 코드 | 의미 |
|---|---|
| `too_few_stars` | 매칭에 필요한 별 후보가 부족함 |
| `cloudy` | 구름이나 낮은 대비로 별 구조가 충분히 보이지 않음 |
| `plate_solve_failed` | Plate Solving을 시도했지만 WCS를 찾지 못함 |
| `plate_solve_not_run` | Plate Solving이 실행되지 않음 |
| `ambiguous` | 후보가 여러 개이거나 검증 근거가 부족함 |
| `no_candidate` | 그래프 후보를 만들지 못함 |

### 2.4 현재 모델과 향후 딥러닝 학습

`21_prepare_yolo_dataset.py`가 MobilTelesco 8클래스 데이터를 세션 누수 없이 YOLO 형식으로
구성하고, `22_train_yolo.py`가 사전 학습된 YOLO11n을 전이 학습합니다. GPU/CPU 자동 선택,
스모크 테스트, 체크포인트 재개, 가중치와 지표 저장까지 구현되어 있습니다. 현재 생성된
`best.pt`는 1 epoch·5% 데이터로 실행한 동작 확인용이므로 실제 예측 모델로 사용하려면
전체 학습을 별도로 실행해야 합니다. 기존 별자리 인식 파이프라인은 다음 규칙·기하·천문
검증 방법도 계속 사용합니다.

| 기능 | 현재 사용 방법 |
|---|---|
| 별 검출 | DoG, 임계값, 연결요소, NMS |
| 별 구조 | Delaunay 삼각분할 |
| 후보 검색 | 삼각형 비율과 그래프 구조 매칭 |
| 절대 위치 계산 | Astrometry.net 인덱스 기반 Plate Solving |
| 검증 | WCS에 HYG/Gaia 좌표 재투영 |
| 별자리 표시 | Stellarium Western 연결선 투영 |

향후 딥러닝은 현재 파이프라인을 버리는 대신 다음 부분부터 보조하는 것이 현실적입니다.

1. `good`, `cloudy`, `too_few_stars`, `motion_blur`, `light_pollution` 품질 분류
2. 기존 DoG보다 강한 별/핫픽셀/비행기 구분용 keypoint 또는 object detector
3. 별 그래프 후보 순위를 개선하는 learned descriptor
4. 최종 WCS·Gaia 검증은 안전장치와 자동 라벨 생성기로 계속 유지

외부 사진을 학습에 사용할 때는 저작권, 촬영기기, 중복 및 라벨 품질을 확인해야 합니다.
학습/검증/테스트는 개별 프레임이 아니라 `scene_id`, 촬영자, 촬영일을 기준으로 분리합니다.

## 3. 데이터 출처와 각 데이터의 의미

### AstroSmartphoneDataset

- 출처: [GitHub](https://github.com/oparisot/AstroSmartphoneDataset),
  [Zenodo](https://zenodo.org/records/14933725)
- 내용: Google Pixel 4a, 6, 8 Pro, 8a 등으로 촬영한 실제 광각 스마트폰 밤하늘 사진
- 용도: 이미지 품질 분석, 별 검출, Plate Solving, 평가셋 자동 생성
- 주의: 같은 Night Sight 촬영의 연속 프레임은 독립 장면으로 계산하지 않음

### Image Constellation Dataset

- 출처: [Kaggle](https://www.kaggle.com/datasets/basimbaqai/image-constellation-dataset)
- 내용: 별자리 이미지와 연결선이 포함된 참고 이미지
- 용도: 별자리 형태와 라벨 구조 참고
- 한계: 실제 스마트폰 사진과 영상 분포가 달라 이것만으로 실사용 모델을 학습하기 어려움

### HYG Database

- 출처: [HYG Database GitHub](https://github.com/astronexus/HYG-Database)
- 내용: Hipparcos, Yale Bright Star, Gliese 자료를 결합한 비교적 다루기 쉬운 별 목록
- 주요 값: HIP/HD/HR 번호, RA, DEC, 겉보기등급, 고유명, 별자리 약어
- 용도: Stellarium 연결선의 HIP 번호를 실제 천구 좌표와 결합

### Gaia DR3

- 출처: [ESA Gaia Data Access](https://www.cosmos.esa.int/web/gaia/data-access)
- 내용: 별의 고정밀 위치, 밝기, 색, 고유운동, 시차
- 이 프로젝트의 파일: 전체 약 20억 개가 아니라 밝은 별만 ADQL로 조회한 CSV
- 용도: 사진 전체에서 WCS 재투영이 일관적인지 정밀 검증

사용한 조회 조건의 예시는 다음과 같습니다.

```sql
SELECT source_id, designation, ra, dec, ref_epoch,
       pmra, pmdec, parallax,
       phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp
FROM gaiadr3.gaia_source
WHERE phot_g_mean_mag < 10
```

### 공식 별자리 경계

- 출처: [CDS VizieR VI/49](https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=VI%2F49)
- 사용 표: `bound_20`, J2000으로 갱신된 별자리 경계점
- 내용: 어느 천구 영역이 88개 IAU 별자리 중 어디에 속하는지 판정하는 경계
- 주의: 경계는 화면에 그리는 연결선과 다른 데이터

### Stellarium Sky Cultures

- 출처: [Stellarium Sky Cultures](https://github.com/Stellarium/stellarium-skycultures)
- 사용 문화권: Western
- 내용: 별자리별 HIP 번호 연결선, 이름, 문화·역사 설명
- 용도: 그래프 기준 패턴과 최종 화면 연결선
- 주의: 연결선은 IAU 공식 경계가 아니며 문화권마다 다르고 폴더별 라이선스를 확인해야 함

### Astrometry.net과 Nova

- 출처: [Astrometry.net](https://astrometry.net/),
  [Nova 사용법](https://nova.astrometry.net/use.html)
- 내용: 사진의 별 배열로 촬영한 하늘의 실제 좌표계와 카메라 방향을 해결하는 소프트웨어
- 용도: WCS, 중심 RA/DEC, 화각, 회전, 픽셀 스케일 생성
- 개인정보: Nova 업로드 시 기본적으로 EXIF/GPS를 제거한 비공개 임시 사본 사용

### 사용자가 직접 촬영한 사진

`data/photo/smartphone/`에 저장합니다. 개인 사진은 GPS와 촬영시간을 포함할 수
있으므로 Git에 커밋하지 않습니다. `15`단계가 촬영기기와 메타데이터 보유 여부를 조사하고,
`16`단계가 검토된 사진만 자동 라벨링합니다.

## 4. 주요 변수와 천문 용어

### 천구 좌표와 관측 위치

| 변수 | 한국어 의미 | 단위·범위 | 설명 |
|---|---|---|---|
| `ra` / `RAJ2000` | 적경 | 도 0~360 또는 시 0~24h | 지구 경도와 비슷한 천구의 동서 좌표 |
| `dec` / `DEJ2000` | 적위 | 도 -90~+90 | 지구 위도와 비슷한 천구의 남북 좌표 |
| `J2000` | J2000 기준시점 | epoch | 세차로 좌표가 변하므로 사용하는 표준 기준 시점 |
| `ICRS` | 국제천구기준계 | 좌표계 | Gaia와 현대 천문학에서 사용하는 기준 좌표계 |
| `latitude` | 위도 | 도 -90~+90 | 촬영 장소의 남북 위치, 북위가 양수 |
| `longitude` | 경도 | 도 -180~+180 | 촬영 장소의 동서 위치, 동경이 양수 |
| `altitude` | 고도각 | 도 -90~+90 | 관측자 지평선에서 천체가 얼마나 높은지 |
| `azimuth` | 방위각 | 도 0~360 | 일반적으로 북쪽부터 시계 방향의 방향 |
| `center_ra` | 사진 중심 적경 | 도 | 사진 중심 픽셀이 가리키는 천구 적경 |
| `center_dec` | 사진 중심 적위 | 도 | 사진 중심 픽셀이 가리키는 천구 적위 |

`latitude/longitude`는 지구상의 촬영 위치이고, `ra/dec`는 하늘에 있는 별의 위치입니다.
둘은 같은 위도·경도가 아니며 촬영 시간과 함께 천체의 지평선 가시성을 계산할 때 연결됩니다.

### 별 카탈로그 변수

| 변수 | 의미 |
|---|---|
| `hip` | Hipparcos 카탈로그의 별 식별번호 |
| `hd` | Henry Draper 카탈로그 번호 |
| `hr` | Harvard Revised/Yale Bright Star 번호 |
| `source_id` | Gaia DR3 천체 고유 식별번호 |
| `designation` | `Gaia DR3 ...` 형태의 공식 명칭 |
| `proper` | Betelgeuse 같은 별의 고유명 |
| `con` / `cst` / `iau` | `Ori`, `Per`, `Cas` 같은 IAU 3글자 별자리 약어 |
| `mag` | 겉보기등급. 숫자가 작거나 음수일수록 밝음 |
| `phot_g_mean_mag` | Gaia G 밴드 평균 밝기 등급 |
| `phot_bp_mean_mag` | Gaia 청색 광도계(BP) 평균 등급 |
| `phot_rp_mean_mag` | Gaia 적색 광도계(RP) 평균 등급 |
| `bp_rp` | BP-RP 색지수. 별의 색과 온도 추정에 사용 |
| `ref_epoch` | Gaia 좌표가 기준으로 하는 관측 시점 |
| `pmra`, `pmdec` | 적경·적위 방향 고유운동, 보통 mas/year |
| `parallax` | 연주시차, 보통 mas. 거리를 추정하는 데 사용 |

### 이미지와 별 검출 변수

| 변수 | 의미 |
|---|---|
| `x`, `y` | 사진 왼쪽 위를 원점으로 한 별 후보 픽셀 좌표 |
| `width`, `height` | 이미지 가로·세로 픽셀 수 |
| `area` | 연결요소로 검출된 밝은 영역의 픽셀 면적 |
| `peak` | 후보 영역의 최대 밝기 |
| `contrast` | 후보가 주변 배경보다 밝은 정도 |
| `score` | 밝기·대비·모양 등을 결합한 별 후보 또는 매칭 점수 |
| `threshold_sigma` | 배경 노이즈 표준편차에 대한 검출 임계 배수 |
| `min_distance` | 중복 별 후보를 막는 최소 픽셀 거리 |
| `max_stars` | 다음 단계로 넘길 별 후보 최대 개수 |
| `sky_fraction` | 사진 위쪽에서 별 검출에 사용할 영역 비율 |

### 그래프 매칭 변수

| 변수 | 의미 |
|---|---|
| `edge` | 두 별 후보를 잇는 그래프 간선 |
| `triangle` | Delaunay 삼각분할로 만든 세 별의 조합 |
| `edge_length` | 두 별 사이의 픽셀 거리 |
| `side_ratio` | 삼각형 변을 가장 긴 변으로 나눈 비율 |
| `matched` | 기준 별자리 연결선/별 중 관측 그래프와 대응된 개수 |
| `matched/total` | 예: `9/11`은 기준점 11개 중 9개가 대응되었다는 의미 |
| `confidence` | 구조 근거와 외부 검증을 요약한 신뢰도 등급 |

매칭 이미지의 `18246`, `18614` 같은 숫자는 검출 순번이 아니라 Stellarium 연결선이
참조하는 **HIP 별 번호**입니다.

### Plate Solving과 WCS 변수

| 변수 | 한국어 의미 | 설명 |
|---|---|---|
| `WCS` | 세계좌표계 | 이미지 픽셀 `(x,y)`와 천구 `(RA,DEC)`를 변환하는 FITS 좌표 정보 |
| `pixscale` | 픽셀 스케일 | 한 픽셀이 나타내는 하늘 각도, `arcsec/pixel` |
| `field_of_view` / `fov` | 화각 | 사진이 포함하는 하늘의 가로·세로 각도 |
| `orientation` | 방향/회전각 | 사진 축이 천구 기준 방향에서 회전한 각도 |
| `radius` | 사진 중심에서 가장자리까지의 대략적인 각거리 |
| `reprojection_error` | 재투영 오차 | 카탈로그 별을 WCS로 사진에 옮겼을 때 검출점과 떨어진 픽셀 거리 |
| `median_error_px` | 중앙 재투영 오차 | 모든 일치점 오차의 중앙값 |
| `p90_error_px` | 90백분위 오차 | 일치점의 90%가 이 값 이하라는 뜻 |
| `matched_gaia_stars` | Gaia 일치 별 수 | 사진 전체에서 검출점과 대응된 Gaia 별 개수 |

### 평가 변수

| 변수 | 의미 |
|---|---|
| `expected_iau` | 정답 별자리 약어. 복수이면 `Per|Cas`처럼 기록 |
| `predicted_iau` | 시스템이 예측한 별자리 약어 집합 |
| `scene_id` | 같은 장소·방향·연속 촬영을 하나로 묶는 장면 ID |
| `precision` | 예측한 별자리 중 정답인 비율 |
| `recall` | 정답 별자리 중 찾아낸 비율 |
| `F1` | Precision과 Recall의 조화평균 |
| `exact_match` | 예측 집합과 정답 집합이 완전히 같은지 여부 |
| `overlap` | 정답 중 하나 이상을 예측했는지 여부 |
| `recognized` | WCS 등 외부 검증까지 통과한 확정 결과 |
| `candidate_only` | 그래프 후보는 있으나 확정 근거가 부족한 상태 |

## 5. 설치와 실행

### Python 환경

```powershell
cd C:\dev\star-predict-system\Constellation
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

`.env`에는 다음 형식으로 Nova API 키를 입력합니다.

```text
ASTROMETRY_NET_API_KEY=your_api_key_here
```

### 기준 데이터 검사

```powershell
.\.venv\Scripts\python.exe .\scripts\02_reference_validation.py
```

### 사진 한 장 전체 인식

```powershell
.\.venv\Scripts\python.exe .\scripts\10_end_to_end_pipeline.py ".\data\photo\smartphone\사진.jpg"
```

외부 업로드 없이 로컬 후보까지만 확인하려면 다음 옵션을 사용합니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\10_end_to_end_pipeline.py ".\data\photo\smartphone\사진.jpg" --skip-plate-solving
```

### WSL 로컬 Plate Solver 확인

```powershell
.\.venv\Scripts\python.exe .\scripts\17_local_plate_solver.py --check
```

### 새 스마트폰 사진 준비와 자동 라벨링

```powershell
.\.venv\Scripts\python.exe .\scripts\15_prepare_uploaded_photos.py
.\.venv\Scripts\python.exe .\scripts\16_batch_label_uploaded_photos.py
```

### Wikimedia Commons 사진 자동 수집

기존에 수동으로 받은 사진의 출처 정보를 먼저 등록합니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\18_collect_wikimedia_images.py --index-existing --limit 0
```

스마트폰 EXIF와 허용 라이선스를 확인해 사진을 최대 20장 다운로드합니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\18_collect_wikimedia_images.py --query "smartphone astrophotography" --query "mobile phone night sky" --limit 20
```

원본은 `data/photo/WikimediaCommons/images/`, 저작자·라이선스·카메라·원본 URL은
`data/photo/WikimediaCommons/metadata/sources.csv`에 저장됩니다. 기본 라이선스 필터는
CC0, Public Domain, CC BY이며 CC BY-SA는 `--include-sharealike`를 명시해야 합니다.

### 정답 평가와 오답 분석

```powershell
.\.venv\Scripts\python.exe .\scripts\13_evaluate_ground_truth_set.py
.\.venv\Scripts\python.exe .\scripts\14_error_analysis.py
```

## 6. 개인정보와 라이선스 주의사항

- `.env`의 API 키를 GitHub에 올리지 않습니다.
- 스마트폰 원본에는 GPS, 촬영시간, 기기 정보가 포함될 수 있습니다.
- Nova를 사용할 때는 기본적으로 메타데이터가 제거된 임시 사본을 비공개 업로드합니다.
- 외부 사진은 URL, 저작자, 라이선스, 원본 파일 URL을 함께 기록합니다.
- CC BY는 저작자와 라이선스를 표시해야 하며 CC BY-SA는 동일조건 의무도 확인합니다.
- 대용량 카탈로그와 외부 데이터셋은 각 원본 라이선스를 따르며 Git 저장소에 포함하지 않습니다.

## 7. 현재 완성도와 다음 단계

현재 사진 한 장을 입력해 별 후보 검출, 그래프 후보, 로컬/Nova Plate Solving, WCS·Gaia
검증, 복수 별자리 오버레이와 실패 판정까지 수행할 수 있습니다. 즉 천문학적 규칙 기반
인식 MVP는 동작합니다.

딥러닝 모델까지 포함한 완성형 시스템을 위해 남은 주요 작업은 다음과 같습니다.

1. 라이선스가 명확하고 촬영 세션이 다양한 실제 스마트폰 사진 확보
2. 외부 사진의 EXIF·라이선스·중복 해시를 포함한 수집 매니페스트 구축
3. 현재 파이프라인으로 자동 라벨 생성 후 애매한 사진 수동 검수
4. 장면 단위 train/validation/test 분할
5. 품질 분류 모델과 별 keypoint 검출 모델 학습
6. 기존 DoG와 딥러닝 모델을 동일 평가셋에서 비교
7. ONNX 등 배포 형식으로 내보내고 10단계 파이프라인에 선택적으로 결합
