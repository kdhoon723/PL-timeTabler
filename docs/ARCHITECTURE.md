# PL-timeTabler Architecture

## 상태와 원칙

- 결정일: 2026-07-10
- 상태: 제품 아키텍처 채택
- 제품 범위: 대진대학교 전용, 수동 편집 우선, 자동 시간표 생성과 졸업요건 안내 포함
- 품질 원칙: 시험용 MVP를 버릴 구조가 아니라 출시·운영할 구조를 처음부터 만든다.
- 이식 목표: 현재 서버에서 개발·검증한 스택을 다른 Docker 호스트에서도 같은 이미지·설정·스키마·데이터로 실행한다.

완성도는 기능을 한 번에 모두 구현한다는 뜻이 아니다. 구현은 검증 가능한 세로 단위로 나누되, 컨테이너 경계·데이터 모델·API 계약·디자인 시스템·테스트 기준은 최종 제품을 기준으로 고정한다.

## 최종 기술 선택

| 영역 | 선택 | 이유 |
|---|---|---|
| 프론트엔드 | React + TypeScript | 모바일 편집 UI, 접근성 높은 상호작용, 로컬 검색·오프라인 편집 |
| API | Python + FastAPI | 최적화·데이터 파이프라인과 언어 통일, 검증 모델, OpenAPI 자동 생성 |
| 최적화 | Python + OR-Tools CP-SAT | 시간 충돌·필수과목·학점·공강·시간대 선호를 hard/soft constraint로 모델링 |
| 데이터베이스 | PostgreSQL 18 | 학기·과목·분반·교육과정·규칙 버전·최적화 작업을 관계형 구조로 관리 |
| DB 접근 | SQLAlchemy 2 + Alembic | Python 도메인 모델과 명시적인 버전 마이그레이션 유지 |
| API 계약 | OpenAPI 3.1 → 생성된 TypeScript SDK | Python과 React 사이 요청·응답 타입의 수동 중복 제거 |
| 배포 | Docker Compose | web, api, optimizer, db, migrate, ingest를 한 선언으로 재현 |
| 웹 진입점 | Nginx 기반 React 정적 이미지 | 정적 파일 제공, `/api` 동일 출처 프록시, 캐시·압축 제어 |

Python과 모든 패키지는 호환성이 확인된 안정 버전으로 lockfile과 이미지 digest를 고정한다. PostgreSQL은 18.x 보안·버그 수정 패치를 계획적으로 반영한다.

## Python 서버가 적합한 이유

Python이 Go보다 HTTP 처리 자체가 빠르기 때문에 선택한 것이 아니다. Go는 높은 동시성과 작은 정적 바이너리에 강하고, 순수 API 처리량만 비교하면 더 유리할 수 있다. 이 제품에서는 다음이 더 중요하다.

1. OR-Tools는 공식적으로 C++, Python, Java, C#을 지원하며 Go·JavaScript 바인딩은 제공하지 않는다.
2. Node 또는 Go API를 선택해도 완전 자동 생성에는 Python optimizer가 추가되어 백엔드 언어와 배포 경계가 늘어난다.
3. Python API를 사용하면 수집·정규화·학사규칙·최적화 입력 모델을 한 코드베이스에서 공유할 수 있다.
4. FastAPI의 OpenAPI에서 TypeScript SDK를 생성하므로 프론트와 같은 언어를 쓰지 않아도 계약의 타입 안전성을 유지할 수 있다.

Python의 약점은 구조로 격리한다.

- DB·네트워크 중심 API는 비동기 I/O와 연결 풀을 사용한다.
- API 컨테이너는 여러 프로세스 또는 여러 replica로 확장한다.
- CPU를 오래 사용하는 OR-Tools 계산은 API 이벤트 루프에서 실행하지 않고 별도 `optimizer` 컨테이너가 처리한다.
- API 처리량과 solver 지연은 실제 1,576개 과목 fixture로 부하 테스트해 회귀 기준을 고정한다.

