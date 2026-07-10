# PL-timeTabler Architecture

## 상태

- 결정일: 2026-07-10
- 상태: MVP 기준 채택
- 목표: 현재 서버에서 개발·검증한 전체 스택을 다른 Docker 호스트에서도 같은 방식으로 실행

## 기술 선택

| 영역 | 선택 | 이유 |
|---|---|---|
| 프론트엔드 | React + TypeScript | 모바일 편집 UI와 상태 중심 상호작용, 프론트·백엔드 계약 공유 |
| 백엔드 | Node.js 24 LTS + Fastify 5 | 프론트와 언어 통일, 작은 런타임, 명시적 스키마 기반 API, NestJS보다 낮은 초기 복잡도 |
| 데이터베이스 | PostgreSQL 18 | 학기·과목·분반·수업 세션·공유 시간표를 관계형 구조로 관리하고 향후 확장 가능 |
| DB 접근 | Drizzle ORM + SQL migration | TypeScript 스키마와 검토 가능한 SQL 마이그레이션을 함께 유지 |
| 배포 | Docker Compose | web, api, db, migration을 하나의 선언으로 개발·테스트·단일 서버 배포에 재사용 |
| 웹 진입점 | Nginx 기반 React 정적 이미지 | React 빌드 결과 제공과 `/api` 동일 출처 프록시 |

런타임은 Current가 아니라 LTS만 사용한다. 2026-07-10 기준 Node.js 공식 지원표에서 24는 LTS이고, Fastify 5는 공식 LTS 정책이 적용되는 최신 메이저다. PostgreSQL은 지원 기간이 긴 18 메이저를 고정하고 최신 18.x 패치를 계획적으로 반영한다.

## 대안 검토

### NestJS

- 장점: 모듈·DI·가드 등 대형 애플리케이션 규칙이 풍부하다.
- 제외 이유: 현재 API는 카탈로그, 공유, 상태 확인, 데이터 가져오기 정도로 작다. 초기 보일러플레이트와 프레임워크 규칙이 제품 검증 속도를 낮춘다.

### Python FastAPI

- 장점: 향후 Python 기반 최적화·데이터 분석 코드와 결합하기 쉽다.
- 제외 이유: 현재 추천기는 브라우저에서도 실행되어야 하며 React와 도메인 타입을 공유하는 편이 유리하다. 별도 Python 서비스는 실제로 Python 전용 계산이 필요해질 때 추가한다.

### 백엔드 없음

- 장점: 가장 빠르고 배포가 단순하다.
- 제외 이유: 학기 데이터 버전 관리, 공유 링크, 가져오기 이력과 향후 운영 작업을 추가하면 정적 파일만으로는 관리 경계가 흐려진다.

### SQLite

- 장점: 단일 파일이라 작은 단일 서버에 간단하다.
- 제외 이유: 공유 기능과 데이터 갱신 작업을 병행하고 향후 서버 확장을 고려하면 PostgreSQL을 처음부터 쓰는 편이 DB 재마이그레이션 위험이 작다.

## 저장소 구조

```text
PL-timeTabler/
├── apps/
│   ├── web/                  # React 앱과 Nginx 이미지
│   └── api/                  # Fastify API, DB schema, import job
├── packages/
│   ├── contracts/            # API request/response와 공유 도메인 타입
│   ├── timetable-core/       # 시간 파서, 충돌 검사, 추천기
│   └── data-pipeline/        # 원본 검증·정규화
├── data/                     # 수집한 학기별 원본 fixture
├── drizzle/                  # 버전 관리되는 SQL migration
├── scripts/
│   ├── backup.sh
│   ├── restore.sh
│   └── deploy.sh
├── compose.yaml              # 서버와 CI에서 사용하는 기본 스택
├── compose.dev.yaml          # 소스 마운트·개발 서버 등 개발 전용 차이
└── .env.example
```

npm workspaces로 앱과 공유 패키지를 관리한다. 프론트와 백엔드는 `packages/contracts`의 타입 계약을 공유하고, 핵심 시간표 계산은 `packages/timetable-core`에서 한 번만 구현한다.

## 컨테이너 구성

```text
client
  │
  ▼
web :80 ─────── React 정적 파일
  │ /api/*
  ▼
api :3000 ───── Fastify
  │
  ▼
db :5432 ────── PostgreSQL named volume

migrate ─────── api 이미지의 one-off migration command
```

### `web`

- 다단계 빌드에서 React를 빌드하고 최종 이미지에는 정적 결과와 Nginx 설정만 포함한다.
- `/api`를 `api:3000`으로 프록시해 CORS 설정 없이 동일 출처로 제공한다.
- 운영에서는 소스 디렉터리를 bind mount하지 않는다.

### `api`

