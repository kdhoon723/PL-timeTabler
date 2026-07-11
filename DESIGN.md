# Design

## Source of truth

- Status: Active for product build
- Last refreshed: 2026-07-11
- Primary product surfaces: 모바일 우선 시간표 편집기, 과목 검색 시트, 자동 생성 후보 비교, 졸업요건 안내
- Evidence reviewed: `README.md`, `docs/PRODUCT_PLAN.md`, `docs/ARCHITECTURE.md`, `.omx/context/ux-product-iteration-20260710T160409Z.md`, `apps/web/src/App.tsx`, `apps/web/src/components/*`, `apps/web/src/styles.css`, component tests, `e2e/playwright.config.ts`, `e2e/timetable.spec.ts`
- UI evidence: 2026-07-11 구현은 실제 390×844, 768×1024, 1440×900 Playwright 프로젝트와 컴포넌트 회귀 테스트로 검증한다. 승인된 외부 시각 레퍼런스는 없으며 이 문서와 구현된 semantic token/component가 현재 기준이다.
- Confirmed product decisions: 대진대 전용, 수동 편집 우선, 완전 자동 생성 포함, 게스트 즉시 사용, 선택형 학교 이메일 OTP 로그인, 첫 방문 학과 설정 유도와 명확한 건너뛰기, 출시 수준 품질을 처음부터 적용

## Brand

- Personality: 빠르고 차분하며 정돈된 학사 도구. 유행을 과시하기보다 정보의 정확성과 조작의 명료함을 보여준다.
- Trust signals: 데이터 학기·갱신일·공식 출처는 `데이터 정보`에서 필요할 때 확인하게 하고, 저장본 사용·오류처럼 행동이 필요한 상태만 전역 알림으로 표시한다. 충돌 여부의 즉시 피드백, 추천 변경 이유, 되돌리기 가능한 작업을 제공한다.
- Avoid: 건너뛸 수 없는 소개·회원가입 장벽, 보라색·청색 그라데이션, 유리 효과, 네온 광택, 과도한 둥근 카드, 장식용 차트, 반짝이 아이콘, 설명 없는 AI 추천
- Theme decision: 제품 1.0은 완성도 높은 라이트 테마 하나만 제공한다. 다크 테마를 자동 반전으로 만들지 않으며 별도 설계·검증 전에는 노출하지 않는다.

### Fixed visual direction: Quiet Light

- 전체 인상은 `흰색`, `아주 옅은 중립 회색`, `짙은 회색 텍스트`, `하나의 차분한 파란색 accent`로 끝낸다.
- 브랜드를 드러내기 위한 별도 gradient, illustration, pattern, mascot, 장식 배경을 만들지 않는다.
- 첫 방문 설정은 학과 선택의 효용과 두 행동만 보여주는 한 번의 작업형 화면으로 제한한다. `건너뛰고 바로 만들기`는 항상 같은 화면에 노출하며 마케팅 hero나 기능 나열을 넣지 않는다.
- 정보 계층은 색상 수가 아니라 글자 크기·굵기·여백·정렬로 만든다.
- 기본 컨테이너는 평평하게 유지하고 떠 있어야 하는 sheet·popover 외에는 그림자를 사용하지 않는다.
- 시각적으로 흥미로워 보이게 만드는 것보다 빠르게 이해되고 오래 사용해도 피로하지 않은 것을 우선한다.

## Product goals

- Goals:
  - 로그인 없이도 첫 화면에서 학과 설정을 건너뛰고 바로 시간표 작성을 시작한다.
  - 학과·학년을 선택한 사용자는 메인 편집기에서 입학연도·전형까지 공식 자료와 일치하는 전공필수와 교양필수 분반을 먼저 확인한다. 불일치하거나 편입 인정 판단이 필요한 경우 자동 적용하지 않는다.
  - 학교 이메일 로그인은 선택이며 활성화되지 않은 배포에서는 로그인 행동을 노출하지 않는다.
  - 모바일에서도 한 손으로 과목 검색·추가·삭제·분반 변경이 가능하다.
  - 사용자가 고른 과목을 존중하면서 충돌 없는 분반과 더 나은 공강 구성을 제안한다.
  - 입학연도·학과·전공 방식에 맞는 졸업요건과 아직 부족한 교양·전공 영역을 근거와 함께 보여준다.
  - 필수과목, 후보과목, 희망 학점, 공강과 시간대 조건으로 설명 가능한 시간표 후보를 자동 생성한다.
  - 자동 생성 후보는 저장된 시간표를 바꾸기 전에 메인 격자에서 유지·추가·제외·분반 교체를 정확히 미리 보고 적용 또는 취소한다.
  - 균형, 수업 몰아서, 공강일 우선, 오전 회피, 늦은 수업 회피처럼 학생 언어로 조건을 시작하고 세부 수치는 필요할 때만 펼친다.
  - 신입학 입학연도와 현재 학년이 활성 학기 기준으로 이례적이면 예상 학년을 설명한다. 지연 진급은 휴학·복학 확인 후 사용할 수 있지만, 일반 예상보다 빠른 진급은 프로필만 저장하고 학과 확인 전에는 필수과목 자동 판정에 사용하지 않는다.
  - 수강신청 전에 여러 시간표 후보를 빠르게 비교하고 보존한다.
