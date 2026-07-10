# UX Iteration 1 — 시간표 캔버스 + 계획 큐

Date: 2026-07-11

## Outcome

시간표 격자를 주 작업면으로 유지하면서 필수과목, 검색 분반, 자동 생성 조건과 내보내기를 필요할 때만 여는 계획 큐로 정리했다. API, optimizer, 데이터 계약과 의존성은 변경하지 않았다.

## Shipped contract

### Responsive editor

- Playwright 기준 viewport는 mobile `390×844`, tablet `768×1024`, desktop `1440×900`이다.
- 390px 정상 프로필에서 필수과목 상세는 기본 접힘이며 timetable grid 시작점은 `y ≤ 360`이다.
- 768px은 timetable + static tools aside의 2열을 유지하면서 별도 `과목 추가` 행동을 제공한다.
- 1200px 이상은 search/selected queue, timetable canvas, tools queue의 3영역이다.

### Mobile tools and commands

- 닫힌 tools panel은 focus/accessibility 흐름에 존재하지 않는다.
- tools는 `자동 생성과 준비`라는 이름의 modal dialog로 열리며 초기 focus는 닫기 버튼으로 간다.
- 닫기 버튼, Escape, browser Back이 모두 dialog를 닫고 정확한 trigger로 focus를 반환한다. native dialog가 배경 상호작용을 억제한다.
- 상단 `더보기` menu는 실행 취소, 다시 실행, 공유, 졸업요건, PNG, PDF를 두 탭 이내에 제공한다.
- editable control 밖에서 Ctrl/Cmd+Z는 undo, Shift+Ctrl/Cmd+Z는 redo다.
- toast의 Undo는 추가·삭제·교체·후보 적용처럼 해당 메시지가 실제로 되돌릴 수 있을 때만 노출한다.

### Required-course progress

- 상세는 기본 접힘이다.
- 요약은 선택 과목/전체 과목 수, 선택 필수학점/전체 필수학점, 다음 행동을 표시한다.
- 펼친 상태에서는 기존 분반 선택과 `시간표에 배치` button을 그대로 유지한다.

### Course-first search

- 초기 결과는 최대 20개 course row이며 분반 button은 0개다.
- 한 번에 한 과목만 펼친다.
- 펼친 분반에는 하나의 추천과 충돌, 시간 미정, 현재 분반, 추가/교체 상태가 시각 텍스트와 accessible name으로 함께 제공된다.
- 이미 선택한 과목의 다른 분반은 명시적인 교체 행동이며 현재 분반은 disabled 상태로 구분한다.

### Accessibility and targets

- mobile tools는 named dialog, desktop/tablet tools는 named complementary aside다.
- 주요 button과 required-course select/action은 최소 44px hit target을 유지한다.
- 검색과 분반 선택, 필수과목 배치, dialog close, undo/redo는 keyboard와 tap 모두 가능하다.
- serious/critical axe 위반이 없는 editor, requirements, open tools dialog를 E2E로 확인한다.

## Test evidence

- Targeted component/App regression: `npm test -- --run src/components/CourseSearchSheet.test.tsx src/components/RequiredCoursePanel.test.tsx src/App.test.tsx` → 3 files, 11 tests passed.
- Frontend unit suite: `npm test` → 13 files, 47 tests passed.
- Static/release checks: `npm run typecheck`, `npm run lint`, and `npm run build` passed; Vite production bundle completed with 56 transformed modules.
- Mobile browser contract: `npx playwright test --project=mobile-390` → 9 passed, 3 skipped (live integration only and desktop-only contract).
- Full browser suite: `npx playwright test` → 23 passed, 13 intentionally skipped across the real 390×844, 768×1024, and 1440×900 projects. Skips are viewport-inapplicable contracts and the two `E2E_LIVE` optimizer/service-worker cases per project.

## Explicit non-goal and next compatibility contract

Iteration 1 does not implement free movement or drag-and-drop. The next compatible drag contract is desktop fixed-section drag from search, the plan queue, or an existing timetable block to a canonical valid alternative section. It never changes a course to an arbitrary time. Every drag action must retain tap, explicit button, and keyboard alternatives.
