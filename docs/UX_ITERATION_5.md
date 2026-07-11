# UX iteration 5 — vivid timetable course colors

## Problem

The previous timetable palette used six low-saturation colors selected from a course-code hash. In dark mode the blocks blended into the grid and were difficult to scan. Hash assignment also made the apparent color order feel arbitrary instead of matching the student's act of building a timetable.

## Reference

The existing DJPic project (`/home/kdhoon/projects/DJPic/popup.js`) uses an Everytime-inspired palette and assigns colors to unique course names in the order they first appear. PL-timeTabler adopts that interaction principle without copying DJPic's presentation structure.

## Product decision

- Assign colors by the order in which unique course codes first appear in the current timetable.
- Keep every session of the same course on the same color.
- Use ten medium-saturation hues before repeating the palette.
- Define separate light and dark theme tokens instead of applying opacity or mechanically inverting colors.
- Use a dark foreground on the vivid color surfaces and keep every foreground/background pair at a contrast ratio of at least 5:1.
- Preserve conflict, preview, and drag states with borders and labels; color is course identity, not status.

## Verification contract

- The first three unique courses receive `course-0`, `course-1`, and `course-2` regardless of course-code sorting or hashing.
- Light and dark themes render three distinct opaque backgrounds for three courses.
- Every measured course-block foreground/background pair has at least 5:1 contrast.
- Dark-mode blocks use `opacity: 1`, `filter: none`, and `mix-blend-mode: normal` outside explicit preview or drag states.
- Mobile, tablet, and desktop Playwright projects exercise the ordered palette and contrast assertions.