- Non-goals:
  - 실제 수강신청 실행 또는 계정 연동
  - 학교가 공개하지 않은 성적·개인정보의 자동 수집
  - 근거 자료 없이 졸업 가능 여부를 확정하는 법적·학사적 보증
  - 강의평, 실시간 잔여석, 다학교 지원
- Success signals:
  - 신규 사용자가 별도 안내 없이 30초 안에 첫 과목을 추가한다.
  - 모바일 사용자가 3분 안에 5개 과목으로 충돌 없는 시간표를 만든다.
  - 추천 결과가 바꾼 분반과 개선 효과를 사용자가 이해할 수 있다.
  - 졸업요건마다 적용 입학연도·학과·원문 출처·갱신일을 확인할 수 있다.

## Personas and jobs

- Primary personas:
  - 수강신청을 처음 준비하는 신입생
  - 필수 과목과 희망 교양을 빠르게 조합하려는 재학생
  - 모바일로 이동 중 시간표 후보를 수정하는 학생
- User jobs:
  - 과목명·교수명·과목코드로 빠르게 수업을 찾는다.
  - 같은 과목의 여러 분반을 비교하고 충돌 없는 분반을 고른다.
  - 특정 수업은 고정한 채 공강과 빈 시간을 개선한다.
  - 입학연도와 학과를 선택해 부족한 필수·영역 학점을 확인한다.
  - 여러 조건을 입력해 자동 생성된 후보를 비교한 뒤 수동으로 다듬는다.
  - 만든 시간표를 새로고침 후에도 이어서 사용하고 공유한다.
- Key contexts of use: 수강편람 공개 직후, 모바일 브라우저, 짧은 반복 방문, 네트워크가 느린 환경

## Information architecture

- Primary navigation: 시간표 편집을 기본 화면으로 두고 `졸업요건`과 `저장한 시간표`는 보조 화면으로 제공한다.
- Core routes/screens:
  - 첫 방문 온보딩 overlay: 학과 → 이번 학기 기준 학년, 언제든 건너뛰기. 편입생만 작은 `혹시 편입생인가요?` 선택으로 편입학년도를 펼칠 수 있고, 일반 학생의 입학연도·학생 구분은 편집기에서 여는 선택형 학사 기준으로 분리한다.
  - `/`: 시간표 편집기
  - `/requirements`: 입학연도·학과별 졸업요건과 이수 현황
  - `/share/:id`: 공유 시간표의 읽기·복사 화면
- Content hierarchy:
  1. 현재 시간표 캔버스와 충돌 상태
  2. 접힌 필수과목 진행 요약과 다음 행동(프로필이 있을 때만)
  3. 과목 추가와 course-first 검색
  4. 총 학점·공강일·빈 시간 요약
  5. 계획 큐의 선택·잠금·후보 상태
  6. 수동 개선·자동 생성과 변경 이유
  7. 졸업요건 충족·부족 상태와 공식 근거

## Core editor model: 시간표 캔버스 + 계획 큐

