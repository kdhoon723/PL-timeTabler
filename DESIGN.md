# Design

## Source of truth

- Status: Active for product build
- Last refreshed: 2026-07-10
- Primary product surfaces: 모바일 우선 시간표 편집기, 과목 검색 시트, 보조 추천 결과
- Evidence reviewed: `README.md`, `data/README.md`, `data/manifest.json`
- Confirmed product decisions: 대진대 전용, 수동 편집 우선, 완전 자동 생성 포함, 로그인 없는 즉시 사용, 출시 수준 품질을 처음부터 적용

## Brand

- Personality: 빠르고 차분하며 학사정보를 신뢰할 수 있는 실용 도구
- Trust signals: 데이터 학기와 갱신일 표시, 충돌 여부의 즉시 피드백, 추천 변경 이유 표시
- Avoid: 첫 화면을 막는 소개 페이지, 과도한 장식과 유리 효과, 대시보드형 정보 과밀, 설명 없는 AI 추천

## Product goals

- Goals:
  - 로그인 없이 첫 화면에서 바로 시간표 작성을 시작한다.
  - 모바일에서도 한 손으로 과목 검색·추가·삭제·분반 변경이 가능하다.
  - 사용자가 고른 과목을 존중하면서 충돌 없는 분반과 더 나은 공강 구성을 제안한다.
  - 입학연도·학과·전공 방식에 맞는 졸업요건과 아직 부족한 교양·전공 영역을 근거와 함께 보여준다.
  - 필수과목, 후보과목, 희망 학점, 공강과 시간대 조건으로 설명 가능한 시간표 후보를 자동 생성한다.
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
  - `/`: 시간표 편집기
  - `/requirements`: 입학연도·학과별 졸업요건과 이수 현황
  - `/share/:id`: 공유 시간표의 읽기·복사 화면
- Content hierarchy:
  1. 현재 시간표와 충돌 상태
  2. 과목 추가 버튼과 검색
  3. 총 학점·공강일·빈 시간 요약
  4. 선택 과목 목록과 잠금 상태
  5. 수동 개선·자동 생성과 변경 이유
  6. 졸업요건 충족·부족 상태와 공식 근거

## Design principles

- **편집기가 첫 화면이다:** 소개나 설정을 먼저 요구하지 않는다.
- **드래그보다 탭을 우선한다:** 실제 강의시간은 고정이므로 모바일에서 불안정한 자유 드래그 대신 검색, 추가, 분반 교체를 명확한 탭 동작으로 제공한다.
- **추천은 사용자의 선택을 존중한다:** 잠근 과목은 유지하고 변경 수를 최소화한다.
- **자동 생성 후에도 편집권은 사용자에게 있다:** 생성 결과를 정답처럼 강요하지 않고 비교·부분 적용·되돌리기를 제공한다.
- **학사 규칙에는 근거가 따라야 한다:** 적용 연도와 원문을 확인할 수 없는 규칙은 확정 판정에 사용하지 않는다.
- **문제와 해결을 함께 보여준다:** 충돌만 알리지 않고 가능한 대체 분반을 바로 제시한다.
- **복잡성은 점진적으로 공개한다:** 처음에는 검색과 시간표만, 조건·추천은 필요할 때 펼친다.
- Tradeoffs: 화면 밀도보다 터치 정확성과 가독성을 우선한다. 수동 편집을 기본 경로로 유지하되 자동 생성은 별도 모드로 완성도 있게 제공한다.

## Visual language

- Color: 밝은 중립 배경, 높은 대비의 본문, 과목 구분용 제한된 색상 팔레트, 오류는 색상과 아이콘·텍스트를 함께 사용
- Typography: 모바일 본문 16px 기준, 시간표 내부는 축약하되 12px 미만을 사용하지 않는다.
- Spacing/layout rhythm: 4px 기반 간격, 주요 터치 대상은 최소 44px로 설계
- Shape/radius/elevation: 중간 정도의 둥근 모서리, 시트와 고정 컨트롤에만 절제된 그림자
- Motion: 시트 전환과 추천 비교에 짧은 전환만 사용하며 `prefers-reduced-motion`을 존중
- Imagery/iconography: 기능 의미가 분명한 선형 아이콘, 아이콘 단독 버튼에는 접근 가능한 이름 제공

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
  - `RequirementNavigator`: 입학연도·학과별 졸업요건과 부족 영역
  - `SourceEvidence`: 규칙의 원문, 적용 대상, 기준일 표시
