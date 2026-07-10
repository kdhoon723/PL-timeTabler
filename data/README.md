# 테스트 데이터

시간표 자동 완성 알고리즘과 UI/UX 프로토타입에서 사용할 2026학년도 1학기 대진대학교 데이터 모음이다.

## 디렉터리

```text
data/
├── courses/
│   ├── courses-2026-1.json
│   ├── courses-2026-1.csv
│   └── courses-lookup-2026-1.json
├── classrooms/
│   └── classroom-sessions-2026-1.json
└── manifest.json
```

## 데이터셋

### `courses/courses-2026-1.json`

- 출처: `/home/kdhoon/projects/DJSS/scraper/data/courses_20260203.json`
- 1,576개 분반의 과목 카탈로그
- 필드: `category`, `curiNo`, `clssNo`, `cousNm`, `profNm`, `lectTm`, `pnt`
- 시간표 최적화, 전공·교양 필터, 학점 계산의 기준 데이터
- 원본의 내부 교번 `empno`와 값이 비어 있던 `tlsn`, `tlsnLmt`는 복사 과정에서 제외했다.

### `courses/courses-2026-1.csv`

- 출처: `/home/kdhoon/projects/DJSS/scraper/data/courses_20260203.csv`
- JSON과 동일한 1,576개 분반을 표 형태로 확인하거나 분석할 때 사용한다.

### `courses/courses-lookup-2026-1.json`

- 출처: `/home/kdhoon/projects/DJSS/frontend/app/data/courses-lookup.json`
- 과목 검색과 자동완성을 위한 경량 데이터
- `category`가 없으므로 최적화 기준 데이터가 아니라 검색 인덱스 용도로 사용한다.

### `classrooms/classroom-sessions-2026-1.json`

- 출처: `/home/kdhoon/projects/DJGongsil/app/public/data.json`
- 325개 강의실과 1,693개 수업 세션
- 건물, 강의실, 수용인원, 요일, 시작·종료시간 포함
- 과목 데이터와 `(curiNo, clssNo)`를 결합키로 사용한다.

## 결합 현황

- 과목 카탈로그: 1,576개 분반
- 강의실 데이터: 1,342개 고유 분반
- 양쪽에서 일치하는 분반: 1,336개
- 과목 카탈로그 기준 강의실 결합률: 약 84.8%

두 출처는 같은 2026학년도 1학기 데이터지만 수집 시점과 포함 범위가 다르므로, 결합되지 않는 과목은 오류로 간주하지 않고 `room: null` 같은 형태로 처리한다.

## 사용 원칙

- 현재 파일은 자동 완성 알고리즘과 화면 프로토타입용 고정 fixture다.
- 실제 서비스 데이터는 학기별 디렉터리 또는 버전 필드를 사용해 교체한다.
- 수집 원본을 갱신할 때는 `manifest.json`의 레코드 수와 체크섬도 함께 갱신한다.
- 내부 식별자, 계정 정보, 쿠키 등 시간표 생성에 필요하지 않은 값은 이 프로젝트에 복사하지 않는다.