- **시간표 캔버스가 중심이다:** 격자는 선택 결과와 충돌을 즉시 보여주는 편집기의 주 작업면이다. 정상 프로필의 390px 화면에서 격자 시작점은 초기 viewport의 `y ≤ 360`을 유지한다.
- **계획 큐는 캔버스를 보조한다:** 필수과목 진행, 선택 과목, 예비·제외 과목, 자동 생성 조건과 후보는 모두 캔버스에 넣기 전후의 계획 상태다. 모바일에서는 필요할 때 dialog/sheet로, 768px 이상에서는 정적 aside로 제공한다.
- **점진적 공개:** 필수과목 상세는 기본 접힘이며 선택 수와 필수학점 진행, 다음 행동을 요약한다. 검색 결과는 최대 20개 과목 행만 먼저 보여주고 한 과목의 분반만 펼친다.
- **명령 복구:** 모바일 상단 `더보기`는 실행 취소·다시 실행·공유·졸업요건·PNG/PDF를 두 탭 이내에 제공한다. 편집 입력 밖에서는 Ctrl/Cmd+Z와 Shift+Ctrl/Cmd+Z를 지원한다.
- **상태를 행동과 함께 설명한다:** 검색 분반은 추천, 충돌, 시간 미정, 현재 분반, 추가/교체를 텍스트와 accessible name으로 함께 제공한다.
- **후보는 적용 전에 캔버스에서 비교한다:** 후보 card의 미리보기 행동은 저장된 draft를 바꾸지 않는다. 캔버스와 비교 bar가 유지·추가·제외·교체 전·교체 후를 텍스트와 선/테두리로 구분하며 `적용`만 undo 가능한 변경을 만든다.
- **데스크톱 drag는 고정 분반 교체의 보조 입력이다:** 1200px 이상에서 잠기지 않은 기존 블록만 끌 수 있고, 같은 과목의 충돌 없는 공식 대체 분반 위치만 drop slot으로 나타난다. 같은 시간에 여러 공식 분반이 겹치면 하나의 slot에서 분반을 명시적으로 고른다.

## Profile information architecture

- **시간표 기본 설정:** 첫 방문의 필수 결정은 학과·전공과 이번 학기 기준 학년뿐이다. 편입생에게만 작은 보조 선택을 제공하고, 선택했을 때만 편입학년도와 인정 내역 안내를 펼친다.
- **학사 기준 설정:** 입학연도·처음 입학한 경로·학생 구분은 전공필수·교양필수 판정 정확도를 높이는 선택 설정이다. 메인 필수과목 패널과 프로필 메뉴에서 다시 진입한다.
- **이수 현황:** 총·교양·전공 이수학점, 이수과목, 편입 인정학점은 `/requirements`에서만 점진적으로 받는다.
- 편입 선택을 하지 않은 기본 온보딩은 입학연도를 학년으로 역산하거나 입학 경로를 `신입학`으로 추정해 저장하지 않는다.
- 학번 홀짝 분반처럼 검증된 적용 대상이 없는 필드는 숨기고, 공식 규칙이 확인된 학과에만 조건부 노출한다.
- 데이터 경계와 화면별 필드 계약은 `docs/ONBOARDING_INFORMATION_ARCHITECTURE.md`를 따른다.

## Screen layout contract

### Mobile editor

- 필수과목 패널은 기본 접힘이며 선택 과목 수·필수학점 진행·다음 행동을 먼저 보여준다. 펼치면 `필수 → 전공선택 → 교양선택` 순서를 안내하며 사용자가 분반을 확인한 뒤 배치한다.
- 상단 앱바는 52px 높이로 학기 선택, 총 학점, 더보기만 배치한다. 로고나 큰 제목으로 세로 공간을 소비하지 않는다.
- 시간표 격자는 화면 본문을 차지하며 시간 축 36px와 월~금 5개 열이 한 화면 폭에 들어와야 한다.
- 과목 블록을 탭하면 상세·분반 교체·잠금·삭제가 바텀시트로 열린다. 블록 안에 작은 조작 버튼을 여러 개 넣지 않는다.
- `과목 추가`는 하단 내비게이션 위의 명확한 단일 기본 행동으로 유지한다. 자동 생성은 같은 중요도의 두 번째 고정 버튼으로 경쟁시키지 않는다.
- 검색 시트는 최대 92dvh이며 검색창·필터 요약은 상단에 고정하고 결과만 스크롤한다. 저장된 학과와 카탈로그 전공 분류가 일치하면 `내 전공` 빠른 필터를 검색창 바로 아래에 노출하고, 이수구분 목록에서도 `전체` 다음 첫 항목으로 둔다. 전체 과목은 기본값으로 유지해 교양 탐색을 방해하지 않는다.
- 자동 생성/준비 도구는 닫혔을 때 접근성·focus 흐름에서 사라지는 이름 있는 modal dialog다. 열 때 닫기 버튼으로 focus를 옮기고 닫기·Escape·browser Back 모두 정확한 trigger로 focus를 돌린다.
- 후보 미리보기를 선택하면 tools dialog를 닫고 메인 캔버스의 비교 bar로 focus를 이동한다. 비교 bar는 등교일·학점·빈 시간·첫 수업·마지막 수업을 유지한다. 미리보기 충돌은 읽기 전용이며, 취소는 저장된 draft를 유지하고 캔버스 제목으로 focus를 돌린다.
- 모바일·태블릿의 분반 교체는 drag나 long press를 요구하지 않으며 블록 tap/Enter → 상세 sheet → 명시적 `교체`가 완전한 경로다.
- 하단 고정 UI는 `env(safe-area-inset-bottom)`을 포함하며 콘텐츠와 키보드 포커스를 가리지 않는다.

