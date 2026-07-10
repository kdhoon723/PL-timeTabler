# PL-timeTabler MVP 실행 계획

## 1. 요구사항 요약

### 확정된 방향

- 대상: 대진대학교 학생
- 주 사용 흐름: **수동 편집 우선**
- 자동화 범위: 선택한 과목을 존중하는 **보조 추천**
- 주요 사용 환경: 모바일 브라우저
- 진입 방식: 로그인과 온보딩을 요구하지 않고 첫 화면에서 바로 편집

현재 저장소에는 자동완성·충돌 검사·공강 최적화라는 제품 목표가 정의되어 있다(`README.md:5-12`). 2026학년도 1학기 과목 1,576개와 강의실 325개가 준비되어 있고(`README.md:14-23`), 과목·강의실 데이터는 `(curiNo, clssNo)`로 결합하며 84.8%가 연결된다(`data/README.md:39-53`, `data/manifest.json:36-43`).

### MVP에서 해결할 사용자 문제

1. 과목명이 정확히 기억나지 않아도 빠르게 찾는다.
2. 같은 과목의 여러 분반을 시간표에서 비교한다.
3. 충돌을 즉시 발견하고 대체 분반으로 해결한다.
4. 중요한 과목은 고정한 채 공강과 빈 시간을 개선한다.
5. 모바일에서 만든 시간표를 다시 방문해 이어서 수정한다.

### MVP 제외 범위

- 실제 수강신청 실행과 학교 계정 로그인
- 졸업요건·선수과목·학년 제한 판정
- 실시간 잔여석과 강의평
- 다학교 지원
- 사용자가 과목을 고르지 않아도 전체 시간표를 만드는 완전 자동 생성

## 2. 핵심 사용자 흐름

### 첫 방문

1. `/`에 접속하면 빈 시간표와 `과목 추가` 버튼이 바로 보인다.
2. 검색 시트를 열어 과목명·교수명·과목코드를 입력한다.
3. 검색 결과는 과목명으로 묶고 내부에서 분반과 시간을 비교한다.
4. 분반을 탭하면 즉시 시간표에 배치된다.
5. 충돌하면 추가를 막는 대신 충돌 원인과 가능한 대체 분반을 함께 보여준다.

### 시간표 개선

1. 사용자는 반드시 유지할 과목을 잠근다.
2. `공강 늘리기`, `빈 시간 줄이기`, `오전 수업 피하기` 조건을 선택한다.
3. 추천기는 잠긴 과목을 유지하고 변경 분반 수를 최소화한 후보 3개를 만든다.
4. 각 후보는 `무엇이 바뀌는지`와 `무엇이 좋아지는지`를 설명한다.
5. 적용 후 한 번의 실행 취소로 이전 시간표로 돌아갈 수 있다.

### 재방문과 공유

1. 선택 과목과 조건은 브라우저에 자동 저장된다.
2. 새로고침 후 마지막 편집 상태를 복원한다.
3. 공유 기능은 과목코드·분반만 포함하고 개인 정보는 포함하지 않는다.

## 3. 제품 및 기술 결정

### 앱 형태

- 프론트엔드: React + TypeScript
- 백엔드: Node.js 24 LTS + Fastify 5
- 데이터베이스: PostgreSQL 18 + Drizzle SQL migration
- 실행 환경: web, api, db, migration을 Docker Compose로 구성
- 과목 검색과 추천 계산은 브라우저에서 실행하고, API는 학기별 카탈로그·공유 링크·데이터 가져오기 이력을 담당한다.
- 사용자 계정은 만들지 않고 개인 편집 상태는 브라우저에 저장한다.
- 세부 근거와 서버 이동 계약은 `docs/ARCHITECTURE.md`를 따른다.

### 상태 모델

```text
Course
  courseCode, name, category, credits

Section
  courseCode, sectionCode, professor, sessions[], room?, capacity?

Session
  day, startMinute, endMinute, room?

DraftTimetable
  selectedSectionKeys[], lockedCourseCodes[], preferences, history[]
```

- 내부 식별키: `${curiNo}-${clssNo}`
- 강의실 데이터가 없는 15.2%의 분반은 정상 상태로 취급하고 `room: null`을 허용한다.
- 강의시간이 비어 있는 과목은 `시간 미정`으로 검색할 수 있지만 격자에는 배치하지 않는다.

