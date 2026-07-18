# 졸업요건·교육과정 데이터

대진대학교 공식 공개 자료를 자동 시간표 생성과 예상 졸업요건 점검에 사용할 수 있도록 원본과 정규화 결과를 분리했다.

## 구조

```text
requirements/
├── raw/
│   ├── 2016/ ... 2026/          # 연도별 교육과정편람 HWP/PDF
│   ├── 2026/                     # 학과별 졸업심사·대체/동일과목 원본
│   └── rules/                    # 학칙·시행세칙·졸업논문시행규정 HWP
└── normalized/
    ├── curriculum-requirements-2016-2026.json
    ├── sources.json
    ├── common-graduation-rules.json
    ├── graduation-requirements-2020-2026.json
    ├── major-required-courses-2026.json
    ├── department-source-coverage-2026.csv
    ├── graduation-transition-2026.csv
    ├── graduation-standardized-requirements-2026.csv
    ├── graduation-legacy-requirements-2026.csv
    └── graduation-credential-details-2026.csv
```

## 커버리지

- 2016~2026 입학연도별 교육과정 정규화: 11개 연도, 712개 교육과정 단위, 전공기초·전공필수 2,944과목
- 분류별 정규화: 전공기초(`전기`) 284과목, 전공필수(`전필`) 2,660과목
- 2020~2026 학과·입학연도·전공경로별 졸업 최저학점 프로필: 789개
- 2020~2026 교양필수 과목: 52개 연도별 레코드, 교양 영역 조건 포함
- 2026 학과별 졸업심사 프로필: 66개 단위, 표준 A/C/E/S 조건 264개와 자격 상세를 학과 단위로 묶어 저장
- 종전 학과 졸업심사 자유서술 조건: 35개 규칙, 학번 언급을 별도 인덱스로 보존
- 2026 현재 교육과정 단위: 46/46
- 2026 편람 전공필수 정규화: 46개 단위 상태를 모두 보존하며, 45개 표 수록 단위 중 전공필수가 있는 31개 단위, 113과목
- 학과별 개별 교육과정 URL: 44/46, 나머지 2개는 중앙 편람 원문 확보
- 현재 독립 졸업심사 단위: 44/44
- 졸업심사 원천의 현재·종전·융합 단위: 66개
- 표준화 A/C/E/S 행: 264개
- 교육과정편람 로컬 원본: 2016~2026, 11개 연도 연속 확보
- 2012~2015 교육과정편람: 대학 공식 대학생활안내 색인과 iBook 원문 URL 확인, 로컬 보존·정규화 대기
- 학칙·시행세칙·졸업논문시행규정 및 2026-1 대체·동일과목 원본 확보

상세 근거와 누락은 `docs/research/DAEJIN_ACADEMIC_REQUIREMENTS_SOURCE_AUDIT.md`와 `docs/research/DAEJIN_GRADUATION_RULES.md`를 참고한다.

## 사용 원칙

1. 원본은 수정하지 않고 SHA-256으로 동일성을 검증한다.
2. 졸업요건은 학생의 입학연도 편람을 기준으로 적용한다.
3. 현재 학과명과 원본 학과명은 별도로 보존한다.
4. PDF 페이지, XLSX 시트·행, 규정 조항을 결과와 함께 저장한다.
5. 원문 메타데이터가 충돌하면 자동 보정하지 않고 검수 대상으로 둔다.
6. 공개 자료로 확정할 수 없는 개인별 승인·증빙·포털 판정은 `UNKNOWN`으로 처리한다.
7. 서비스 문구는 `졸업 확정`이 아니라 `예상 졸업요건 점검`을 사용한다.
8. `curriculum-requirements-2016-2026.json`은 2016 HWP 표 셀과 2017~2026 PDF 좌표를 복원한 통합 입학연도별 자료다. 원문 학과명, 별칭, 과목코드, 학점, 학년·학기와 페이지/표 위치를 함께 보존한다.
9. `major-required-courses-2026.json`은 현재 브라우저 호환용 검수 snapshot이다. 통합 자료의 2026 현재 교육과정 단위 전공필수 집합은 이 파일과 일치하도록 회귀 검증한다.
10. `timetabler-ingest`는 통합 교육과정과 공통·학과별 졸업심사 자료를 checksum 검증 후 PostgreSQL에 멱등 적재한다. 학과별 자유서술 졸업심사 조건은 자동 확정하지 않고 `requires_manual_review`로 저장한다.
11. `graduation-requirements-2020-2026.json`은 편람의 졸업소요 최저학점 표를 학과·입학연도·전공경로(`DOUBLE_MAJOR`, `ADVANCED_MAJOR`, 2025년 이후 `MINOR`, `MICRO_MAJOR`)별 정량 프로필로 만든 자료다. 총학점, 교양, 전공기초·필수·선택, 주전공·추가전공 최소학점과 해당 연도 교양필수 과목을 API가 자동 점검한다.

## 데이터 제한

- 2012~2015 교육과정편람은 공식 iBook 원문을 확인했지만 아직 로컬 원본·페이지 인덱스·학과별 과목표를 정규화하지 않았다. 정규화와 검수가 끝날 때까지 이 학번의 학과별 전공필수는 `UNKNOWN`으로 처리한다.
- 2016~2026은 중앙 교육과정편람에 실제 과목표가 수록된 모든 교육과정 단위를 정규화했다. 정량 졸업 최저학점 자동 점검은 과목 데이터가 연속된 2020~2026을 대상으로 한다. 외국인·편입학 예외, 개인별 승인, 자유서술형 졸업논문·시험·자격 조건은 자동 확정 범위가 아니다.
- 공식 표 자체에서 세부 전공학점 합계와 주전공 합계가 어긋나는 성인학습자 복수전공 7개 행은 값을 임의 보정하지 않고 `consistencyWarnings`와 `requiresManualReview`로 표시했다.
- 전수 공식 선수과목 관계는 확인되지 않았다. 이수체계도는 필수 선수조건이 아니라 추천 순서로 분리해야 한다.
- 학과 홈페이지는 기준일 미표시와 SSO redirect가 있어 중앙 편람·XLSX의 보조 원천으로만 사용한다.
- 2026 대학생활안내는 약 41MB이므로 일반 Git에 넣지 않고 공식 URL과 checksum만 source inventory에 보존한다.

## 갱신

- 교육과정편람: 12~2월 주 1회, 평시 월 1회
- 학과별 졸업심사 XLSX: 2~5월과 8~11월 주 1회
- 대체·동일과목 및 규정 포털: 주 1회
- 수강신청 전 학과 보조 페이지: 주 1회

새 버전은 `fetch → checksum → parse → schema/합계 검증 → diff → 사람 승인 → 활성화` 순서로 반영한다.

```bash
uv --directory apps/backend run timetabler-normalize-requirements
uv --directory apps/backend run timetabler-normalize-graduation-requirements
docker compose run --rm --build ingest
```