### Tablet and desktop editor

- 768~1199px: 시간표와 선택 과목/추천 패널을 2열로 배치하며 시간표 영역에 독립적인 `과목 추가` 행동을 유지한다.
- 1200px 이상: 검색·필터 280px, 시간표 `minmax(560px, 1fr)`, 선택·추천 320px의 3영역을 기본으로 한다.
- 전체 콘텐츠 최대 폭은 1440px이며 넓은 화면에서도 격자를 무한히 늘리지 않는다.
- 데스크톱 패널은 모두 카드로 띄우지 않는다. 배경·얇은 구분선·간격으로 영역을 나누고 실제 독립 객체에만 surface를 사용한다.
- 1200px 이상에서는 잠기지 않은 기존 시간표 블록을 공식 대체 분반으로 끌어 교체할 수 있다. drag 중에는 대체 분반의 모든 실제 session을 포함하도록 시간·요일 범위를 확장한다.

### Requirements screen

- 프로필 선택 → 충족 요약 → 부족 항목 → 공식 근거 순으로 읽힌다.
- 원형 진행률이나 장식용 점수보다 `32학점 중 24학점`, `필수 2과목 남음`처럼 실제 값을 먼저 보여준다.
- `UNKNOWN`은 성공·실패 색으로 위장하지 않고 `확인 필요`와 사유, 공식 문의가 필요한 범위를 함께 표시한다.

## Design principles

- **편집기는 항상 접근 가능하다:** 첫 방문 학과 설정은 필수과목 연결을 위한 선택형 도움이며, 게스트 건너뛰기를 막거나 로그인부터 요구하지 않는다.
- **drag는 보조 입력이고 tap/keyboard가 기준이다:** 실제 강의시간은 고정한다. 모바일·태블릿은 검색, 추가, 상세 sheet의 분반 교체를 사용하고, 데스크톱 drag도 같은 공식 대체 분반만 선택한다.
- **추천은 사용자의 선택을 존중한다:** 잠근 과목은 유지하고 변경 수를 최소화한다.
- **자동 생성 후에도 편집권은 사용자에게 있다:** 생성 결과를 정답처럼 강요하지 않고 비교·전체 적용·되돌리기를 제공한다.
- **학사 규칙에는 근거가 따라야 한다:** 적용 연도와 원문을 확인할 수 없는 규칙은 확정 판정에 사용하지 않는다.
- **문제와 해결을 함께 보여준다:** 충돌만 알리지 않고 가능한 대체 분반을 바로 제시한다.
- **복잡성은 점진적으로 공개한다:** 처음에는 검색과 시간표만, 조건·추천은 필요할 때 펼친다.
- **한 화면에는 하나의 주 행동만 둔다:** 동일한 시각 무게의 기본 버튼을 여러 개 배치하지 않는다.
- **장식보다 정렬과 계층을 사용한다:** 카드·색상·아이콘을 추가하기 전에 여백, 정렬, 제목 크기, 구분선으로 관계를 표현한다.
- **AI처럼 보이지 않게 한다:** 기능을 `AI 추천`, `마법처럼 생성`으로 포장하지 않고 `자동 생성`, `공강 늘리기`, `빈 시간 줄이기`처럼 결과를 설명한다.
- Tradeoffs: 화면 밀도보다 터치 정확성과 가독성을 우선한다. 수동 편집을 기본 경로로 유지하되 자동 생성은 별도 모드로 완성도 있게 제공한다.

## Visual language

### Color tokens

색은 역할 기반 token으로만 사용한다. 컴포넌트에서 임의 hex 값을 추가하지 않는다.

