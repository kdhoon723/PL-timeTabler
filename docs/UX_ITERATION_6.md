# UX iteration 6 — required-course focus and weekly timetable colors

## Problems

1. `필수과목 확인` 바텀시트가 `1 필수 → 2 전공선택 → 3 교양선택` 순서와 다음 행동을 함께 보여줘, 실제 필수과목을 관리하는 도구보다 시간표 작성 튜토리얼처럼 보였다.
2. 시간표 색상이 과목 추가 순서에 따라 달라져 새로고침·자동 생성 결과에서 시각 순서가 불안정했다.
3. 일부 Galaxy/Samsung Internet 다크 모드 조합은 페이지가 이미 다크 테마를 제공해도 과목 블록을 추가 변환해 색을 탁하거나 검게 만들 수 있다.

## Product decisions

### Required-course sheet

- 바텀시트의 책임을 `이번 학기 필수과목`, 실제 개설 분반, 현재 배치 상태로 제한한다.
- 시간표 작성 순서, 전공선택·교양선택 탐색 버튼, 번호형 단계 표시는 제거한다.
- 전공선택과 교양선택은 메인 `과목 찾기`의 검색·필터에서 처리한다.
- 필수과목은 `전공필수`와 `교양필수`로만 나누고, 학과·학년·배치 과목 수·학점을 한 줄 요약으로 제공한다.

### DJPic-compatible palette

- `/home/kdhoon/projects/DJPic/popup.js`의 에브리타임 계열 20색 팔레트를 그대로 사용한다.
- 색상은 입력·추가 순서가 아니라 시간표의 가장 이른 수업을 기준으로 월요일 이른 시간부터 토요일 늦은 시간까지 배정한다.
- 같은 과목의 모든 세션과 분반은 같은 색을 유지한다.
- 20색 이후에만 팔레트를 반복한다.
- 정확한 색면을 라이트·다크에서 동일하게 유지하고 검정 전경을 사용한다. 20색 전체의 최소 명암비는 5.39:1이다.

### Galaxy and browser auto-dark protection

- 문서 전체는 `color-scheme: light dark`와 `prefers-color-scheme` 기반의 명시적 라이트·다크 테마를 유지한다.
- 과목 블록은 루트의 작성자 색상 체계를 상속한다. 라이트에서는 `light`, 다크에서는 `dark`로 계산돼야 하며 다크 환경에서 `only light`를 사용하지 않는다. 일부 Chromium 계열 브라우저는 `only light` 지원이 비활성화된 경우 이를 `light`로 취급해 밝은 색면과 검정 글자를 강제로 어둡게 변환한다.
- 과목 블록에는 opacity·filter·blend mode를 적용하지 않는다. 다크 모드의 구분은 불투명 색면과 밝은 경계선으로 만든다.
- Galaxy 기기 자체가 원인이라고 단정하지 않는다. Samsung Internet의 force-dark 모드, Chromium 계열 Auto Dark, 또는 이전 CSS 캐시가 색을 재변환할 수 있으므로 작성자 테마와 요소 단위 opt-out을 함께 제공한다.

## Verification contract

- 입력 배열이 섞여 있어도 월요일의 이른 과목이 `course-0`, 월요일의 다음 과목이 `course-1`, 화요일 과목이 그다음 색을 받는다.
- 라이트·다크의 각 과목 블록은 같은 불투명 RGB를 사용한다.
- 모든 과목 블록은 `opacity: 1`, `filter: none`, `mix-blend-mode: normal`을 유지하고, 계산된 `color-scheme`은 라이트에서 `light`, 다크에서 `dark`여야 한다.
- 데스크톱·태블릿·모바일 Playwright 프로젝트에서 색 순서·명암비·다크 변환 방지를 검증한다.
- 필수과목 시트에는 번호형 작성 순서와 전공선택·교양선택 이동 버튼이 없고, 실제 필수과목 및 배치 행동이 바로 보인다.

## References

- Samsung Internet, [Dark Mode in Samsung Internet](https://developer.samsung.com/internet/blog/en/2020/12/15/dark-mode-in-samsung-internet)
- Naver Whale Help, [다크 모드](https://help.whale.naver.com/ko/desktop/darkmode/)
- Chrome Developers, [Auto Dark Theme](https://developer.chrome.com/blog/auto-dark-theme)
- Chromium, [Implement color-scheme override per spec](https://chromium.googlesource.com/chromium/src/+/9a69785f81c63534ca6526e4a3fb2b162d9763cb)
- web.dev, [Improved dark mode default styling with the color-scheme CSS property and the corresponding meta tag](https://web.dev/articles/color-scheme)
