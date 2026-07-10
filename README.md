# PL-timeTabler

대진대학교 수강신청 전에 모바일과 데스크톱에서 과목을 고르고, 충돌 없는 시간표 후보를 자동으로 만드는 서비스다. 수동 편집을 우선하고 OR-Tools가 사용자의 선택을 보조한다.

## 구현된 기능

- 2026-1 개설과목 1,576개를 과목명·교수·과목코드·이수구분·요일로 검색
- 분반 추가·교체·잠금·삭제, 필수·희망·예비·제외 역할, 실행 취소·다시 실행
- 시간 충돌 즉시 표시, 대체 가능한 다른 분반 제안
- 정수 목표·최소·최대 학점, 공강 요일, 이른/늦은 수업, 연속 점심 여유, 하루 수업시간, 공강 길이·현재 선택 유지 선호
- OR-Tools CP-SAT 기반 결정론적 후보 3개와 등교일·공강·첫/마지막 수업·미반영 조건 설명
- 입학연도와 46개 교육과정 단위별 공식 졸업요건 출처 안내
- 검증되지 않은 학과 규칙은 자동 충족으로 단정하지 않고 `확인 필요`로 표시
- 브라우저 자동 저장, URL 공유, PNG·인쇄/PDF 내보내기, 수강신청용 예비 분반 체크리스트
- 반응형 모바일 UI, 키보드 접근성, PWA 설치와 네트워크 우선 갱신·오프라인 직접 경로 fallback
- 요청별 rate limit, 활성 작업 상한, lease 복구·취소·만료 정리로 공개 optimizer 보호

## 구성

```text
browser → Nginx/React web → FastAPI → PostgreSQL ← OR-Tools worker
                                  └── versioned catalog files
```

프론트, API/optimizer, DB는 한 이미지에 섞지 않는다. `compose.yaml`이 `web`, `api`, `optimizer`, `db`, `migrate`, `ingest`를 같은 방식으로 재현한다. 자세한 선택 근거는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)에 있다.

## 로컬·서버 실행

```bash
cp .env.example .env
# .env의 POSTGRES_PASSWORD를 긴 무작위 값으로 교체
docker network create kdhoon-public 2>/dev/null || true
docker compose up -d --build
curl http://127.0.0.1:18080/api/v1/health/ready
```

기본 웹 주소는 `http://127.0.0.1:18080`이며 DB는 호스트에 공개하지 않는다. 다른 서버에서도 저장소, `.env`, Docker와 Compose만 있으면 같은 스택을 실행할 수 있다.

### Cloudflare Tunnel

`cloudflared` 컨테이너를 `kdhoon-public` 외부 네트워크에 연결하고 다음 ingress를 사용한다.

```yaml
- hostname: timetabler.kdhoon.me
  service: http://timetabler-web:80
```

DNS에는 Cloudflare 계정에서 다음 CNAME을 한 번 생성해야 한다.

```text
timetabler → c3767b2a-e2e0-460d-8f40-d249ad521e55.cfargotunnel.com
```

## 데이터 갱신

새 강의계획서/개설과목 snapshot은 기존 파일을 직접 덮어쓰지 않고 별도 staging에서 준비한다.

1. `data/courses`, `data/classrooms`, `data/requirements`에 새 학기 원본과 정규화 결과를 둔다.
2. `data/manifest.json`의 레코드 수와 SHA-256 checksum을 갱신한다.
3. canonical API snapshot에서 브라우저 fallback을 다시 생성한다.
4. 아래 release gate가 통과한 뒤 새 이미지를 빌드한다.

```bash
uv --directory apps/backend run timetabler-validate-data
uv --directory apps/backend run timetabler-export-static-catalog
docker compose --profile ingest run --rm --build ingest
```

API와 정적 fallback은 과목·강의실 checksum을 합친 같은 `datasetVersion`과 1,576개 분반의 동일한 세션 의미를 사용한다. API는 이 버전을 최적화 요청과 함께 검증하므로 브라우저의 오래된 데이터와 새 카탈로그가 섞이지 않는다. 데이터 구성과 출처는 [`data/README.md`](data/README.md)를 참고한다.

## 개발·검증

```bash
# backend
uv --directory apps/backend sync --frozen
uv --directory apps/backend run ruff format --check src tests
uv --directory apps/backend run ruff check src tests
uv --directory apps/backend run mypy src
uv --directory apps/backend run pytest -q

# web
npm ci --prefix apps/web
npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
npm test --prefix apps/web
npm run build --prefix apps/web

# browser E2E (mobile + desktop + axe)
npm ci --prefix e2e
npm test --prefix e2e

# running Docker stack + real optimizer worker
E2E_BASE_URL=http://127.0.0.1:18080 E2E_LIVE=1 \
  npm test --prefix e2e -- --grep 'production optimizer integration'
```

CI는 백엔드, OpenAPI·정적 카탈로그 snapshot, 데이터 검증, 프론트 타입·lint·unit·build, Playwright, Docker Compose 기동, 실제 OR-Tools와 서비스워커 E2E를 독립적으로 검사한다.

## 운영

```bash
./scripts/backup-db.sh
./scripts/restore-db.sh backups/timetabler-YYYYMMDDTHHMMSSZ.dump
docker compose logs -f api optimizer web
```

개인 이수내역은 기본적으로 서버에 전송하지 않고 브라우저에 저장한다. 공유 URL에도 시간표 구성만 포함한다.

## 문서

- [`DESIGN.md`](DESIGN.md) — 모바일 우선 제품·UI/UX 규칙
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 기술·배포·최적화 경계
- [`docs/PRODUCT_PLAN.md`](docs/PRODUCT_PLAN.md) — 기능과 출시 기준
- [`docs/IMPLEMENTATION_READINESS.md`](docs/IMPLEMENTATION_READINESS.md) — OR-Tools 검증 기준
- [`docs/research/DAEJIN_GRADUATION_RULES.md`](docs/research/DAEJIN_GRADUATION_RULES.md) — 공식 졸업요건 출처와 자동 판정 경계