| 역할 | 기준값 | 사용 |
|---|---|---|
| `canvas` | `#F6F7F9` | 앱 배경 |
| `surface` | `#FFFFFF` | 시트, 메뉴, 독립 패널 |
| `surface-subtle` | `#F0F2F5` | 선택 전 보조 영역, hover |
| `text-primary` | `#16181D` | 제목·본문 |
| `text-secondary` | `#555D6B` | 보조 설명 |
| `text-tertiary` | `#676F7B` | 메타데이터; 작은 본문에도 4.5:1 유지 |
| `border` | `#DCE0E6` | 구분선·비강조 테두리 |
| `border-strong` | `#8A93A0` | 입력 경계·비텍스트 대비가 필요한 상태 |
| `accent` | `#2B59C3` | 기본 행동·선택·링크 |
| `accent-hover` | `#20459E` | hover/pressed |
| `accent-soft` | `#E8EEFC` | 선택 배경 |
| `success` | `#146C43` | 충족·저장 완료 |
| `warning` | `#8A5B00` | 미확인·주의 |
| `danger` | `#B42318` | 충돌·삭제 |
| `focus` | `#1D4ED8` | 키보드 포커스 |

- 보라색-파란색 그라데이션과 다중 색상 glow는 사용하지 않는다.
- 상태는 색만으로 전달하지 않고 아이콘·라벨·설명을 함께 사용한다.
- 과목 색상은 최대 6개의 저채도 배경/진한 전경 쌍으로 제한하고 과목키 hash로 일관되게 배정한다. 채도가 높은 원색은 사용하지 않는다.
- 같은 과목의 분반은 같은 hue를 사용하고 선택·잠금·충돌은 별도 테두리와 아이콘으로 구분한다.

### Typography

- 기본 글꼴은 self-hosted `Pretendard Variable`을 우선하고 `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Noto Sans KR`, `sans-serif` 순으로 fallback한다.
- 숫자 정렬이 중요한 시간·학점에는 `font-variant-numeric: tabular-nums`를 사용한다.
- 본문 16/24, 보조 본문 14/20, 메타 12/16, 소제목 18/26, 화면 제목 24/32를 기본 scale로 사용한다.
- 12px 미만을 사용하지 않는다. 굵기는 400·500·600 세 단계만 사용하고 700 이상의 과도한 굵기를 남용하지 않는다.
- 영문 대문자·넓은 자간을 장식적으로 사용하지 않는다. 한국어 제목의 자간은 기본값을 유지한다.

### Spacing, shape, elevation

- 간격은 4px base scale의 `4, 8, 12, 16, 20, 24, 32, 40, 48, 64`만 사용한다.
- 본문 좌우 여백은 360~390px에서 16px, 768px 이상에서 24px, 1200px 이상에서 32px다.
- radius는 작은 요소 6px, 입력·버튼 10px, 시트·큰 패널 14px를 사용한다. 완전한 pill은 필터 chip·상태 badge에만 허용한다.
- 기본 화면은 그림자 없이 border와 배경으로 구분한다. 팝오버·바텀시트·고정 도구에만 한 단계의 얕은 그림자를 사용한다.
- 카드 안에 카드를 중첩하지 않는다. 섹션마다 흰 카드를 만드는 대신 하나의 surface 안에서 간격과 구분선을 사용한다.
- 한 화면에서 사용하는 surface 단계는 `canvas`, `surface`, `surface-subtle` 세 단계를 넘기지 않는다.

### Motion and iconography

- hover/press 120ms, 패널·시트 180~220ms의 ease-out 전환만 사용한다.
- bounce, elastic spring, 배경 blob 이동, 숫자 카운트업 같은 장식 모션을 사용하지 않는다.
- `prefers-reduced-motion`에서는 위치·크기 전환을 제거하고 즉시 상태를 바꾼다.
- 단일 1.75~2px stroke 아이콘 체계만 사용한다. emoji, 3D 아이콘, 채움/선형 아이콘 혼용을 금지한다.
- 반짝이·마술봉·로봇 아이콘으로 자동 생성을 표현하지 않는다. 자동 생성은 명확한 텍스트와 일반적인 조정/재생성 아이콘을 사용한다.

## Anti-slop visual guardrails

다음 패턴은 명시적 디자인 검토 없이는 구현하지 않는다.