OR-Tools의 핵심 solver는 C++로 구현되고 Python은 모델링 API를 제공하므로, 시간표 탐색의 주된 계산이 순수 Python 반복문에만 묶이지 않는다. 반대로 검색·충돌 미리보기처럼 즉시 반응해야 하는 작은 계산은 TypeScript로 브라우저에서 수행한다.

## 대안 검토

### Go API + Python optimizer

- 장점: 높은 API 동시성, 낮은 메모리 사용, 단순한 정적 바이너리 배포.
- 제외 이유: React TypeScript + Go API + Python optimizer의 세 언어를 운영해야 한다. 대진대 단일 학교 규모에서 API 처리량보다 학사규칙·최적화 정확도와 개발 일관성이 우선이다.
- 재검토 조건: 최적화와 무관한 API 트래픽이 측정상 병목이고 수평 확장보다 런타임 비용 절감이 중요한 경우.

### Node.js + Fastify API + Python optimizer

- 장점: 프론트와 TypeScript 사용, 높은 I/O 처리량, 익숙한 웹 생태계.
- 제외 이유: 완전 자동 생성을 처음부터 포함하면 Python 서비스가 어차피 필요하다. OpenAPI SDK로 프론트 계약을 해결할 수 있으므로 Node를 별도로 유지할 이점이 작다.

### Python 단일 프로세스

- 장점: 가장 단순한 실행 구조.
- 제외 이유: CPU-bound solver가 API 응답을 막고 장애·재시도·시간 제한 경계가 흐려진다. 같은 코드와 이미지는 공유하되 API와 optimizer 프로세스를 분리한다.

### Redis/Celery 큐

- 장점: 검증된 분산 작업 큐와 재시도 기능.
- 현재 제외 이유: 초기 단일 서버에서 별도 영속 서비스가 늘어난다. PostgreSQL의 `optimization_jobs`를 내구성 있는 작업 상태 저장소로 사용하고, 실제 처리량이 요구할 때 큐를 교체할 수 있도록 worker 인터페이스를 분리한다.

## 저장소 구조

```text
PL-timeTabler/
├── apps/
│   ├── web/                       # React 앱, 생성 SDK, Nginx 이미지
│   └── backend/                   # FastAPI와 공용 Python 도메인
│       ├── src/timetabler/api/
│       ├── src/timetabler/catalog/
│       ├── src/timetabler/curriculum/
│       ├── src/timetabler/optimizer/
│       └── tests/
├── data/
│   ├── courses/                   # 학기별 개설과목 fixture
│   ├── classrooms/               # 강의실 세션 fixture
│   └── requirements/              # 공식 졸업요건 원문·정규화 결과
├── migrations/                    # Alembic revision
├── contracts/                     # 커밋된 OpenAPI snapshot과 생성 설정
├── e2e/                           # 모바일·접근성·자동생성 E2E
├── scripts/                       # import, backup, restore, deploy
├── compose.yaml
├── compose.dev.yaml
└── .env.example
```

`api`, `optimizer`, `migrate`, `ingest`는 같은 backend 소스와 이미지를 사용하되 서로 다른 명령으로 실행한다. 같은 이미지라는 것은 역할을 한 프로세스에 섞는다는 뜻이 아니라 의존성과 코드를 동일하게 재현한다는 뜻이다.

## 컨테이너 구성

프론트·백엔드·DB를 한 이미지에 넣지 않는다.

```text
browser
  │
  ▼
web :80 ───────── React 정적 파일 / /api 프록시
  │
  ▼
api :8000 ─────── FastAPI ─────────────┐
  │                                    │
  ▼                                    ▼
db :5432 ──────── PostgreSQL ◀──── optimizer worker + OR-Tools
                       ▲
                       ├──── migrate  (backend 이미지, one-off)
                       └──── ingest   (backend 이미지, one-off)
```

- `web`: React 빌드 결과, Nginx, 정적 카탈로그 캐시와 동일 출처 프록시.
- `api`: 카탈로그·요건·공유·최적화 작업 API. solver를 직접 실행하지 않는다.
- `optimizer`: PostgreSQL에서 작업을 점유하고 OR-Tools를 실행한 뒤 후보와 설명 근거를 저장한다.
- `db`: 공식 PostgreSQL 이미지와 named volume. 호스트 포트는 기본 공개하지 않는다.
- `migrate`: Alembic upgrade를 일회 실행한다.
- `ingest`: 공식 원문 검증·정규화·원자적 데이터 버전 전환을 수행한다.

