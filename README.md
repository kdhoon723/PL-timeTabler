# PL-timeTabler

[![CI](https://github.com/kdhoon723/PL-timeTabler/actions/workflows/ci.yml/badge.svg)](https://github.com/kdhoon723/PL-timeTabler/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/demo-timetabler.kdhoon.me-2563eb)](https://timetabler.kdhoon.me)

대진대학교 수강신청 전에 모바일과 데스크톱에서 과목을 고르고, 충돌 없는 시간표 후보를 자동으로 만드는 비공식 시간표 설계 도구입니다. 수동 편집을 우선하고 OR-Tools가 사용자의 선택과 생활 패턴을 보조합니다.

> **중요:** 이 서비스는 대진대학교의 공식 서비스가 아닙니다. 개설과목과 졸업요건 결과는 참고용이며, 실제 수강신청 전 학교 포털·최신 교육과정편람·소속 학과 안내를 반드시 확인해야 합니다.

## 바로 사용하기

- 서비스: <https://timetabler.kdhoon.me>
- 로그인 없이 시간표 작성, 자동완성, 저장, 공유와 내보내기를 사용할 수 있습니다.
- 선택형 학교 이메일 OTP 로그인은 운영 환경에 메일 발송 자격 증명이 구성된 경우에만 표시됩니다.

## 주요 기능

- 2026-1 개설과목 1,576개를 과목명·교수·과목코드·이수구분·요일로 검색
- 현재 시간표와 자동완성 후보 바구니를 분리하고, 후보는 분반 선택 없이 과목 단위로 담아 조합
- 드래그 앤 드롭, 분반 추가·교체·삭제, 필수·희망·예비·제외 역할, 실행 취소·다시 실행
- 시간 충돌이 있을 때만 경고하고 대체 가능한 다른 분반 제안
- 정수 목표·최소·최대 학점, 공강 요일, 이른/늦은 수업, 점심 여유, 하루 수업시간, 공강 길이·현재 선택 유지 선호
- OR-Tools CP-SAT 기반 결정론적 후보 3개와 등교일·공강·첫/마지막 수업·미반영 조건 설명
- 입학연도와 46개 교육과정 단위별 공식 졸업요건 출처 안내
- 첫 방문에서 학과·입학연도·학년을 단계별로 설정하거나 즉시 건너뛰는 모바일 온보딩
- 2026 신입학 교육과정에서 정규화한 31개 교육과정 단위·113개 전공필수와 교양필수의 실제 개설 분반 연결
- 브라우저 자동 저장, URL 공유, PNG·인쇄/PDF 내보내기, 수강신청용 예비 분반 체크리스트
- 모바일 바텀시트, 키보드 접근성, 명시적 라이트·다크 테마, PWA 설치와 오프라인 직접 경로 fallback
- 요청별 rate limit, 활성 작업 상한, lease 복구·취소·만료 정리로 공개 optimizer 보호

## 구조

```text
browser → Nginx/React web → FastAPI → PostgreSQL ← OR-Tools worker
                                  └── versioned catalog files
```

프론트, API/optimizer, DB는 한 이미지에 섞지 않습니다. `compose.yaml`이 다음 서비스를 같은 방식으로 재현합니다.

| 서비스 | 역할 |
| --- | --- |
| `web` | React 정적 앱과 Nginx reverse proxy |
| `api` | FastAPI 카탈로그·인증·최적화 API |
| `optimizer` | OR-Tools CP-SAT 작업 처리 |
| `db` | PostgreSQL 영속 저장소 |
| `migrate` | Alembic 스키마 마이그레이션 |
| `ingest` | 배포 전 데이터 검증 release gate |

기술 선택과 경계는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), 저장소별 데이터
흐름과 HTTP 계약은 [`docs/API_SPEC.md`](docs/API_SPEC.md)에 정리되어 있습니다.

## 로컬 실행

### 요구 사항

- Docker Engine
- Docker Compose v2
- 외부 reverse proxy를 연결하려는 경우 Compose에서 사용하는 Docker network

```bash
git clone https://github.com/kdhoon723/PL-timeTabler.git
cd PL-timeTabler
cp .env.example .env

# .env의 POSTGRES_PASSWORD를 긴 무작위 값으로 교체
docker network create kdhoon-public 2>/dev/null || true
docker compose up -d --build
curl http://127.0.0.1:18080/api/v1/health/ready
```

기본 웹 주소는 <http://127.0.0.1:18080>이며 DB는 호스트에 공개하지 않습니다. 다른 서버에서도 저장소, `.env`, Docker와 Compose만 있으면 같은 스택을 실행할 수 있습니다.

주요 환경 변수는 [`.env.example`](.env.example)에 있습니다. `.env`와 운영 자격 증명은 Git에서 제외됩니다.

### 선택형 학교 이메일 로그인

로그인은 시간표 편집의 선행 조건이 아닙니다. 활성화하려면 소유한 발신 도메인을 Resend에서 검증하고 `.env`에 다음 값을 설정합니다. API 키와 HMAC secret은 저장소에 커밋하지 않습니다.

```dotenv
TIMETABLER_AUTH_ENABLED=true
TIMETABLER_AUTH_HMAC_SECRET=<32바이트 이상의 무작위 비밀값>
TIMETABLER_AUTH_EMAIL_PROVIDER=resend
TIMETABLER_AUTH_RESEND_API_KEY=<Resend API key>
TIMETABLER_AUTH_RESEND_FROM=PL-timeTabler <login@검증한-발신-도메인>
```

서버는 입력한 학번으로 `학번@daejin.ac.kr`을 생성하고 6자리 코드를 보냅니다. 코드는 5분 후 만료되고 5회 실패 시 폐기되며, 재전송은 60초로 제한합니다. 세션은 원문 토큰을 저장하지 않는 `Secure`·`HttpOnly`·`SameSite=Lax` 쿠키를 사용합니다.

### Cloudflare Tunnel 예시

현재 Compose는 `kdhoon-public` 외부 네트워크를 사용합니다. `cloudflared`를 같은 네트워크에 연결하고 다음처럼 origin을 지정할 수 있습니다.

```yaml
- hostname: timetable.example.com
  service: http://timetabler-web:80
```

DNS CNAME 대상은 Cloudflare가 해당 계정에 발급한 `<tunnel-id>.cfargotunnel.com`을 사용합니다. 터널 토큰과 계정 자격 증명은 저장소에 넣지 않습니다.

## 데이터와 정확성 경계

- 과목·강의실 snapshot과 졸업요건 정규화 결과는 공개된 학교 자료를 기반으로 합니다.
- 학생 계정, 쿠키, 개인 이수내역과 내부 교번은 데이터셋에 포함하지 않습니다.
- 교수명·강의시간·강의실처럼 공개 강의정보에 포함된 항목만 시간표 생성에 사용합니다.
- 데이터 수집 시점과 학교 시스템의 최신 상태가 다를 수 있습니다. 이 저장소의 판정은 공식 수강신청·졸업 판정을 대체하지 않습니다.
- 원문 자료의 권리는 각 원저작자·제공기관에 있으며, 재사용 시 원문 사이트의 이용 조건을 확인해야 합니다.

상세 출처, 변환 과정, checksum과 현재 제한은 [`data/README.md`](data/README.md)와 [`data/requirements/README.md`](data/requirements/README.md)를 참고하세요.

## 데이터 갱신

새 강의계획서나 개설과목 snapshot은 기존 파일을 직접 덮어쓰지 않고 별도 staging에서 준비합니다.

1. `data/courses`, `data/classrooms`, `data/requirements`에 새 학기 원본과 정규화 결과를 둡니다.
2. `data/manifest.json`의 레코드 수와 SHA-256 checksum을 갱신합니다.
3. canonical API snapshot에서 브라우저 fallback을 다시 생성합니다.
4. 아래 release gate가 통과한 뒤 새 이미지를 빌드합니다.

```bash
uv --directory apps/backend run timetabler-validate-data
uv --directory apps/backend run timetabler-export-static-catalog
docker compose --profile ingest run --rm --build ingest
```

API와 정적 fallback은 과목·강의실 checksum을 합친 같은 `datasetVersion`과 1,576개 분반의 동일한 세션 의미를 사용합니다. API는 이 버전을 최적화 요청과 함께 검증하므로 브라우저의 오래된 데이터와 새 카탈로그가 섞이지 않습니다.

전공필수 snapshot은 `python3 scripts/extract-major-required.py`로 2026 편람의 세로 병합 셀을 좌표 기반으로 복원한 뒤 정규화 파일과 브라우저 배포 사본을 함께 검수합니다. 입학연도가 다른 학생이나 편입생에게 이 snapshot을 임의 적용하지 않으며, 독립 전공표가 없는 단위도 수동 확인 상태로 보존합니다.

## 개발과 검증

```bash
# backend
uv --directory apps/backend sync --frozen
uv --directory apps/backend run ruff format --check src tests ../../scripts/extract-major-required.py
uv --directory apps/backend run ruff check src tests ../../scripts/extract-major-required.py
uv --directory apps/backend run mypy src
uv --directory apps/backend run pytest -q
uv --directory apps/backend run timetabler-validate-data

# web
npm ci --prefix apps/web
npm run api:generate --prefix apps/web
npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
npm test --prefix apps/web
npm run build --prefix apps/web

# browser E2E: mobile, desktop, accessibility
npm ci --prefix e2e
npm test --prefix e2e
```

GitHub Actions는 GitHub가 제공하는 `ubuntu-latest` runner에서 백엔드, OpenAPI·정적 카탈로그 snapshot, 데이터 검증, 프론트 타입·lint·unit·build, Playwright, Docker Compose 기동과 실제 OR-Tools E2E를 검사합니다. 운영 서버를 Actions runner로 사용하지 않습니다.

## 운영

```bash
./scripts/backup-db.sh
./scripts/restore-db.sh backups/timetabler-YYYYMMDDTHHMMSSZ.dump
docker compose logs -f api optimizer web
```

개인 이수내역은 기본적으로 서버에 전송하지 않고 브라우저에 저장합니다. 공유 URL에도 시간표 구성만 포함합니다.

## 보안 제보

보안 문제는 공개 이슈에 민감한 내용을 남기지 말고 GitHub의 **Security → Report a vulnerability**를 이용해 주세요. 자세한 정책은 [`SECURITY.md`](SECURITY.md)에 있습니다.

## 기여

1. 변경 범위를 작게 유지하고 관련 테스트를 추가합니다.
2. 위의 backend, web, E2E 검증 중 변경 범위에 해당하는 명령을 실행합니다.
3. 데이터 변경은 출처, 변환 방식, 레코드 수와 checksum을 함께 갱신합니다.
4. 공식 근거로 확정할 수 없는 규칙은 자동 충족으로 단정하지 않고 `UNKNOWN` 또는 수동 확인 상태로 둡니다.

## 라이선스

이 저장소에는 아직 별도의 오픈소스 라이선스가 부여되지 않았습니다. 공개 열람과 이슈·기여 검토가 가능하지만, 코드와 데이터의 재배포·상업적 이용 권한이 자동으로 부여되지는 않습니다. 포함된 학교 원문 자료와 공개 데이터의 권리는 각 제공기관에 있습니다.

## 문서

- [`DESIGN.md`](DESIGN.md) — 모바일 우선 제품·UI/UX 규칙
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 기술·배포·최적화 경계
- [`docs/API_SPEC.md`](docs/API_SPEC.md) — 파일·PostgreSQL 저장 경계와 HTTP API 계약
- [`docs/PRODUCT_PLAN.md`](docs/PRODUCT_PLAN.md) — 기능과 출시 기준
- [`docs/IMPLEMENTATION_READINESS.md`](docs/IMPLEMENTATION_READINESS.md) — OR-Tools 검증 기준
- [`docs/UX_ITERATION_3.md`](docs/UX_ITERATION_3.md) — 현재 시간표와 자동완성 후보 분리
- [`docs/UX_ITERATION_4.md`](docs/UX_ITERATION_4.md) — 과목 진입 역할과 모바일 바텀시트 스와이프
- [`docs/UX_ITERATION_5.md`](docs/UX_ITERATION_5.md) — 초기 시간표 배색 실험
- [`docs/UX_ITERATION_6.md`](docs/UX_ITERATION_6.md) — 필수과목 도구 역할, 20색 시간순 배정, 브라우저 자동 다크 방지
- [`docs/research/DAEJIN_GRADUATION_RULES.md`](docs/research/DAEJIN_GRADUATION_RULES.md) — 공식 졸업요건 출처와 자동 판정 경계
