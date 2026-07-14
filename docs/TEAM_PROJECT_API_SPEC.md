# 팀프로젝트 API 명세서

## 인증

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 회원가입 | POST | `/api/v1/auth/signup` | `studentNumber`, `name`, `grade`, `departmentId`, `consentVersion` | `user`, `accessToken`, `refreshToken` | `400 INVALID_REQUEST`, `409 ALREADY_REGISTERED` |
| 소셜 로그인 시작 | GET | `/api/v1/auth/oauth/{provider}` | Path: `provider` | `authorizationUrl` | `400 UNSUPPORTED_PROVIDER` |
| 소셜 로그인 완료 | POST | `/api/v1/auth/oauth/{provider}/callback` | `code`, `state` | `user`, `accessToken`, `refreshToken`, `isNewUser` | `400 INVALID_OAUTH_CODE`, `401 OAUTH_FAILED` |
| 로그인 세션 조회 | GET | `/api/v1/auth/session` | 없음 | `authenticated`, `user`, `expiresAt` | `401 SESSION_EXPIRED` |
| 토큰 재발급 | POST | `/api/v1/auth/refresh` | `refreshToken` | `accessToken`, `refreshToken`, `expiresAt` | `401 INVALID_REFRESH_TOKEN`, `401 SESSION_EXPIRED` |
| 로그아웃 | POST | `/api/v1/auth/logout` | `refreshToken` | `message` | `401 UNAUTHORIZED` |

## 사용자·개인정보 동의

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 내 계정정보 조회 | GET | `/api/v1/users/me` | 없음 | `id`, `studentNumber`, `name`, `grade`, `department`, `createdAt` | `401 UNAUTHORIZED` |
| 내 계정정보 변경 | PATCH | `/api/v1/users/me` | `name?`, `grade?`, `departmentId?` | 변경된 `user` | `400 INVALID_REQUEST`, `401 UNAUTHORIZED`, `404 DEPARTMENT_NOT_FOUND` |
| 개인정보 동의 등록 | POST | `/api/v1/users/me/consents` | `consentVersion`, `agreed` | `consentId`, `consentVersion`, `agreedAt` | `400 CONSENT_REQUIRED`, `401 UNAUTHORIZED` |
| 개인정보 동의 내역 조회 | GET | `/api/v1/users/me/consents` | 없음 | `consents[]` | `401 UNAUTHORIZED` |
| 회원 탈퇴 | DELETE | `/api/v1/users/me` | `confirmation` | `message`, `deletedAt` | `400 CONFIRMATION_REQUIRED`, `401 UNAUTHORIZED` |

## 학과·학기

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 학과 목록 조회 | GET | `/api/v1/departments` | Query: `keyword?` | `departments[]` | `500 INTERNAL_ERROR` |
| 학과 상세 조회 | GET | `/api/v1/departments/{departmentId}` | Path: `departmentId` | `department` | `404 DEPARTMENT_NOT_FOUND` |
| 학기 목록 조회 | GET | `/api/v1/semesters` | 없음 | `semesters[]`, `activeSemester` | `500 INTERNAL_ERROR` |
| 학기 데이터 버전 조회 | GET | `/api/v1/semesters/{semester}/version` | Path: `semester` | `semester`, `datasetVersion`, `updatedAt` | `404 SEMESTER_NOT_FOUND` |