- `GET /api/health`: 프로세스와 DB 연결 상태
- `GET /api/v1/semesters`: 사용 가능한 학기
- `GET /api/v1/catalog/:semester`: 브라우저가 로컬 검색에 사용할 전체 정규화 카탈로그
- `POST /api/v1/shares`: 과목코드·분반·잠금 상태만 저장
- `GET /api/v1/shares/:id`: 공유 시간표 복원
- 데이터 갱신은 공개 관리자 API 대신 컨테이너 내부 one-off import 명령으로 수행한다.

### `db`

- 외부 호스트 포트를 기본 공개하지 않고 Compose 내부 네트워크에서만 접근한다.
- 데이터는 named volume에 유지한다.
- 스키마 변경은 `drizzle/`의 SQL migration으로만 수행하고 운영에서 schema push를 사용하지 않는다.

## 초기 데이터 모델

- `semesters`: 학기, 활성 여부, 공개일, 데이터 버전
- `courses`: 학기별 과목코드, 과목명, 이수구분, 학점
- `sections`: 분반, 교수명, 시간 미정 여부
- `sessions`: 요일, 시작·종료 분, 강의실
- `rooms`: 건물, 호실, 수용인원
- `shared_timetables`: 무작위 공유 ID, 학기, 선택 분반과 잠금, 만료·생성 시각
- `data_imports`: 입력 체크섬, 레코드 수, 성공·실패 결과

MVP에는 사용자 계정 테이블을 만들지 않는다. 개인 편집 상태는 브라우저에 저장하고 공유할 때만 최소 데이터가 서버에 저장된다.

## 서버 이식 계약

컨테이너만 옮기는 것으로는 DB 상태가 따라오지 않는다. 다음 네 가지를 함께 고정한다.

1. **이미지:** base image와 애플리케이션 의존성을 버전과 lockfile로 고정한다.
2. **설정:** 서버별 차이는 `.env`에만 두고 `.env.example`에 키 목록을 유지한다.
3. **스키마:** 모든 변경을 `drizzle/` SQL migration으로 커밋한다.
4. **데이터:** raw volume 복사보다 `pg_dump`와 `pg_restore`를 기본 이동 방식으로 사용한다.

새 서버 이동 절차:

```bash
git clone git@github.com:kdhoon723/PL-timeTabler.git
cd PL-timeTabler
cp .env.example .env
# 비밀값 입력
docker compose build
docker compose up -d db
docker compose run --rm migrate
./scripts/restore.sh backups/latest.dump   # 기존 데이터가 있을 때
docker compose up -d
docker compose ps
```

정확히 같은 빌드 결과가 필요해지면 CI가 커밋 SHA 태그로 `web`과 `api` 이미지를 GHCR에 게시하고, 서버는 빌드 대신 해당 이미지를 pull한다.

## 개발·운영 Compose 분리

- `compose.yaml`: 운영과 CI에 가까운 기본 구성, 소스 코드는 이미지 안에 포함
- `compose.dev.yaml`: 개발 서버, 소스 bind mount, 상세 로그만 추가
- 운영 실행: `docker compose up -d`
- 개발 실행: `docker compose -f compose.yaml -f compose.dev.yaml up --build`

Docker 공식 문서가 권장하는 것처럼 운영에서는 애플리케이션 코드 bind mount를 제거하고 환경별 차이는 추가 Compose 파일과 환경변수로 제한한다.

## 백업·복구 기준

- `scripts/backup.sh`: `pg_dump --format=custom`으로 날짜별 덤프 생성
- `scripts/restore.sh`: 빈 DB에 `pg_restore` 후 migration 상태 확인
- 배포 전 자동 백업, 최소 7개 최근 백업 보관
- 주 1회 임시 DB에 실제 복원하는 검증 작업 추가
- raw PostgreSQL volume은 같은 호스트의 지속성 수단이지 서버 간 백업 형식으로 간주하지 않는다.

## 배포 완료 조건

- 새 디렉터리에서 `.env`와 DB 덤프만으로 스택을 재구성할 수 있다.
- `docker compose config`가 오류 없이 렌더링된다.
- 모든 서비스가 healthcheck를 통과한다.
- 백업을 임시 DB에 복원한 뒤 학기·과목·분반 레코드 수가 원본과 일치한다.
- 같은 E2E 테스트가 현재 서버와 새 Docker 호스트에서 모두 통과한다.

## 참고

- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [Fastify TypeScript reference](https://fastify.dev/docs/latest/Reference/TypeScript/)
- [Fastify LTS policy](https://fastify.dev/docs/latest/Reference/LTS/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [Docker Compose production guidance](https://docs.docker.com/compose/how-tos/production/)
- [Docker Compose volumes](https://docs.docker.com/reference/compose-file/volumes/)
- [Drizzle migration workflow](https://orm.drizzle.team/docs/drizzle-kit-migrate)