## API 경계

주요 API는 `/api/v1` 아래 버전을 명시한다.

- `GET /health/live`, `GET /health/ready`: 프로세스와 DB 준비 상태
- `GET /semesters`: 사용 가능한 학기와 데이터 버전
- `GET /catalog/{semester}`: 브라우저 검색용 정규화 카탈로그
- `GET /curricula`: 입학연도·학과·전공방식별 졸업요건
- `GET /curricula/{id}/sources`: 적용 규칙의 공식 원문·페이지·갱신일
- `POST /optimizations`: 후보과목·고정과목·학점·선호조건으로 작업 생성
- `GET /optimizations/{id}`: `QUEUED/RUNNING/FEASIBLE/INFEASIBLE/TIME_LIMIT/FAILED` 상태와 후보 조회
- `DELETE /optimizations/{id}`: 대기·실행 작업 취소 요청
- `POST /shares`, `GET /shares/{id}`: 최소 정보로 시간표 공유·복원

FastAPI가 생성한 OpenAPI 3.1 문서를 CI에서 snapshot으로 검증하고 TypeScript SDK를 생성한다. breaking change는 API 버전 또는 명시적 migration 없이 병합하지 않는다.

## 데이터 모델

### 강의 카탈로그

- `semesters`: 학기, 공개일, 활성 버전, 원문 체크섬
- `courses`: 과목코드, 과목명, 학점, 이수구분, 영역
- `sections`: 분반, 교수, 정원 정보 유무, 시간 미정 여부
- `sessions`: 요일, 시작·종료 분, 강의실
- `rooms`: 건물, 호실, 좌표 또는 이동 그룹
- `data_imports`: source URL, fetched_at, checksum, parser version, 결과와 오류

### 졸업요건

- `academic_units`: 단과대·학부·학과·전공, 유효기간, 명칭 변경 관계
- `curriculum_versions`: 입학연도 범위, 학과, 학위과정, 근거 문서 버전
- `requirement_groups`: 총학점·교양필수·교양영역·전공기초·전공필수·전공선택·다전공
- `requirement_rules`: 최소/최대 학점, 필수 과목 집합, 선택 개수, AND/OR 그룹, 예외 조건
- `course_equivalencies`: 폐지·대체·동일 교과목과 유효기간
- `graduation_assessments`: 논문·시험·실기·작품·인증과 적용 대상
- `source_documents`: 공식 URL, 문서명, 시행일, 페이지·조항, checksum, 검증 상태

모든 판정은 `curriculum_version_id`와 `source_document_id`를 추적한다. 공개 원문으로 확정하지 못한 학과 규칙은 `UNVERIFIED`로 저장하고 사용자에게 확정 충족으로 표시하지 않는다.

### 사용자 입력과 최적화

- `draft_timetables`: 익명 공유가 필요할 때만 최소 선택 상태 저장
- `optimization_jobs`: 입력 snapshot, 상태, 시도 횟수, deadline, 취소 시각, 오류 코드
- `optimization_candidates`: 선택 분반, 목적함수 구성값, 변경 설명

개인 이수내역은 기본적으로 브라우저에 저장한다. 서버 저장 또는 성적표 가져오기를 추가할 때는 명시적 동의·삭제·암호화 정책을 먼저 정의한다.

## 최적화 모델

### Hard constraints

- 수업시간 충돌 금지
- 동일 과목 중복 금지
- 사용자가 잠근 분반 유지
- 필수로 지정한 과목 또는 요건 그룹 충족
- 희망 최소·최대 학점
- 학년·학과·선수과목 제한은 근거가 검증된 경우에만 적용

### Soft constraints

