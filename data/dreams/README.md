# DREAMS2 강의 이력 아카이브

대진대학교 DREAMS2 수강편람에서 인증 세션으로 수집한 2020~2026학년도 강의 목록, 강의계획서, 연도별 교육과정, 대체·동일과목 관계를 저장한다. 사용자의 과거 시간표를 `(학년도, 학기, 교과목코드, 분반)`으로 식별하고 이수구분·학점·학과 맥락과 연결하기 위한 원천 아카이브다.

## 수집 범위

- 수집 시각: 각 파일과 [`manifest.json`](manifest.json)의 `collectedAt`/`generatedAt` 참고
- 학년도: 2020~2026
- 학기 코드: `1`(1학기), `2`(2학기), `11`(여름계절), `22`(겨울계절)
- 학기 파일: 28개
- 분반-학기 레코드: 20,031개
- 상세 강의계획서 확인: 19,898개
- 원문 미입력 또는 자동 복귀: 133개 (`detailStatus: "BLANK"`)
- 연도별 교육과정: 7개 파일, 12,216행
- 대체과목 관계: 807건
- 동일과목 관계: 518건

2026-2는 수집 시점의 사전 공개 데이터이므로 `PRELIMINARY`, 2026-11은 `CURRENT`, 아직 데이터가 없는 2026-22는 `EMPTY_FUTURE`다. 나머지는 수집 시점 기준 `FINAL`로 분류한다. 이 상태는 폐강 여부가 아니라 데이터 성숙도를 뜻한다.

## 파일 구조

```text
data/dreams/
├── manifest.json
├── terms/
│   ├── 2020-1.json.gz
│   ├── ...
│   └── 2026-22.json.gz
├── curricula/
│   ├── curriculum-2020.json.gz
│   ├── ...
│   └── curriculum-2026.json.gz
└── relations.json.gz
```

모든 압축 파일은 UTF-8 JSON을 deterministic gzip으로 저장한다. `manifest.json`에는 파일별 SHA-256, 바이트 수, 레코드 수와 상세 필드 커버리지가 있다.

## 학기 데이터 계약

`terms/<학년도>-<학기코드>.json.gz`의 `sections`는 다음 데이터를 포함한다.

- 식별: `courseCode`, `sectionCode`, `koreanName`, `englishName`
- 수강 정보: `completionCategory`, `credits`, `lectureHours`, `practiceHours`
- 시간표 정보: `rawLectureTime`, `rawLocation`, `targetGrade`, `professorName`
- 분류 맥락: `categoryContexts`, `departmentContexts`
- 상태: `listingStatus`, `detailStatus`
- 강의계획서:
  - 개요, 선수요건, 학습목표
  - 핵심역량·전공역량과 비중/목표
  - 수업형태·수업방법·수업매체
  - 평가요소·비율·기준
  - 교재·참고문헌, 과제
  - 주차/날짜별 수업주제·내용·방법·준비사항·자료
  - 연계 비교과 프로그램

과목의 안정적인 결합키는 학기를 포함한 `(academicYear, termCode, courseCode, sectionCode)`다. 과목코드만으로는 재개설·과목명 변경·분반 변화를 구분할 수 없다.

`categoryContexts`는 교양필수·교양선택·전공 등 포털 조회 코드와 교양 영역을 보존한다. `departmentContexts`는 해당 학과 코드로 전공 조회했을 때 반환된 분반에만 붙는다. 교양·교직·일반선택 과목에 학과 맥락이 없는 것은 정상이다.

## 교육과정·과목 관계

- `curricula/curriculum-<연도>.json.gz`: 포털에 노출된 대학/학과 코드와 학년, 권장학기, 이수구분, 과목명, 학점, 강의/실습 시수, 강의유형
- `relations.json.gz`: 대체과목과 동일과목 표의 전체 역사 관계

교육과정 표에는 교과목코드가 제공되지 않으므로, 이름만으로 자동 확정하지 않는다. 시간표 분반의 코드·학기·학과 맥락을 우선 사용하고, 교육과정/동일·대체과목 이름은 후보 매칭과 졸업요건 해석의 보조 근거로 사용한다.

## 결측과 개인정보 원칙

- `BLANK`는 수집 실패가 아니라 포털이 상세 표를 제공하지 않거나 자동으로 이전 화면으로 복귀한 경우다.
- 향후 학기, 온라인 수업, 계절학기는 장소·시간·주차계획이 비어 있을 수 있다.
- 포털은 과거 폐강 상태를 일관된 API로 제공하지 않으므로 모든 반환 분반을 `LISTED`로 저장하며 개설 확정/폐강을 추정하지 않는다.
- 담당교수명은 강의 식별·선택에 필요한 공개 강의정보로 보존한다.
- 내부 교번, 연구실, 전화번호, 이메일, 면담시간, 계정, 비밀번호, 쿠키, 세션 값은 저장하지 않는다. 자유서술에서 이메일·전화번호 형태가 발견되면 수집 단계에서 제거한다.

## 재수집과 검증

기본 실행은 유효한 기존 파일을 재사용하므로 중단 후 다시 실행할 수 있다.

```bash
node scripts/collect-dreams-history.cjs --from 2020 --to 2026 --terms 1,2,11,22
node scripts/validate-dreams-archive.cjs
```

특정 범위를 원문에서 다시 받으려면 `--years`, `--terms`, `--force`를 조합한다. `--limit`가 사용된 파일은 개발용이며 검증기가 배포 가능한 아카이브로 인정하지 않는다.

검증기는 다음을 확인한다.

- 매니페스트 SHA-256과 바이트 수
- gzip/JSON 및 스키마 버전
- 학기별 `(courseCode, sectionCode)` 중복
- 매니페스트/실데이터 건수와 상세 커버리지 일치
- 28개 학기, 7개 교육과정, 관계 파일의 범위 완전성
- 내부 교번·연락처·계정·세션 키와 이메일/전화번호 형태의 부재

## 기존 2026-1 fixture와의 관계

`data/courses/courses-2026-1.json`은 별도 시점에 만든 제품 고정 fixture(1,576개)이고, 이 아카이브의 2026-1은 2026-07-14 포털 조회 결과(1,489개)다. 원본 시점과 포함 범위가 다르므로 새 아카이브가 기존 fixture를 자동으로 덮어쓰지 않는다. 앱에 연결할 때는 별도 import/정규화 단계와 회귀 테스트를 거친다.
