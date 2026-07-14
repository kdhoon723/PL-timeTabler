# 제품 검증 데이터

시간표 자동 생성 알고리즘, 모바일 UI/UX, 입학연도·학과별 예상 졸업요건 점검에 사용할 대진대학교 데이터 모음이다.

## 디렉터리

```text
data/
├── courses/
│   ├── courses-2026-1.json
│   ├── courses-2026-1.csv
│   └── courses-lookup-2026-1.json
├── classrooms/
│   └── classroom-sessions-2026-1.json
├── dreams/                      # 2020~2026 포털 강의·교육과정 이력 아카이브
│   ├── terms/
│   ├── curricula/
│   ├── relations.json.gz
│   └── manifest.json
├── requirements/
│   ├── raw/                      # 공식 교육과정편람·졸업심사 원본
│   └── normalized/               # 출처 커버리지와 정규화 규칙
└── manifest.json
```

## 데이터셋

### `courses/courses-2026-1.json`

- 출처 snapshot: `DJSS/scraper/data/courses_20260203.json`
- 1,576개 분반의 과목 카탈로그
- 필드: `category`, `curiNo`, `clssNo`, `cousNm`, `profNm`, `lectTm`, `pnt`
- 시간표 최적화, 전공·교양 필터, 학점 계산의 기준 데이터
- 원본의 내부 교번 `empno`와 값이 비어 있던 `tlsn`, `tlsnLmt`는 복사 과정에서 제외했다.

### `courses/courses-2026-1.csv`

- 출처 snapshot: `DJSS/scraper/data/courses_20260203.csv`
- JSON과 동일한 1,576개 분반을 표 형태로 확인하거나 분석할 때 사용한다.

### `courses/courses-lookup-2026-1.json`

- 출처 snapshot: `DJSS/frontend/app/data/courses-lookup.json`
- 과목 검색과 자동완성을 위한 경량 데이터
- `category`가 없으므로 최적화 기준 데이터가 아니라 검색 인덱스 용도로 사용한다.

### `classrooms/classroom-sessions-2026-1.json`

- 출처 snapshot: `DJGongsil/app/public/data.json`
- 325개 강의실과 1,693개 수업 세션
- 건물, 강의실, 수용인원, 요일, 시작·종료시간 포함
- 과목 데이터와 `(curiNo, clssNo)`를 결합키로 사용한다.

### `requirements/`

- 출처: 대진대학교 공식 학칙·시행세칙·교육과정편람·졸업심사 지정표
- 2016~2026 교육과정편람 원본, 최신 학칙·시행세칙, 2026 학과별 졸업심사·대체/동일과목 원본
- 2026 현재 교육과정 단위 46/46과 독립 졸업심사 단위 44/44의 출처 매핑
- 공통 졸업학점·교양·다전공 규칙과 학과별 논문·시험·자격·경력 조건
- 2026 교육과정편람의 전공필수 113과목(31개 단위)과 학년·학기·편람 페이지
- 자세한 구조와 제한은 [`requirements/README.md`](requirements/README.md)를 참고한다.

### `dreams/`

- 출처: 대진대학교 DREAMS2 수강편람 인증 화면
- 2020~2026 정규·여름·겨울 28개 학기, 총 20,031개 분반-학기 레코드
- 강의계획서의 영문명, 이수구분, 시수, 강의실, 대상학년, 역량, 평가, 교재, 과제, 주별계획 포함
- 연도별 교육과정 12,216행과 대체과목 807건·동일과목 518건 포함
- 내부 교번과 교수 연락처·연구실·이메일·면담시간, 로그인·세션 정보는 저장하지 않음
- 자세한 스키마·결측 정책·재수집 방법은 [`dreams/README.md`](dreams/README.md)를 참고한다.

## 결합 현황

- 과목 카탈로그: 1,576개 분반
- 강의실 데이터: 1,342개 고유 분반
- 양쪽에서 일치하는 분반: 1,336개
- 과목 카탈로그 기준 강의실 결합률: 약 84.8%

두 출처는 같은 2026학년도 1학기 데이터지만 수집 시점과 포함 범위가 다르므로, 결합되지 않는 과목은 오류로 간주하지 않고 `room: null` 같은 형태로 처리한다.

## 사용 원칙

- 현재 파일은 자동 생성기, 졸업요건 파서, 제품 UI의 고정 fixture다.
- 실제 서비스 데이터는 학기별 디렉터리 또는 버전 필드를 사용해 교체한다.
- 수집 원본을 갱신할 때는 `manifest.json`의 레코드 수와 체크섬도 함께 갱신한다.
- 브라우저 fallback은 수동으로 편집하지 않고 `uv --directory apps/backend run timetabler-export-static-catalog`로 canonical API snapshot에서 생성한다.
- 내부 식별자, 계정 정보, 쿠키 등 시간표 생성에 필요하지 않은 값은 이 프로젝트에 복사하지 않는다.

`DJSS`와 `DJGongsil` 표기는 이 저장소를 준비할 때 사용한 별도 수집·정규화 프로젝트의 snapshot 식별자다. 로컬 절대경로가 아니며, 학교 원문과 공식 근거 URL은 `requirements/normalized/sources.json` 및 연구 문서에 보존한다.

이 데이터는 공개 강의정보와 공식 문서를 기반으로 한 참고용 snapshot이다. 학교의 최신 시스템 상태와 다를 수 있고 공식 수강신청·졸업 판정을 대체하지 않는다. 원문 자료의 권리와 이용 조건은 각 제공기관에 있다.
