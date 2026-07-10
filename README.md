# PL-timeTabler

대학교 개설과목 데이터와 사용자 선호조건을 이용해 시간표를 쉽고 빠르게 구성하는 도구다.

## 목표

- 과목명·과목코드 자동완성
- 수업시간 충돌 실시간 검사
- 공강일 최대화와 수업 사이 빈 시간 최소화
- 오전 수업, 연강, 희망 학점 등 사용자 조건 반영
- 전공·교양영역 필터와 복수 시간표 추천
- 강의실 위치를 고려한 이동 부담 최소화

## 현재 상태

자동 시간표 생성기와 모바일 제품 구현을 검증할 2026학년도 1학기 테스트 데이터를 준비했다.

- 과목 및 분반: 1,576개
- 강의실: 325개
- 수업 세션: 1,693개
- 과목·강의실 결합 가능 분반: 1,336개
- 교육과정편람 원본: 2016~2026, 11개 연도
- 2026 현재 교육과정 단위: 46/46
- 2026 독립 졸업심사 단위: 44/44

데이터 구성과 출처는 [`data/README.md`](data/README.md)를 참고한다.

## 문서

- [`DESIGN.md`](DESIGN.md) — 모바일 우선 제품·UI/UX 설계 계약
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — React·FastAPI·OR-Tools·PostgreSQL·Docker Compose 아키텍처
- [`docs/PRODUCT_PLAN.md`](docs/PRODUCT_PLAN.md) — 완성형 제품 구현 단계와 출시 기준
- [`docs/IMPLEMENTATION_READINESS.md`](docs/IMPLEMENTATION_READINESS.md) — 구현 시작 판단, OR-Tools 검증 게이트, 실용 기능 우선순위
- [`docs/research/DAEJIN_GRADUATION_RULES.md`](docs/research/DAEJIN_GRADUATION_RULES.md) — 대진대 공통·학과별 졸업요건 공식 출처와 자동 판정 경계

## 다음 단계

1. 과목 데이터 정규화 및 시간 문자열 파서 작성
2. 입학연도·학과별 졸업요건과 교육과정 원천 데이터 정리
3. 충돌 검사와 OR-Tools 기반 시간표 생성기 구현
4. 자동완성 중심의 모바일 시간표 편집 UI 제작
5. 실제 사용 시나리오 기반 추천·접근성·성능 검증
