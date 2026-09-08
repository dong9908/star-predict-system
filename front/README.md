# ASTRA Frontend

밤하늘 사진을 업로드하면 Python 분석 서버와 연동하여 천체 및 별자리 후보를 찾고, 별자리 연결선과 상세 정보를 화면에 표시하는 React 프론트엔드입니다.

## 2026-09-08 작업 내용

### 1. Python/FastAPI 별자리 분석 연동

- 프론트에서 선택한 JPG 또는 PNG 이미지를 `multipart/form-data`로 전송합니다.
- 기존 FastAPI의 `POST /api/constellation/recognize`를 호출합니다.
- YOLO 천체 검출 결과와 WCS/별 구조 분석 결과를 받아 결과 페이지에 표시합니다.
- Vite 개발 서버의 `/api` 요청은 `http://127.0.0.1:8000`으로 전달됩니다.
- 지원 형식은 JPG와 PNG이며 이미지 한 장의 최대 크기는 10MB입니다.

관련 파일:

- `src/api/constellation.js`
- `src/pages/ConstellationFindPage.jsx`
- `vite.config.js`
- `../server/routes/constellation_recognition.py`
- `../server/services/constellation_recognition.py`

### 2. 사진 업로드 화면 개선

- 파일 선택과 드래그 앤 드롭 업로드를 지원합니다.
- 사진을 선택하면 업로드 영역 안에 실제 사진 미리보기가 나타납니다.
- 미리보기 아래에 선택한 파일명을 초록색으로 표시합니다.
- 선택 후에도 `사진 선택` 버튼을 눌러 다른 이미지로 교체할 수 있습니다.
- 카메라 아이콘과 업로드 안내 문구는 사진을 선택한 뒤 숨겨집니다.
- 잘못된 안내 문구를 `사진 속 별자리를 AI가 찾아 드립니다.`로 수정했습니다.
- 이미지가 변경되거나 페이지가 종료될 때 임시 미리보기 URL을 해제합니다.

관련 파일:

- `src/pages/ConstellationFindPage.jsx`
- `src/pages/styles/ConstellationFindPage.styles.js`

### 3. 별자리 분석 중 페이지 추가

기존에는 업로드 화면에서 API 응답을 기다린 뒤 결과 화면으로 바로 이동했습니다. 현재는 실제 화면 흐름을 다음 3단계로 분리했습니다.

```text
01 사진 업로드 → 02 별자리 분석 → 03 결과 확인
```

분석 화면에서는 다음 기능을 제공합니다.

- 업로드 화면에서 선택한 사진 미리보기
- 보라색 별 궤도 로딩 애니메이션
- 기존 FastAPI 분석 API 자동 호출
- 현재 수행 가능한 분석 절차를 설명하는 순환 안내 문구
- 분석 성공 시 결과 페이지로 자동 이동
- 요청 실패 시 오류 메시지, 다시 분석하기, 다른 사진 선택 기능
- 사진 정보 없이 분석 주소를 직접 열었을 때 업로드 화면 이동 안내
- 1단계는 완료, 2단계는 활성화, 3단계는 대기 상태로 표시

화면에 표시되는 안내 단계는 다음과 같습니다.

1. 업로드한 사진 확인
2. AI 주요 별·천체 후보 탐색
3. 별 위치 및 연결 구조 비교
4. 천구 좌표 검증 시도
5. 분석 결과 정리

현재 API가 중간 진행률을 반환하지 않으므로 부정확한 퍼센트는 표시하지 않습니다. 안내 문구는 사용자에게 분석 내용을 설명하기 위한 것이며 실제 서버 진행률과 정확히 일치하지 않을 수 있습니다.

관련 파일:

- `src/pages/ConstellationAnalyzingPage.jsx`
- `src/pages/styles/ConstellationAnalyzingPage.styles.js`
- `src/App.jsx`

추가된 경로:

```text
/constellation-find-analyzing
```

### 4. 분석 결과 페이지 실데이터 적용

- 고정된 예시 순위 대신 FastAPI 응답을 이용해 결과 목록을 생성합니다.
- WCS 검증 결과가 있으면 검증된 구조 결과를 우선 표시합니다.
- WCS가 없으면 별 구조 분석 후보를 표시합니다.
- 결과별 한글 이름, 영문 이름, 점수 및 검증 상태를 표시합니다.
- 최대 4개의 별자리 구조 후보를 서로 다른 색상으로 구분합니다.

구조 후보 색상:

1. 보라색
2. 파란색
3. 초록색
4. 빨간색

관련 파일:

- `src/pages/ConstellationFindResultPage.jsx`
- `src/pages/styles/ConstellationFindResultPage.styles.js`
- `src/data/analysisResults.js`

### 5. 별자리 점과 연결선 표시

- 분석된 사진 위에 SVG 오버레이로 별자리 점과 선을 표시합니다.
- 여러 별자리가 검증되면 모든 별자리 연결선을 동시에 표시합니다.
- 상단 구조 후보 배지와 사진 속 연결선에 같은 색상을 사용합니다.
- WCS로 확인된 결과는 `검증됨`, 구조 비교만 수행한 결과는 `미확정`으로 구분합니다.
- 구조 후보 배지를 사진 영역 밖에 배치하여 사진을 가리지 않도록 수정했습니다.
- 오른쪽 분석 결과에도 구조 후보의 점수와 동일한 결과를 표시합니다.

### 6. 사진 확대·축소·이동 기능

- `+` 버튼으로 0.25배씩 확대하며 최대 배율은 4배입니다.
- `-` 버튼으로 0.25배씩 축소하며 최소 배율은 1배입니다.
- 초기화 버튼을 누르면 배율과 이동 위치가 초기화됩니다.
- 1배로 축소해도 이동 위치가 자동으로 초기화됩니다.
- 사진을 확대하면 마우스 또는 터치 드래그로 원하는 영역을 이동할 수 있습니다.
- 사진을 더블클릭하면 원래 배율과 위치로 돌아갑니다.
- 사진과 SVG 별자리 연결선을 같은 레이어에 배치하여 확대·이동할 때 함께 움직입니다.
- 확대·축소·초기화 버튼을 사진 오른쪽 아래에서 사진 아래 중앙으로 이동했습니다.

관련 파일:

- `src/pages/ConstellationFindResultPage.jsx`
- `src/pages/styles/ConstellationFindResultPage.styles.js`

### 7. 주요 별 강조 기능

- 별자리의 주요 별을 일반 별보다 크고 선명하게 표시합니다.
- 주요 별에는 글로우와 반복되는 밝기 효과가 적용됩니다.
- 상세 정보의 주요 별 버튼을 누르면 사진 속 해당 별이 약 1.8초 동안 반짝입니다.
- 현재 사진 범위에서 확인되지 않은 별은 비활성 상태로 표시합니다.
- 사진 좌표와 주요 별을 연결하기 위해 HIP 번호를 사용합니다.

현재 등록된 주요 별 예시:

- 오리온자리: 베텔게우스, 리겔, 벨라트릭스
- 쌍둥이자리: 카스토르, 폴룩스, 알헤나
- 황소자리: 알데바란, 엘나타, 톈관
- 마차부자리: 카펠라, 멘칼리난, 하살레

관련 파일:

- `src/data/analysisResults.js`
- `src/pages/ConstellationFindResultPage.jsx`
- `src/pages/styles/ConstellationFindResultPage.styles.js`

### 8. 인식 결과 없음 화면 개선

- 작은 결과 메시지 영역을 분석 페이지와 비슷한 폭의 보라색 카드로 변경했습니다.
- 분석에 사용한 사진을 다시 보여줍니다.
- 내부 기술 메시지 대신 사용자에게 이해하기 쉬운 문구를 표시합니다.
- 다음 촬영 안내를 함께 제공합니다.
  - 어두운 장소에서 촬영
  - 카메라를 흔들지 않기
  - 별이 선명한 사진 사용
- `다른 사진 분석하기` 버튼으로 업로드 화면에 돌아갈 수 있습니다.

### 9. 결과 화면 단계 표시

정상 결과와 인식 결과 없음 화면 모두 상단에 다음 상태를 표시합니다.

```text
✓ 사진 업로드 → ✓ 별자리 분석 → 03 결과 확인
```

1단계와 2단계는 초록색 완료 상태, 3단계는 보라색 활성 상태입니다.

## 실행 방법

명령어는 프로젝트 루트 `D:\dev\star-predict-system`을 기준으로 합니다.

### 1. Python 분석 서버 실행

```powershell
cd D:\dev\star-predict-system; .\Constellation\.venv\Scripts\python.exe -m uvicorn main:app --app-dir server --host 127.0.0.1 --port 8000 --reload
```

### 2. 프론트 개발 서버 실행

새 PowerShell 또는 Cmder 창에서 실행합니다.

```powershell
cd D:\dev\star-predict-system\front; npm run dev
```

브라우저 접속 주소:

```text
http://localhost:5173/constellation-find
```