- 대형 hero 문구, 마케팅 랜딩을 편집기 앞에 배치
- 페이지 전체 gradient, glassmorphism, backdrop blur, neon glow
- 모든 섹션을 둥근 흰 카드로 만들거나 카드 안에 카드 중첩
- 의미 없는 badge, 통계 카드, sparkline, 진행 원형 추가
- 기본 버튼을 한 화면에 2개 이상 같은 강조도로 배치
- 설명 없이 icon-only control 사용
- 제목 옆 장식 emoji, 자동 생성 기능의 별·반짝이 표현
- `AI가 분석 중입니다` 같은 모호한 문구와 가짜 단계별 진행 애니메이션
- 지나치게 큰 radius, pill 버튼 남용, 과도한 그림자
- placeholder를 label 대신 사용하거나 저대비 회색으로 핵심 정보를 표시
- 모바일에서 hover, drag, long-press만으로 가능한 핵심 기능
- 데스크톱 화면을 축소해 모바일로 쓰거나 가로 스크롤을 기본 탐색으로 요구

## Components

- Existing components to reuse: 현재 구현 컴포넌트 없음
- New/changed components:
  - `AppHeader`: 학기, 총 학점, 실행 취소·다시 실행
  - `TimetableGrid`: 요일·시간 격자와 선택 과목 블록
  - `CourseSearchSheet`: 모바일 바텀시트/데스크톱 사이드패널
  - `CourseResultGroup`: 과목명 단위 결과와 분반 비교
  - `SelectedCourseList`: 선택 과목, 잠금, 분반 교체, 삭제
  - `ConflictNotice`: 충돌한 과목과 해결 가능한 대체 분반
  - `PreferenceChips`: 공강, 오전 제외, 빈 시간 최소화 조건
  - `SuggestionTray`: 현재 안과 추천안 비교, 변경 이유, 적용·되돌리기
  - `AutoGeneratePanel`: 필수·후보 과목, 학점, 시간대, 공강 조건 입력
  - `CandidateComparison`: 자동 생성 후보의 차이와 점수 근거 비교
  - `CandidatePreviewBar`: 비파괴 후보 비교와 적용·취소
  - `PreferencesPanel`: 학생 언어 preset, 핵심 학점·공강일, 세부 조건 disclosure
  - `Onboarding`: 학과·학년 기본 설정, 작은 편입생 disclosure, 선택형 입학연도 기준과 학년 일관성 확인
  - `RequirementNavigator`: 입학연도·학과별 졸업요건과 부족 영역
  - `SourceEvidence`: 규칙의 원문, 적용 대상, 기준일 표시
- Variants and states: 기본, 선택, 잠금, 충돌, 시간 미정, 강의실 미상, 미리보기 유지·추가·제외·교체 전·교체 후, drag source, official drop slot
- Token/component ownership: 색상·간격·타이포 토큰은 앱 전역에서 정의하고 기능 컴포넌트가 임의 값을 추가하지 않는다.

### Component usage rules

- `Button`: 모바일 최소 높이 44px. `primary`, `secondary`, `ghost`, `danger` 네 종류만 두고 primary는 현재 영역의 주 행동 하나에만 사용한다.
- `IconButton`: 시각 크기와 무관하게 44×44px hit area, tooltip, accessible name을 제공한다.
- `TextField/Combobox`: 모바일 48px, 데스크톱 44px 높이. label을 항상 유지하며 오류·도움말 공간을 layout shift 없이 확보한다.
- `FilterChip`: 실제 toggle/filter에만 사용한다. 선택 상태는 배경색뿐 아니라 check 또는 명시적 label로 표시한다.
- `BottomSheet`: drag handle만으로 닫지 않고 닫기 버튼·Escape·back 동작을 지원하며 focus를 trigger로 돌려보낸다.
- `Toast`: 저장 완료처럼 일시적이고 되돌릴 필요 없는 정보에만 사용한다. 오류와 졸업요건 경고는 사라지는 toast로 숨기지 않는다.
- `UndoSnackbar`: 과목 삭제·추천 적용 직후 사용하며 한 번의 탭으로 이전 상태를 복원한다.
- `Dialog`: 파괴적이거나 되돌릴 수 없는 작업에만 사용한다. 단순 선택과 상세정보에는 sheet/popover를 사용한다.
- `Skeleton`: 실제 레이아웃과 같은 형태로 최소 사용하며 반복 shimmer를 장시간 노출하지 않는다.

## Accessibility