## 강의 검색·정렬·필터

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 강의 목록 조회 | GET | `/api/v1/courses` | Query: `semester`, `keyword?`, `professor?`, `departmentId?`, `category?`, `area?`, `grade?`, `day?`, `sort?`, `order?`, `page?`, `size?` | `courses[]`, `page`, `size`, `total` | `400 INVALID_FILTER`, `404 SEMESTER_NOT_FOUND` |
| 강의 인기순 조회 | GET | `/api/v1/courses` | Query: `semester`, `sort=POPULARITY`, `order=DESC` | 인기 점수가 적용된 `courses[]` | `400 INVALID_SORT`, `404 SEMESTER_NOT_FOUND` |
| 강의 평점순 조회 | GET | `/api/v1/courses` | Query: `semester`, `sort=RATING`, `order=DESC` | 평균 별점이 적용된 `courses[]` | `400 INVALID_SORT`, `404 SEMESTER_NOT_FOUND` |
| 강의 이름순·역순 조회 | GET | `/api/v1/courses` | Query: `semester`, `sort=NAME`, `order=ASC 또는 DESC` | 정렬된 `courses[]` | `400 INVALID_SORT`, `404 SEMESTER_NOT_FOUND` |
| 강의 상세 조회 | GET | `/api/v1/courses/{courseCode}` | Path: `courseCode`, Query: `semester` | `course`, `sections[]`, `ratingSummary` | `404 COURSE_NOT_FOUND` |
| 강의 분반 목록 조회 | GET | `/api/v1/courses/{courseCode}/sections` | Path: `courseCode`, Query: `semester`, `professor?`, `day?` | `sections[]` | `404 COURSE_NOT_FOUND` |
| 분반 상세 조회 | GET | `/api/v1/sections/{sectionId}` | Path: `sectionId` | `section`, `sessions[]` | `404 SECTION_NOT_FOUND` |
| 대체 분반 조회 | GET | `/api/v1/sections/{sectionId}/alternatives` | Path: `sectionId`, Query: `timetableId?`, `sameProfessor?` | `alternatives[]`, `conflicts[]` | `404 SECTION_NOT_FOUND`, `404 TIMETABLE_NOT_FOUND` |

## 강의 리뷰·별점

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 강의 리뷰 목록 조회 | GET | `/api/v1/courses/{courseCode}/reviews` | Path: `courseCode`, Query: `professor?`, `semester?`, `sort?`, `page?`, `size?` | `reviews[]`, `ratingSummary`, `page`, `total` | `404 COURSE_NOT_FOUND` |
| 강의 리뷰 작성 | POST | `/api/v1/courses/{courseCode}/reviews` | `professor`, `semester`, `rating`, `content` | 생성된 `review`, `ratingSummary` | `400 INVALID_RATING`, `401 UNAUTHORIZED`, `409 REVIEW_ALREADY_EXISTS` |
| 리뷰 수정 | PATCH | `/api/v1/reviews/{reviewId}` | `rating?`, `content?` | 변경된 `review`, `ratingSummary` | `400 INVALID_RATING`, `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 REVIEW_NOT_FOUND` |
| 리뷰 삭제 | DELETE | `/api/v1/reviews/{reviewId}` | 없음 | `message`, `ratingSummary` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 REVIEW_NOT_FOUND` |
| 내가 작성한 리뷰 조회 | GET | `/api/v1/users/me/reviews` | Query: `page?`, `size?` | `reviews[]`, `page`, `total` | `401 UNAUTHORIZED` |
| 강의 별점 요약 조회 | GET | `/api/v1/courses/{courseCode}/ratings` | Path: `courseCode`, Query: `professor?` | `averageRating`, `reviewCount`, `popularityScore` | `404 COURSE_NOT_FOUND` |

## 시간표 저장·조회·수정

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 시간표 생성 | POST | `/api/v1/timetables` | `name`, `semester`, `sections[]`, `preferences?` | 생성된 `timetable` | `400 INVALID_TIMETABLE`, `401 UNAUTHORIZED`, `409 SECTION_CONFLICT` |
| 내 시간표 목록 조회 | GET | `/api/v1/timetables` | Query: `semester?`, `favorite?`, `page?`, `size?` | `timetables[]`, `page`, `total` | `401 UNAUTHORIZED` |
| 시간표 상세 조회 | GET | `/api/v1/timetables/{timetableId}` | Path: `timetableId` | `timetable`, `sections[]`, `metrics`, `conflicts[]` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND` |
| 시간표 이름·조건 변경 | PATCH | `/api/v1/timetables/{timetableId}` | `name?`, `preferences?` | 변경된 `timetable` | `400 INVALID_REQUEST`, `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND` |
| 시간표 강의 구성 변경 | PATCH | `/api/v1/timetables/{timetableId}/sections` | `sections[]` | `sections[]`, `metrics`, `conflicts[]` | `400 INVALID_SECTION`, `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND`, `409 SECTION_CONFLICT` |
| 시간표 삭제 | DELETE | `/api/v1/timetables/{timetableId}` | 없음 | `message` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND` |
| 시간표 복사 | POST | `/api/v1/timetables/{timetableId}/copy` | `name?` | 복사된 `timetable` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND` |
| 시간표 즐겨찾기 변경 | PATCH | `/api/v1/timetables/{timetableId}/favorite` | `favorite` | `timetableId`, `favorite` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND` |
| 이전 학기 시간표 조회 | GET | `/api/v1/timetables/history` | Query: `semester?` | 학기별 `timetables[]` | `401 UNAUTHORIZED` |
| 시간표 공유 링크 생성 | POST | `/api/v1/timetables/{timetableId}/shares` | `expiresAt?` | `shareCode`, `shareUrl`, `expiresAt` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 TIMETABLE_NOT_FOUND` |
| 공유 시간표 조회 | GET | `/api/v1/shared-timetables/{shareCode}` | Path: `shareCode` | `timetable`, `sections[]`, `metrics` | `404 SHARE_NOT_FOUND`, `410 SHARE_EXPIRED` |
| 공유 시간표 내 계정에 복사 | POST | `/api/v1/shared-timetables/{shareCode}/copy` | `name?` | 복사된 `timetable` | `401 UNAUTHORIZED`, `404 SHARE_NOT_FOUND`, `410 SHARE_EXPIRED` |