### 3. 프론트 빌드 검사

```powershell
cd D:\dev\star-predict-system\front; npm run build
```

2026-09-08 작업 완료 시점에 Vite 프로덕션 빌드가 정상적으로 통과했습니다.

## 페이지 구성

| 경로 | 화면 | 현재 단계 |
|---|---|---:|
| `/constellation-find` | 사진 선택 및 업로드 | 01 |
| `/constellation-find-analyzing` | AI·구조·WCS 분석 안내 | 02 |
| `/constellation-find-result` | 별자리 결과 및 연결선 | 03 |

## 분석 데이터 전달 구조

```text
사진 선택
  → 업로드 페이지에서 File 객체 보관
  → 분석 페이지로 File 객체 전달
  → POST /api/constellation/recognize
  → Python YOLO 추론
  → 캐시된 WCS 확인 또는 별 구조 분석
  → JSON 분석 결과 반환
  → 결과 페이지에서 순위, 점, 선, 상세 정보 표시
```

## 현재 AI와 비AI 분석 구분

- YOLO 천체 검출: 딥러닝 AI 사용
- 별의 밝은 점 검출: AI 미사용
- 별 구조 그래프 비교: AI 미사용
- Astrometry.net Plate Solving: AI 미사용
- WCS 좌표 변환 및 연결선 생성: AI 미사용

따라서 화면에서 YOLO 결과는 AI 검출 후보이고, WCS 결과는 천문 좌표와 기하학적 계산에 기반한 검증 결과입니다.

## 현재 모델 범위

현재 YOLO 모델은 다음 8개 클래스를 검출합니다.

1. Pleiades
2. Jupiter
3. Betelgeuse
4. Aldebaran
5. Zeta Tauri
6. Elnath
7. Hassaleh
8. Bellatrix

서버에서는 검출된 천체를 황소자리, 오리온자리, 마차부자리 또는 목성 결과로 묶습니다. WCS가 있는 사진은 이 범위를 넘어 쌍둥이자리, 에리다누스자리 등의 구조를 표시할 수 있습니다.

## 테스트에 사용한 WCS 성공 사진

```text
D:\dev\star-predict-system\Constellation\data\photo\AstroSmartphoneDataset\pixel4a-medium-res\PXL_20220207_190705969.NIGHT_0008.jpg
```

이 사진에서는 황소자리, 쌍둥이자리, 오리온자리, 에리다누스자리의 WCS 구조 결과를 확인했습니다.

## 현재 제한사항

- 한 번에 사진 한 장만 분석합니다.
- 분석 중 안내 문구는 실제 서버의 세부 진행률이 아닙니다.
- 업로드한 `File`과 분석 결과는 React Router 상태로 전달되므로 분석 또는 결과 주소에서 새로고침하면 사라질 수 있습니다.
- 새로운 사진의 Plate Solving을 실시간으로 실행하는 구조는 아직 안정화되지 않았습니다.
- 현재 WCS 검증은 기존 Plate Solving 성공 원본과 파일명 및 파일 내용이 일치할 때 가장 안정적으로 작동합니다.
- Plate Solving 결과가 없으면 구조 분석 결과가 `미확정` 후보로 표시될 수 있습니다.
- 별자리 설명과 주요 별 정보는 현재 DB가 아니라 `src/data/analysisResults.js`의 프론트 데이터에 의존합니다.
- 프론트에 상세 정보가 없는 별자리는 기본 설명만 표시됩니다.
- 여러 사진 분석, 분석 이력 DB 저장, 새로고침 복구는 아직 구현되지 않았습니다.

## 발표용 SHA-256 결과 캐시

발표 PC의 프로젝트 위치나 업로드 파일명과 관계없이 동일한 시연 결과를 재현할 수 있도록, 등록된 테스트 사진은 파일 내용의 SHA-256 해시만으로 판별합니다.

- 캐시 위치: `../server/assets/constellation_results/`
- 파일 이름: `<SHA-256>.json`
- 성공 사진은 황소자리, 쌍둥이자리, 오리온자리, 에리다누스자리의 미리 계산된 WCS 검증 결과를 반환합니다.
- 미검출 사진은 촬영 안내가 포함된 결과 없음 화면을 반환합니다.
- 등록되지 않은 일반 사진은 기존 YOLO 및 WCS/구조 분석 절차를 그대로 실행합니다.
- 사진의 이름이나 저장 경로는 바꿔도 되지만 이미지 편집, 압축, 크기 변경이 발생하면 해시가 달라져 일반 분석으로 처리됩니다.
