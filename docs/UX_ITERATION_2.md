# UX Iteration 2 — 후보 미리보기 + guided 분반 drag

Date: 2026-07-11

## Outcome

Iteration 1의 시간표 캔버스 + 계획 큐를 유지하면서 자동 생성 후보를 적용 전에 메인 캔버스에서 검토하고, 데스크톱에서는 기존 수업 블록을 공식 대체 분반으로만 끌어 교체할 수 있게 했다. 선호 조건과 학적 입력은 학생이 이해하는 언어와 명시적 안전장치로 정리했다.

새 의존성, backend/API contract, optimizer contract, catalog schema는 추가하거나 변경하지 않았다.

## Shipped behavior

### Candidate preview before apply

- optimizer candidate card는 즉시 적용하지 않고 `후보 N 미리보기`만 제공한다.
- 미리보기는 저장된 draft를 바꾸지 않는다. 메인 격자에서 `유지`, `추가`, `제외`, `교체 전`, `교체 후`를 텍스트와 시각 경계로 구분한다.
- 비교 bar는 정확한 추가·제외·분반 교체 목록과 후보의 등교일·학점·공강을 보여주며 `후보 적용`과 `취소`를 제공한다.
- 모바일에서 미리보기를 시작하면 tools dialog가 닫히고 비교 bar로 focus가 이동한다. 취소하면 캔버스 제목으로 돌아간다.
- 적용은 기존 history reducer를 통해 undo 가능하다. catalog, profile 또는 draft가 바뀌어 preview 기준이 오래되면 preview를 제거한다.

### Student-language preferences

- preset은 `균형`, `수업 몰아서`, `공강일 우선`, `오전 수업 피하기`, `늦은 수업 피하기`다.
- 목표 학점, 선호 공강일, 기존 시간표 변경 최소화는 바로 접근할 수 있다.
- 최소·최대 학점, 회피 시간, 점심시간, 하루 최대 수업시간, compactness는 `세부 조건 조정` disclosure 안에 둔다.
- preset은 기존 `Preferences` field만 쓴다. 목표 학점과 사용자가 선택한 공강일을 덮어쓰지 않는다.

### Academic-profile consistency

- 활성 학기 `2026-1` 기준으로 신입학 입학연도와 현재 학년을 비교한다.
- 이례적인 조합은 일반적으로 예상되는 학년을 설명하며 사용자가 현재 학년을 명시적으로 확인하기 전에는 저장할 수 없다.
- 확인은 optional `gradeMismatchAcknowledged` frontend profile field로 저장된다. field가 없는 기존의 일관된 profile은 그대로 유효하다.
- 편입학은 이 검사에서 제외한다.
- 확인하지 않은 불일치 profile은 전공필수와 입학연도 기준 교양필수 자동 판정의 근거로 사용하지 않는다.

### Guided desktop section drag

- viewport `1200px` 이상에서 잠기지 않은 기존 timetable block만 draggable이다.
- drag를 시작하면 같은 과목의 canonical catalog section 중 다른 현재 수업과 충돌하지 않는 대체 분반만 ghost drop slot으로 나타난다.
- drop slot은 대체 분반의 실제 공식 요일·시작·종료 위치다. 조기·야간·토요일과 multi-session 대체 분반도 grid bounds와 slot에 모두 포함한다.
- 같은 대체 분반의 여러 session은 하나의 hover target으로 강조되며 어느 session에 놓아도 그 section 전체를 교체한다.
- drop은 source `PlanItem`의 role/lock 의미를 보존하는 `SWAP`이며 undo 가능하다. 완료 결과는 live region과 toast로 알린다.
- drag 직후 발생하는 click은 상세 sheet를 열지 않는다.

## Drag fallback rules

- mobile `390px`과 tablet `768px`에서는 timetable block이 `draggable=false`다. long press를 요구하지 않는다.
- 모든 viewport에서 block click/tap 또는 Enter로 기존 상세 sheet를 열 수 있다.
- 상세 sheet의 `충돌 없는 다른 분반` 목록과 명시적 `교체` button은 drag와 같은 canonical alternative set을 제공한다.
- locked block과 candidate-preview block은 draggable이 아니다.
- grid 빈 공간, 임의 요일/시간, resize handle은 drop target이 아니다. 자유 이동 semantics는 없다.

## Explicit non-goals

- 임의 시간·요일·길이로 수업 이동 또는 resize
- mobile/tablet drag 또는 long-press 전용 기능
- search result나 계획 큐에서 canvas로 끌어 새 과목 추가
- candidate 일부 항목만 선택 적용
- backend/API/catalog/optimizer schema 변경
- 새로운 drag-and-drop library 또는 UI dependency 추가

## Accessibility and state safety

- draggable block은 official alternative-only 규칙과 click/Enter fallback을 accessible description으로 제공한다.
- drag 시작과 교체 완료는 polite live region으로 전달한다.
- preview block은 저장 draft의 상세 sheet를 열지 않고 상태별 accessible name을 제공한다.
- preview, drag source, hover/drop slot은 색상만으로 구분하지 않고 badge, border style, text를 함께 사용한다.
- reduced-motion media query는 기존 전역 규칙을 유지하며 drag/preview에 필수 animation을 추가하지 않았다.

## Exact verification evidence

- Focused preview regression: `npm test -- --run src/domain/candidateDiff.test.ts src/components/OptimizerPanel.test.tsx src/App.preview.test.tsx` → 3 files, 4 tests passed.
- Focused preferences regression: `npm test -- --run src/components/PreferencesPanel.test.tsx` → 1 file, 4 tests passed.
- Focused profile regression: `npm test -- --run src/domain/profile.test.ts src/components/Onboarding.test.tsx src/components/RequiredCoursePanel.test.tsx` → 3 files, 14 tests passed.
- Focused drag regression: `npm test -- --run src/components/TimetableGrid.test.tsx` → 1 file, 5 tests passed.
- Full frontend suite: `npm test` in `apps/web` → 17 files, 63 tests passed.
- Static checks: `npm run typecheck` and `npm run lint` in `apps/web` → passed with zero reported errors or warnings.
- Production build: `npm run build` in `apps/web` → passed; Vite transformed 59 modules.
- Desktop browser gate: `npm test -- --project=desktop-1440` in `e2e` → 10 passed, 5 intentionally skipped (viewport-inapplicable or `E2E_LIVE` only).
- Full browser gate: `npm test` in `e2e` → 28 passed, 17 intentionally skipped across `mobile-390`, `tablet-768`, and `desktop-1440`. Skips are viewport-inapplicable contracts and the two `E2E_LIVE` integration cases per project.
- Automated accessibility checks reported no serious or critical axe violations for onboarding, editor, requirements, and the open mobile tools dialog in the applicable projects.

## Release audit

- Candidate preview mutation boundary: only `후보 적용` dispatches `APPLY`; cancel and preview do not mutate persisted draft.
- Stale preview boundary: draft timestamp, catalog refresh, and profile completion clear preview state.
- Drag mutation boundary: App revalidates desktop viewport, no active preview, unlocked source, and membership in `findAlternatives` before dispatching `SWAP`.
- Fallback boundary: Playwright verifies the same detail-sheet alternative remains reachable by Enter on mobile, tablet, and desktop.
- Dependency/API boundary: package manifests and backend/contracts are unchanged.