- Target standard: [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/). 핵심 터치 대상은 enhanced 기준에 가까운 44×44px을 제품 규칙으로 채택한다.
- Keyboard/focus behavior: 검색 결과와 분반 목록을 키보드로 이동·선택할 수 있고, 바텀시트 포커스를 관리하며 닫은 뒤 트리거로 복귀. focus는 최소 2px 외곽선과 2px offset을 사용하고 sticky UI 아래 가려지지 않는다.
- Contrast/readability: 일반 텍스트 4.5:1, 큰 텍스트·UI 상태 경계 3:1 이상. 과목과 상태를 색상에만 의존하지 않는다.
- Screen-reader semantics: 시간표는 시각 격자 외에 요일·시간·과목을 읽을 수 있는 구조화된 대체 목록 제공
- Drag semantics: draggable block은 공식 분반에만 놓을 수 있다는 설명을 `aria-describedby`로 연결하고 시작·완료를 polite live region으로 알린다. 같은 동작의 tap, 명시적 button, Enter 경로를 항상 유지한다.
- Reduced motion and sensory considerations: 모션 축소 설정 지원, 오류·추천 상태를 색상 외 텍스트로 설명

## Responsive behavior

- Supported breakpoints/devices: 360~767px mobile, 768~1199px tablet, 1200px 이상 desktop. breakpoint는 기기명이 아니라 레이아웃이 깨지는 지점으로 조정한다.
- Layout adaptations:
  - 모바일: 시간표 중심 단일 화면 + 하단 고정 과목 추가 버튼 + 바텀시트
  - 태블릿: 시간표와 선택 과목 요약을 병렬 배치
  - 데스크톱: 검색 패널, 시간표, 선택·추천 요약의 3영역 구성
- Touch/hover differences: 핵심 기능은 hover 없이 동작한다. guided drag는 1200px 이상 pointer 보조 기능이며 모바일·태블릿에서 `draggable=false`; 길게 누르기는 어떤 핵심 동작에도 필요하지 않다.
- Mobile viewport rules: `100vh` 대신 동적 viewport 단위와 safe area를 고려한다. 키보드가 열린 상태에서도 검색 입력과 선택 결과가 동시에 보이도록 한다.

## Interaction states

- Loading: 앱 골격과 데이터 로딩 진행을 표시하되 기존 시간표가 있으면 먼저 복원. solver는 가짜 퍼센트 대신 `대기 중`, `후보 생성 중`, `비교 준비됨`처럼 실제 상태만 표시
- Empty: 빈 격자 위에 간단한 한 문장과 `과목 추가` 기본 행동 제공
- Error: 데이터 로딩 실패, 잘못된 시간 형식, 저장 복원 실패를 구분하고 재시도 제공
- Success: 과목 추가·추천 적용 후 짧은 상태 메시지와 실행 취소 제공
- Preview: 저장된 draft는 유지한 채 비교 bar와 격자가 변경 내용을 함께 표시한다. 적용·취소가 명시적이고 preview 중 수업 블록은 상세 sheet를 열지 않는다.
- Dragging: source는 grabbing 상태, 공식 대체 session은 dashed ghost slot, hover target은 solid accent로 표시한다. drop 또는 drag 종료 시 모든 임시 상태를 제거하고 accidental click을 억제한다.
- Disabled: 비활성 이유를 인접 텍스트로 설명
- Offline/slow network: 정적 데이터 로딩 이후 편집은 네트워크 요청 없이 동작하도록 설계
- Destructive: 삭제보다 실행 취소를 우선하며 확인 dialog는 되돌릴 수 없는 전체 초기화에만 사용

## Content voice

- Tone: 짧고 직접적이며 학생이 쓰는 표현을 우선
- Terminology: `과목`, `분반`, `공강`, `빈 시간`, `잠금`, `충돌`, `시간 미정`
- Microcopy rules:
  - `최적화`보다 결과를 설명하는 `공강 늘리기`, `빈 시간 줄이기`를 우선한다.
  - 추천은 `화요일 공강을 만들기 위해 2개 분반을 변경합니다`처럼 변경과 이유를 함께 쓴다.
  - 오류는 `추가할 수 없음`에서 끝내지 않고 `02분반은 충돌하지 않습니다`처럼 다음 행동을 제시한다.
  - `AI`, `스마트`, `매직`, `완벽한 시간표`처럼 기능을 과장하는 표현을 쓰지 않는다.
  - 버튼은 명사보다 동사와 결과를 사용한다: `추천 적용`, `이 분반으로 변경`, `공강일 선택`.
  - 성공 toast를 남발하지 않는다. 화면 자체의 상태 변경이 분명하면 추가 메시지를 생략한다.