### 추천기 원칙

- Hard constraints:
  - 수업시간 충돌 금지
  - 잠긴 과목과 분반 유지
  - 동일 과목 중복 선택 금지
- Soft constraints:
  - 변경 분반 수 최소화
  - 등교일 수 최소화
  - 수업 사이 빈 시간 합계 최소화
  - 사용자가 피하고 싶은 시간대 최소화
  - 강의실 정보가 있을 때 연속 수업 이동 부담 최소화
- 후보 정렬은 결정론적이어야 하며 같은 입력은 항상 같은 순서를 반환한다.

## 4. 구현 단계

### 단계 A — 모노레포·React/Fastify·Docker 스캐폴드

예정 파일:

- `package.json`
- `apps/web/src/main.tsx`
- `apps/web/src/styles/tokens.css`
- `apps/web/src/app/App.tsx`
- `apps/web/Dockerfile`
- `apps/api/src/server.ts`
- `apps/api/Dockerfile`
- `packages/contracts/`
- `packages/timetable-core/`
- `compose.yaml`
- `compose.dev.yaml`
- `.env.example`
- 테스트·린트·타입 검사 설정 파일

작업:

1. npm workspaces 기반으로 React 앱, Fastify API, 공유 타입, 핵심 도메인 패키지를 구성한다.
2. web, api, PostgreSQL, one-off migration 서비스를 Compose로 연결한다.
3. API healthcheck와 DB readiness를 정의한다.
4. 색상, 간격, 타이포, 레이어 토큰을 먼저 정의한다.
5. 360px 모바일을 기본 뷰포트로 앱 셸과 오류 경계를 만든다.
6. `DESIGN.md`의 접근성·반응형 계약을 테스트 기준으로 연결한다.

완료 조건:

- `dev`, `build`, `test`, `lint`, `typecheck` 명령이 독립적으로 성공한다.
- `docker compose up --build` 후 web, api, db healthcheck가 통과한다.
- `GET /api/health`가 DB 연결 상태를 포함해 성공한다.
- 360px에서 페이지 자체의 불필요한 가로 스크롤이 없다.
- 빈 상태에서 `과목 추가`가 첫 화면에 노출된다.

### 단계 B — 데이터 정규화와 시간 파서

예정 파일:

- `packages/data-pipeline/src/prepare-data.ts`
- `packages/timetable-core/src/course.ts`
- `packages/timetable-core/src/time.ts`
- `packages/timetable-core/src/__tests__/time.test.ts`
- `packages/contracts/src/catalog.ts`
- `apps/api/src/db/schema.ts`
- `apps/api/src/jobs/import-catalog.ts`
- `drizzle/`

작업:

1. 과목 카탈로그와 강의실 세션을 `(curiNo, clssNo)`로 결합한다.
2. `월11:30-13:30,수15:30-17:30` 같은 복수 시간 문자열을 `Session[]`으로 변환한다.
3. 카테고리를 교양필수·교양선택 영역·전공 학과 등 검색 가능한 구조로 정규화한다.
4. 레코드 수, 중복키, 잘못된 시간 범위, 학점 이상치를 검증하는 데이터 준비 명령을 만든다.
5. 정규화 결과를 PostgreSQL에 멱등하게 가져오고 import 이력과 입력 체크섬을 남긴다.
6. `GET /api/v1/catalog/:semester`가 브라우저 검색용 전체 카탈로그를 반환하도록 한다.
7. `data/manifest.json:4-43`의 레코드 수와 체크섬을 입력 검증 근거로 사용한다.

완료 조건:

- 과목 1,576개가 유실 없이 정규화된다.
- 강의실이 연결된 분반 수가 1,336개와 일치한다.
- 빈 시간 13개를 포함해 모든 레코드가 성공 또는 명시적 `시간 미정` 상태로 분류된다.
- 지원하는 모든 시간 문자열 fixture가 분 단위 범위로 변환된다.
- 동일 파일을 두 번 가져와도 과목·분반·세션이 중복되지 않는다.
- DB에서 조회한 레코드 수가 입력 manifest와 일치한다.

### 단계 C — 모바일 우선 수동 편집기

