# UX iteration 4 — course entry hierarchy and mobile sheet gestures

## Problem

The mobile editor presented `전체 과목 추가`, `필수 추천`, `내 전공`, and `교양` as four peer choices even though they represented three different jobs: starting a search, reviewing personalized requirements, and filtering a catalog. The compact entry panel also duplicated the fixed mobile course-add action.

Mobile sheets could only be closed with a button or Escape-equivalent navigation. A downward drag on the sheet header did not dismiss it and could be interpreted by the browser as pull-to-refresh.

## Product decision

- Keep one primary catalog action: `과목 찾기`.
- On phones, use the existing fixed bottom action and remove the duplicate compact search button above the grid.
- Treat `필수과목 확인` as a quiet contextual task, not a catalog filter.
- If no department is saved, replace the unavailable required-course task with a small department setup prompt.
- Move `내 전공` and `교양선택` into the search sheet as quick filters.
- Keep detailed completion category and weekday filters behind `세부 필터`; no active filter means all courses.
- Give every mobile `.sheet` a visible drag handle. A downward header drag of at least 72px dismisses the sheet.
- Contain vertical overscroll so the gesture does not become browser pull-to-refresh.

## Responsive placement

- **Phone (<768px):** contextual required-course prompt above the grid, one fixed `과목 찾기` action at the bottom, quick filters inside the bottom sheet.
- **Tablet (768–1199px):** inline `과목 찾기` plus the contextual prompt; no fixed bottom action.
- **Desktop (≥1200px):** the same hierarchy in the left course panel; modal sheets keep their desktop dialog behavior and do not expose the mobile drag handle.

## Verification contract

- The main course surface has no peer `내 전공` or `교양` buttons.
- `전체 과목 추가` is not used because it can be read as selecting every course.
- Quick filters expose pressed state and an explicit reset only while a filter is active.
- The 390px editor keeps the timetable within its initial viewport budget.
- A real browser pointer gesture closes the mobile search sheet and `overscroll-behavior-y` is `none`.
- Light and dark themes use the same semantic states without horizontal overflow.