## Implementation constraints

- Framework/styling system: React + TypeScript 프론트엔드, Python + FastAPI 백엔드, OpenAPI로 생성하는 TypeScript SDK
- Optimization: API와 분리된 Python optimizer 프로세스에서 OR-Tools CP-SAT 실행
- Data/storage: PostgreSQL + Alembic migration, 개인 편집 상태는 브라우저 저장 우선
- Deployment: web/API/optimizer/DB/migration을 Docker Compose로 실행하며 개발 전용 차이는 별도 Compose 파일로 관리
- Design-token constraints: semantic CSS custom property를 단일 원천으로 사용하고 컴포넌트 내부 raw color·임의 spacing·임의 z-index를 금지한다. light theme token만 우선 구현한다.
- Performance constraints: 과목 검색은 로컬 인덱스로 처리하고 강의실 상세는 필요할 때 로드
- Compatibility constraints: 모바일 Safari와 Android Chrome을 우선 검증
- Test/screenshot expectations: Playwright release gate는 390×844, 768×1024, 1440×900 실제 프로젝트를 사용한다. 360px/320px reflow는 추가 호환 점검으로 유지하며 empty, populated, conflict, search-open, generating, result-comparison, requirements-unknown 상태를 시각 회귀 대상으로 삼는다.

### Shipped compatibility contract: fixed-section drag and drop

- drag source는 1200px 이상에서 보이는, 잠기지 않은 기존 timetable block이다. search 결과·계획 큐·candidate preview block은 drag source가 아니다.
- drop target은 현재 선택을 제외했을 때 충돌 없는 같은 과목의 canonical catalog section이다. 그 section의 모든 session이 실제 요일·시간·길이로 함께 나타난다.
- drop은 source item의 역할을 보존한 `SWAP`이며 history에 기록되어 toast, keyboard shortcut, header command로 undo할 수 있다.
- 임의 시간대·요일·길이로 자유 이동하거나 resize하지 않는다. grid 빈 공간은 drop target이 아니며 실제 개설시간은 catalog가 정한다.
- tap/click, 명시적 `교체` button, Enter 경로는 viewport와 pointer 종류에 관계없이 완전하게 유지한다. drag-only, hover-only, long-press-only 핵심 행동은 허용하지 않는다.

## Visual quality gate

프론트엔드 변경은 다음을 모두 만족해야 디자인 완료로 본다.

1. 360px에서 가로 페이지 스크롤 없이 과목 추가·분반 교체·삭제·실행 취소가 가능하다.
2. primary action이 화면/시트마다 하나로 식별된다.
3. 모든 색·간격·radius·shadow가 token에서 나온다.
4. 일반 텍스트 4.5:1, UI 경계·focus 3:1 이상을 자동 검사한다.
5. 키보드만으로 검색, 결과 이동, 선택, 시트 닫기, 자동 생성 적용이 가능하다.
6. 200% 확대와 320 CSS px reflow에서 핵심 정보와 조작이 손실되지 않는다.
7. loading·empty·error·offline·unknown 상태가 정상 화면과 같은 수준으로 설계돼 있다.
8. 동일 화면에 gradient/glow/중첩 카드/장식 badge/과도한 pill이 없는지 리뷰한다.
9. 자동 생성 결과가 점수 하나가 아니라 변경 과목·공강·빈 시간·미충족 선호로 설명된다.
10. 승인된 360·390·768·1440px baseline과 시각 회귀 차이를 검토한다.

## Open questions

- [ ] 최종 서비스명과 로고가 필요한가 / 제품 / 시각 톤에 영향
- [ ] 시간표 공유에서 URL·이미지·PDF의 우선순위 / 제품 / 내보내기 흐름에 영향
- [ ] 야간·토요일 수업 표시 요구가 있는가 / 데이터·제품 / 격자 범위에 영향
- [ ] 실제 사용자 테스트 참여자를 어떻게 모집할까 / 제품 / 출시 기준에 영향
- [ ] 비공개 포털 성적 없이 기존 이수내역을 입력하는 최소 부담 방식 / 제품·개인정보 / 졸업요건 정확도에 영향