예정 파일:

- `apps/web/src/features/timetable/TimetableGrid.tsx`
- `apps/web/src/features/search/CourseSearchSheet.tsx`
- `apps/web/src/features/search/CourseResultGroup.tsx`
- `apps/web/src/features/selection/SelectedCourseList.tsx`
- `apps/web/src/features/timetable/editor-store.ts`

작업:

1. 시간표, 검색 바텀시트, 선택 과목 목록을 단일 편집 흐름으로 구현한다.
2. 과목명·교수명·과목코드 검색과 교양·전공 필터를 지원한다.
3. 같은 과목은 한 검색 결과로 묶고 분반을 시간·교수 정보와 함께 비교한다.
4. 과목 추가·삭제·분반 변경·잠금과 실행 취소를 구현한다.
5. 시각 시간표 외에 스크린리더용 요일별 목록을 제공한다.

완료 조건:

- 1,576개 데이터에서 검색 결과가 입력 후 100ms 이내 갱신된다.
- 검색 결과에서 두 번 이하의 탭으로 과목을 추가한다.
- 충돌하지 않는 과목은 즉시 격자와 총 학점에 반영된다.
- 360px 화면에서 과목 추가·삭제·분반 변경이 정밀 드래그 없이 가능하다.
- 키보드만으로 검색, 결과 이동, 분반 선택, 시트 닫기가 가능하다.

### 단계 D — 충돌 해결과 보조 추천

예정 파일:

- `packages/timetable-core/src/conflicts.ts`
- `packages/timetable-core/src/recommender.ts`
- `apps/web/src/features/recommendation/PreferenceChips.tsx`
- `apps/web/src/features/recommendation/SuggestionTray.tsx`
- `packages/timetable-core/src/__tests__/recommender.test.ts`

작업:

1. 세션 구간 교차를 기준으로 충돌 그래프를 생성한다.
2. 충돌 시 같은 과목의 가능한 대체 분반을 우선 제시한다.
3. 잠긴 과목을 유지하며 분반 조합을 탐색하는 추천기를 구현한다.
4. 후보별 등교일, 빈 시간, 이른 수업, 변경 분반 수, 이동 부담을 계산한다.
5. 상위 3개 후보의 변경점과 개선 효과를 자연어 템플릿으로 설명한다.

완료 조건:

- 충돌하는 시간 구간을 단위 테스트에서 100% 탐지한다.
- 잠긴 분반이 추천 과정에서 한 번도 변경되지 않는다.
- 동일 입력의 추천 후보와 순서가 반복 실행에서 일치한다.
- 일반적인 5~8과목 조합에서 추천이 모바일 기준 500ms 이내 완료된다.
- 추천 적용 후 한 번의 실행 취소로 원래 상태가 복원된다.

### 단계 E — 저장·공유·복원

예정 파일:

- `apps/web/src/features/persistence/draft-storage.ts`
- `apps/web/src/features/share/share-api.ts`
- `apps/web/src/features/persistence/__tests__/draft-storage.test.ts`
- `apps/api/src/routes/shares.ts`
- `apps/api/src/db/schema/shared-timetables.ts`

작업:

1. 편집 상태를 버전이 있는 로컬 스키마로 자동 저장한다.
2. 데이터 학기가 바뀌거나 분반이 사라진 경우 안전하게 부분 복원한다.
3. 공유 API에는 학기와 과목코드·분반·잠금만 전달하고 무작위 공유 ID를 반환한다.
4. 잘못되거나 오래된 공유 링크는 적용 가능한 과목과 누락 과목을 구분해 보여준다.
5. `scripts/backup.sh`와 `scripts/restore.sh`로 PostgreSQL 덤프·복원 절차를 자동화한다.

완료 조건:

- 새로고침 후 선택 과목, 잠금, 조건이 복원된다.
- 손상된 저장값이 있어도 앱이 빈 상태로 안전하게 실행된다.
- 공유 데이터에 교수명, 계정, 사용자 식별정보가 포함되지 않는다.
- 새 PostgreSQL 컨테이너에 덤프를 복원한 뒤 공유 시간표와 카탈로그 수가 일치한다.

### 단계 F — 모바일 QA와 사용자 검증

예정 파일:

- `e2e/mobile-editor.spec.ts`
- `e2e/recommendation.spec.ts`
- `docs/USABILITY_TEST.md`

작업:

1. 360px, 390px, 768px, 1440px 핵심 상태의 시각 회귀를 만든다.
2. 모바일 Safari와 Android Chrome에서 검색·시트·시간표 스크롤을 확인한다.
3. 접근성 자동검사와 키보드 시나리오를 실행한다.
4. 대진대 학생 5명 이상에게 첫 과목 추가, 5과목 시간표, 충돌 해결, 공강 개선 과제를 수행시킨다.
5. 실패 지점과 10초 이상 머뭇거린 지점을 기록해 한 번 이상 UX를 수정한다.

완료 조건:

- 핵심 E2E 시나리오가 모든 목표 뷰포트에서 통과한다.
- 접근성 검사에서 serious/critical 위반이 0건이다.
- 모바일 Lighthouse Performance와 Accessibility가 각각 90점 이상이다.
- 사용자 테스트 참여자의 80% 이상이 도움 없이 3분 내 5과목 시간표를 완성한다.

## 5. 수용 기준

| 영역 | 검증 가능한 기준 |
|---|---|
| 즉시 사용 | 로그인·온보딩 없이 첫 화면에서 과목 추가 가능 |
| 검색 | 이름·교수·코드 검색, 결과 갱신 100ms 이내 |
| 편집 | 추가·삭제·분반 변경·잠금·실행 취소 지원 |
| 충돌 | 겹치는 모든 세션을 감지하고 대체 분반 제시 |
| 추천 | 잠금 유지, 후보 3개 이하, 변경 이유와 개선 수치 표시 |
| 저장 | 새로고침 후 상태 복원, 손상 데이터 안전 처리 |
| 모바일 | 360px부터 핵심 기능 사용 가능, 터치 대상 44px 이상 |
| 접근성 | WCAG 2.2 AA 목표, serious/critical 자동 위반 0건 |
| 성능 | 검색 100ms, 일반 추천 500ms, 모바일 Lighthouse 90점 이상 |
| 사용성 | 학생 5명 중 80% 이상이 3분 안에 5과목 시간표 완성 |

## 6. 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| 과목·강의실 데이터 불일치 | 일부 이동 추천 부정확 | 강의실을 선택 필드로 취급하고 결측을 명시 |
| 모바일 시간표 정보 과밀 | 과목명이 읽히지 않음 | 격자는 축약, 상세는 탭 시 시트에서 표시 |
| 자유 드래그의 오조작 | 모바일 편집 실패 | 탭 기반 분반 교체를 기본으로 하고 드래그는 필수 기능에서 제외 |
| 추천이 선택을 과도하게 변경 | 신뢰 하락 | 잠금, 변경 수 패널티, 변경 전후 비교, 실행 취소 제공 |
| 학기 데이터 갱신 시 파서 파손 | 출시 직전 데이터 반영 실패 | 데이터 준비 명령과 형식 fixture를 CI에서 실행 |
| 완전 자동 기능으로 범위 확장 | 핵심 편집기 완성도 저하 | MVP는 보조 추천까지만 포함하고 전체 자동 생성은 별도 마일스톤으로 고정 |

## 7. 검증 순서

1. 데이터 준비 명령으로 레코드 수·결합률·시간 파싱을 검증한다.
2. 충돌과 추천기 단위 테스트로 핵심 도메인 로직을 고정한다.
3. 컴포넌트 테스트로 검색·추가·분반 변경·실행 취소를 검증한다.
4. 모바일 E2E로 첫 방문부터 추천 적용·복원까지 검증한다.
5. 접근성·성능·시각 회귀를 실행한다.
6. 실제 학생 사용성 테스트 후 기준을 충족할 때 MVP를 종료한다.

## 8. 권장 실행 순서와 중단 조건

- 구현 순서: A → B → C → D → E → F
- C 단계가 실제 모바일에서 사용 가능하기 전에는 추천 기능을 확장하지 않는다.
- 데이터 파서와 충돌 검사가 검증되기 전에는 추천 점수를 조정하지 않는다.
- 사용자 테스트의 3분 내 완성률 80%와 모바일 핵심 E2E가 통과하면 MVP 완료로 판단한다.