## 시간표 자동 편성

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 자동 편성 작업 생성 | POST | `/api/v1/optimizations` | `semester`, `datasetVersion`, `requiredCourseCodes[]`, `candidateCourseCodes[]`, `excludedCourseCodes[]`, `lockedSectionIds[]`, `professorConstraints[]`, `minCredits`, `maxCredits`, `targetCredits`, `preferredDaysOff[]`, `excludedDays[]`, `avoidBefore?`, `avoidAfter?`, `minGapMinutes?`, `maxGapMinutes?`, `minLunchMinutes?`, `maxDailyMinutes?`, `candidateCount` | `jobId`, `status`, `createdAt` | `400 INVALID_CONDITION`, `409 DATASET_VERSION_MISMATCH`, `422 INFEASIBLE_INPUT`, `429 RATE_LIMITED` |
| 자동 편성 상태·결과 조회 | GET | `/api/v1/optimizations/{jobId}` | Path: `jobId` | `status`, `candidates[]`, `relaxationSuggestions[]`, `error?` | `404 JOB_NOT_FOUND` |
| 자동 편성 작업 취소 | DELETE | `/api/v1/optimizations/{jobId}` | Path: `jobId` | `jobId`, `status=CANCELLED` | `404 JOB_NOT_FOUND`, `409 JOB_ALREADY_COMPLETED` |
| 시간표 후보 비교 | POST | `/api/v1/optimizations/compare` | `currentSectionIds[]`, `candidateSectionIds[][]` | 후보별 `metrics`, `added[]`, `removed[]`, `swapped[]`, `conflicts[]` | `400 INVALID_CANDIDATE`, `404 SECTION_NOT_FOUND` |