- 등교일 최소화와 지정 공강일 우선
- 수업 사이 빈 시간 최소화
- 이른/늦은 수업과 특정 요일 회피
- 연속 수업 이동 부담 최소화
- 사용자가 선택한 과목·교수·분반 변경 최소화
- 여러 후보의 다양성 확보

점수는 단일 불투명 숫자만 보여주지 않는다. 후보마다 등교일, 총 빈 시간, 첫 수업 시각, 변경 과목, 미충족 선호를 별도로 반환한다. solver에는 시간 제한과 결정론적 seed를 적용하고 `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `TIME_LIMIT`을 구분한다.

브라우저는 빠른 충돌 검사와 수동 분반 추천을 즉시 수행할 수 있지만, 공식 자동 생성 결과는 서버 optimizer가 만든다. 두 구현은 동일한 시간 구간 규칙 fixture로 교차 검증한다.

## 졸업요건 데이터 갱신 계약

1. 공식 공개 원문만 수집하고 URL·게시일·시행일·checksum을 보존한다.
2. 원문은 immutable raw 영역에 저장하고 정규화 결과와 parser version을 분리한다.
3. 자동 파싱 결과는 schema·교차합계·필수과목 존재 여부를 검사한다.
4. 변경 diff를 사람이 승인한 뒤 새 `curriculum_version`을 활성화한다.
5. 과거 입학연도 규칙을 덮어쓰지 않고 유효기간으로 병존시킨다.
6. 화면에 데이터 기준일과 공식 원문 링크를 제공한다.

## 서버 이식과 운영 계약

동일한 실행 결과에는 다음이 모두 필요하다.

1. **이미지:** base image digest, Python·Node 도구와 모든 의존성 lockfile
2. **설정:** 서버 차이는 환경변수와 secret에만 두고 `.env.example`에 키 목록 유지
3. **스키마:** 모든 변경을 Alembic migration으로 커밋
4. **데이터:** `pg_dump --format=custom`과 검증된 `pg_restore`
5. **원문:** 졸업요건·카탈로그 source checksum과 parser version

CI는 lint, typecheck, unit, contract, migration, parser fixture, E2E, 접근성, 이미지 취약점 검사를 실행한다. 배포 이미지는 커밋 SHA로 태그하고 healthcheck 실패 시 이전 이미지로 되돌릴 수 있어야 한다.

운영에서는 구조화 로그에 request/job ID를 포함하고, API latency·오류율·optimizer queue time·solve time·import 실패를 측정한다. 비밀값과 개인 이수내역은 로그에 남기지 않는다.

## 백업·복구 기준

- 배포와 데이터 활성화 전 `pg_dump --format=custom` 자동 백업
- 최소 7개 최근 백업과 월 단위 장기 백업 정책
- 주 1회 임시 DB로 실제 복원하고 레코드 수·checksum·migration head 검증
- raw PostgreSQL volume은 같은 호스트의 지속성 수단일 뿐 서버 간 백업으로 간주하지 않음
- 공식 원문 raw 데이터와 정규화 manifest도 DB와 함께 버전 보존

## 출시 아키텍처 완료 조건

- 새 Docker 호스트에서 Compose, `.env`, DB dump, source data로 동일 스택 복원
- API와 optimizer 장애가 서로의 프로세스를 중단시키지 않음
- 1,576개 강의 fixture와 학사규칙 fixture로 결과가 결정론적으로 재현됨
- OpenAPI snapshot과 생성 TypeScript SDK가 일치함
- migration upgrade·downgrade 또는 명시적 forward-fix 절차가 검증됨
- 부하 테스트에서 API와 solver의 목표 SLO를 만족하거나 병목 근거가 기록됨
- 모든 졸업요건 판정에서 적용 버전과 공식 출처를 추적 가능

## 참고

- [FastAPI server workers](https://fastapi.tiangolo.com/deployment/server-workers/)
- [FastAPI Docker deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [FastAPI TypeScript SDK generation](https://fastapi.tiangolo.com/advanced/generate-clients/)
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic migration tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [OR-Tools installation and supported languages](https://developers.google.com/optimization/install/)
- [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [Docker Compose production guidance](https://docs.docker.com/compose/how-tos/production/)
