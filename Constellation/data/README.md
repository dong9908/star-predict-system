# Data directories

실제 데이터는 용량, 라이선스, 개인정보 문제로 Git에 포함하지 않습니다.

```text
data/
├─ photo/
│  ├─ AstroSmartphoneDataset/        외부 스마트폰 밤하늘 데이터
│  ├─ MobilTelesco/                  라벨·DNG·JPG를 포함한 천체사진 데이터
│  ├─ smartphone/                    사용자가 직접 받은 스마트폰 사진
│  ├─ WikimediaCommons/              출처 메타데이터를 포함한 Commons 사진
│  └─ ConstellationDataset/          별자리 모양 참고 이미지
├─ reference/
│  ├─ gaia_dr3_g10.csv               Gaia DR3 밝은 별
│  ├─ constellation_boundaries_j2000.csv
│  └─ stellarium/western/index.json  Stellarium Western 연결선
├─ results/                          재생성 가능한 단계별 결과
├─ wcs/                              WCS, FITS, corr 파일
└─ evaluation/                       로컬 평가 매니페스트와 결과
```

개인 사진과 GPS가 포함될 수 있는 파일을 커밋하지 마세요.