- Variants and states: 기본, 선택, 잠금, 충돌, 시간 미정, 강의실 미상, 추천 변경 예정
- Token/component ownership: 색상·간격·타이포 토큰은 앱 전역에서 정의하고 기능 컴포넌트가 임의 값을 추가하지 않는다.

## Accessibility

- Target standard: [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/)
- Keyboard/focus behavior: 검색 결과와 분반 목록을 키보드로 이동·선택할 수 있고, 바텀시트 포커스를 관리하며 닫은 뒤 트리거로 복귀
- Contrast/readability: 일반 텍스트 AA 대비, 과목 구분을 색상에만 의존하지 않음
- Screen-reader semantics: 시간표는 시각 격자 외에 요일·시간·과목을 읽을 수 있는 구조화된 대체 목록 제공
- Reduced motion and sensory considerations: 모션 축소 설정 지원, 오류·추천 상태를 색상 외 텍스트로 설명

## Responsive behavior

- Supported breakpoints/devices: 최소 360px 모바일부터 태블릿·데스크톱까지
- Layout adaptations:
  - 모바일: 시간표 중심 단일 화면 + 하단 고정 과목 추가 버튼 + 바텀시트
  - 태블릿: 시간표와 선택 과목 요약을 병렬 배치
  - 데스크톱: 검색 패널, 시간표, 선택·추천 요약의 3영역 구성
- Touch/hover differences: 핵심 기능은 hover 없이 동작하며 길게 누르기나 정밀 드래그를 필수 동작으로 사용하지 않는다.

## Interaction states

- Loading: 앱 골격과 데이터 로딩 진행을 표시하되 기존 시간표가 있으면 먼저 복원
- Empty: 빈 격자 위에 간단한 한 문장과 `과목 추가` 기본 행동 제공
- Error: 데이터 로딩 실패, 잘못된 시간 형식, 저장 복원 실패를 구분하고 재시도 제공
- Success: 과목 추가·추천 적용 후 짧은 상태 메시지와 실행 취소 제공
- Disabled: 비활성 이유를 인접 텍스트로 설명
- Offline/slow network: 정적 데이터 로딩 이후 편집은 네트워크 요청 없이 동작하도록 설계

## Content voice

- Tone: 짧고 직접적이며 학생이 쓰는 표현을 우선
- Terminology: `과목`, `분반`, `공강`, `빈 시간`, `잠금`, `충돌`, `시간 미정`
- Microcopy rules:
  - `최적화`보다 결과를 설명하는 `공강 늘리기`, `빈 시간 줄이기`를 우선한다.
  - 추천은 `화요일 공강을 만들기 위해 2개 분반을 변경합니다`처럼 변경과 이유를 함께 쓴다.
  - 오류는 `추가할 수 없음`에서 끝내지 않고 `02분반은 충돌하지 않습니다`처럼 다음 행동을 제시한다.

## Implementation constraints

- Framework/styling system: React + TypeScript 프론트엔드, Python + FastAPI 백엔드, OpenAPI로 생성하는 TypeScript SDK
- Optimization: API와 분리된 Python optimizer 프로세스에서 OR-Tools CP-SAT 실행
- Data/storage: PostgreSQL + Alembic migration, 개인 편집 상태는 브라우저 저장 우선
- Deployment: web/API/optimizer/DB/migration을 Docker Compose로 실행하며 개발 전용 차이는 별도 Compose 파일로 관리
- Design-token constraints: 단일 토큰 집합을 사용하고 기능별 별도 테마를 만들지 않음
- Performance constraints: 과목 검색은 로컬 인덱스로 처리하고 강의실 상세는 필요할 때 로드
- Compatibility constraints: 모바일 Safari와 Android Chrome을 우선 검증
- Test/screenshot expectations: 360px, 390px, 768px, 1440px 뷰포트의 핵심 상태를 시각 회귀 대상으로 유지

## Open questions

- [ ] 최종 서비스명과 로고가 필요한가 / 제품 / 시각 톤에 영향
- [ ] 시간표 공유에서 URL·이미지·PDF의 우선순위 / 제품 / 내보내기 흐름에 영향
- [ ] 야간·토요일 수업 표시 요구가 있는가 / 데이터·제품 / 격자 범위에 영향
- [ ] 실제 사용자 테스트 참여자를 어떻게 모집할까 / 제품 / 출시 기준에 영향
- [ ] 비공개 포털 성적 없이 기존 이수내역을 입력하는 최소 부담 방식 / 제품·개인정보 / 졸업요건 정확도에 영향