## 이수과목

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 내 이수과목 목록 조회 | GET | `/api/v1/users/me/completed-courses` | Query: `status?`, `semester?`, `category?` | `completedCourses[]`, `creditSummary` | `401 UNAUTHORIZED` |
| 이수과목 직접 등록 | POST | `/api/v1/users/me/completed-courses` | `courseCode?`, `courseName`, `credits`, `category`, `area?`, `semester?`, `status` | 생성된 `completedCourse` | `400 INVALID_COURSE`, `401 UNAUTHORIZED`, `409 COURSE_ALREADY_REGISTERED` |
| 이수과목 수정 | PATCH | `/api/v1/users/me/completed-courses/{completedCourseId}` | `courseName?`, `credits?`, `category?`, `area?`, `semester?`, `status?` | 변경된 `completedCourse` | `400 INVALID_REQUEST`, `401 UNAUTHORIZED`, `404 COMPLETED_COURSE_NOT_FOUND` |
| 이수과목 삭제 | DELETE | `/api/v1/users/me/completed-courses/{completedCourseId}` | 없음 | `message` | `401 UNAUTHORIZED`, `404 COMPLETED_COURSE_NOT_FOUND` |
| 현재 시간표를 수강 중 과목으로 등록 | POST | `/api/v1/users/me/completed-courses/import-timetable` | `timetableId`, `status=IN_PROGRESS` | `importedCourses[]`, `skippedCourses[]` | `401 UNAUTHORIZED`, `404 TIMETABLE_NOT_FOUND`, `409 COURSE_ALREADY_REGISTERED` |
| 이수학점 요약 조회 | GET | `/api/v1/users/me/completed-courses/summary` | 없음 | `totalCredits`, `majorCredits`, `liberalCredits`, `areaCredits` | `401 UNAUTHORIZED` |

## OCR

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 시간표·성적표 OCR 요청 | POST | `/api/v1/ocr/jobs` | Multipart: `image`, `documentType=TIMETABLE 또는 TRANSCRIPT` | `jobId`, `status`, `uploadedAt` | `400 INVALID_DOCUMENT_TYPE`, `401 UNAUTHORIZED`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_FILE_TYPE`, `429 RATE_LIMITED` |
| OCR 처리 상태·결과 조회 | GET | `/api/v1/ocr/jobs/{jobId}` | Path: `jobId` | `status`, `recognizedCourses[]`, `warnings[]`, `originalDeleted` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 OCR_JOB_NOT_FOUND`, `422 OCR_FAILED` |
| OCR 결과 확정 | POST | `/api/v1/ocr/jobs/{jobId}/confirm` | `courses[]` | `savedCourses[]`, `skippedCourses[]` | `400 INVALID_OCR_RESULT`, `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 OCR_JOB_NOT_FOUND`, `409 COURSE_ALREADY_REGISTERED` |
| OCR 작업 삭제 | DELETE | `/api/v1/ocr/jobs/{jobId}` | 없음 | `message`, `deletedAt` | `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 OCR_JOB_NOT_FOUND` |

## 졸업요건

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 졸업요건 규칙 조회 | GET | `/api/v1/requirements/rules` | Query: `admissionYear`, `departmentId`, `studentType`, `programPath` | `rules[]`, `sources[]`, `manualReviewItems[]` | `400 INVALID_PROFILE`, `404 REQUIREMENT_RULE_NOT_FOUND` |
| 내 졸업요건 점검 | POST | `/api/v1/requirements/evaluate` | `admissionYear`, `departmentId`, `studentType`, `programPath`, `completedCourses[]?` | `creditStatus`, `areaStatus[]`, `requiredCourseStatus[]`, `missingRequirements[]`, `manualReviewItems[]` | `400 INVALID_PROFILE`, `401 UNAUTHORIZED`, `422 INCOMPLETE_DATA` |
| 부족 과목 추천 | GET | `/api/v1/requirements/recommendations` | Query: `semester`, `admissionYear`, `departmentId`, `studentType`, `programPath` | `missingRequirements[]`, `recommendedCourses[]` | `401 UNAUTHORIZED`, `404 REQUIREMENT_RULE_NOT_FOUND`, `404 SEMESTER_NOT_FOUND` |
| 졸업요건 공식 근거 조회 | GET | `/api/v1/requirements/sources/{sourceId}` | Path: `sourceId` | `sourceId`, `title`, `url`, `effectiveDate`, `verifiedAt` | `404 SOURCE_NOT_FOUND` |

## 시스템

| 기능명 | Method | URL | 요청값 | 응답값 | 오류 |
| --- | --- | --- | --- | --- | --- |
| 서버 생존 상태 확인 | GET | `/api/v1/health/live` | 없음 | `status`, `version` | `503 SERVICE_UNAVAILABLE` |
| 서비스 준비 상태 확인 | GET | `/api/v1/health/ready` | 없음 | `status`, `database`, `catalog`, `optimizer` | `503 SERVICE_NOT_READY` |
