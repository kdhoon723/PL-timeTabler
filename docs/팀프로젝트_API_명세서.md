# 팀프로젝트 API 명세서

## API 명세서

| 기능 | HTTP 메서드 | API Path | 구현여부 | Request | Response | 요청 타입 | 담당자 | 오류 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (1) 인증 | ------------- |  | No |  |  |  |  |  |
| (1-1) 학교 이메일 인증번호 요청 | POST | /api/v1/auth/otp/start | Yes | OtpStartRequest | OtpStartResponse | application/json |  | 400 INVALID_STUDENT_NUMBER, 429 TOO_MANY_REQUESTS, 503 EMAIL_SEND_FAILED |
| (1-2) 학교 이메일 OTP 로그인 | POST | /api/v1/auth/otp/verify | Yes | OtpVerifyRequest | OtpVerifyResponse | application/json |  | 400 INVALID_CODE_FORMAT, 401 INVALID_OR_EXPIRED_CODE, 429 TOO_MANY_ATTEMPTS |
| (1-3) 로그인 세션 조회 | GET | /api/v1/auth/session | Yes |  | AuthSessionResponse |  |  | 401 SESSION_EXPIRED |
| (1-4) 로그아웃 | POST | /api/v1/auth/logout | Yes |  | LogoutResponse |  |  | 401 UNAUTHORIZED |
| (2) 사용자·개인정보 동의 | ------------- |  | No |  |  |  |  |  |
| (2-1) 내 계정정보 조회 | GET | /api/v1/users/me | No |  | UserInfoResponse |  |  | 401 UNAUTHORIZED |
| (2-2) 내 계정정보 변경 | PATCH | /api/v1/users/me | No | UserUpdateRequest | UserUpdateResponse | application/json |  | 400 INVALID_REQUEST, 401 UNAUTHORIZED, 404 DEPARTMENT_NOT_FOUND |
| (2-3) 개인정보 동의 등록 | POST | /api/v1/users/me/consents | No | ConsentCreateRequest | ConsentCreateResponse | application/json |  | 400 CONSENT_REQUIRED, 401 UNAUTHORIZED |
| (2-4) 개인정보 동의 내역 조회 | GET | /api/v1/users/me/consents | No |  | ConsentListResponse |  |  | 401 UNAUTHORIZED |
| (2-5) 회원 탈퇴 | DELETE | /api/v1/users/me | No | confirmation | UserDeleteResponse |  |  | 400 CONFIRMATION_REQUIRED, 401 UNAUTHORIZED |
| (3) 학과·학기 | ------------- |  | No |  |  |  |  |  |
| (3-1) 학과 목록 조회 | GET | /api/v1/departments | No | Query: keyword? | DepartmentListResponse |  |  | 500 INTERNAL_ERROR |
| (3-2) 학과 상세 조회 | GET | /api/v1/departments/{departmentId} | No | Path: departmentId | DepartmentDetailResponse |  |  | 404 DEPARTMENT_NOT_FOUND |
| (3-3) 학기 목록 조회 | GET | /api/v1/semesters | Yes |  | SemesterListResponse |  |  | 500 INTERNAL_ERROR |
| (3-4) 학기 데이터 버전 조회 | GET | /api/v1/semesters/{semester}/version | No | Path: semester | SemesterVersionResponse |  |  | 404 SEMESTER_NOT_FOUND |
| (4) 강의 검색·정렬·필터 | ------------- |  | No |  |  |  |  |  |
| (4-1) 강의 목록 조회 | GET | /api/v1/courses | No | Query: semester, keyword?, professor?, departmentId?, category?, area?, grade?, day?, sort?, order?, page?, size? | CourseListResponse |  |  | 400 INVALID_FILTER, 404 SEMESTER_NOT_FOUND |
| (4-2) 강의 인기순 조회 | GET | /api/v1/courses | No | Query: semester, sort=POPULARITY, order=DESC | PopularCourseListResponse |  |  | 400 INVALID_SORT, 404 SEMESTER_NOT_FOUND |
| (4-3) 강의 평점순 조회 | GET | /api/v1/courses | No | Query: semester, sort=RATING, order=DESC | RatedCourseListResponse |  |  | 400 INVALID_SORT, 404 SEMESTER_NOT_FOUND |
| (4-4) 강의 이름순·역순 조회 | GET | /api/v1/courses | No | Query: semester, sort=NAME, order=ASC 또는 DESC | NamedCourseListResponse |  |  | 400 INVALID_SORT, 404 SEMESTER_NOT_FOUND |
| (4-5) 강의 상세 조회 | GET | /api/v1/courses/{courseCode} | No | Path: courseCode, Query: semester | CourseDetailResponse |  |  | 404 COURSE_NOT_FOUND |
| (4-6) 강의 분반 목록 조회 | GET | /api/v1/courses/{courseCode}/sections | No | Path: courseCode, Query: semester, professor?, day? | CourseSectionListResponse |  |  | 404 COURSE_NOT_FOUND |
| (4-7) 분반 상세 조회 | GET | /api/v1/sections/{sectionId} | No | Path: sectionId | SectionDetailResponse |  |  | 404 SECTION_NOT_FOUND |
| (4-8) 대체 분반 조회 | GET | /api/v1/sections/{sectionId}/alternatives | No | Path: sectionId, Query: timetableId?, sameProfessor? | AlternativeSectionListResponse |  |  | 404 SECTION_NOT_FOUND, 404 TIMETABLE_NOT_FOUND |
| (5) 강의 리뷰·별점 | ------------- |  | No |  |  |  |  |  |
| (5-1) 강의 리뷰 목록 조회 | GET | /api/v1/courses/{courseCode}/reviews | No | Path: courseCode, Query: professor?, semester?, sort?, page?, size? | CourseReviewListResponse |  |  | 404 COURSE_NOT_FOUND |
| (5-2) 강의 리뷰 작성 | POST | /api/v1/courses/{courseCode}/reviews | No | CourseReviewCreateRequest | CourseReviewCreateResponse | application/json |  | 400 INVALID_RATING, 401 UNAUTHORIZED, 409 REVIEW_ALREADY_EXISTS |
| (5-3) 리뷰 수정 | PATCH | /api/v1/reviews/{reviewId} | No | CourseReviewUpdateRequest | CourseReviewUpdateResponse | application/json |  | 400 INVALID_RATING, 401 UNAUTHORIZED, 403 FORBIDDEN, 404 REVIEW_NOT_FOUND |
| (5-4) 리뷰 삭제 | DELETE | /api/v1/reviews/{reviewId} | No |  | CourseReviewDeleteResponse |  |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 REVIEW_NOT_FOUND |
| (5-5) 내가 작성한 리뷰 조회 | GET | /api/v1/users/me/reviews | No | Query: page?, size? | MyReviewListResponse |  |  | 401 UNAUTHORIZED |
| (5-6) 강의 별점 요약 조회 | GET | /api/v1/courses/{courseCode}/ratings | No | Path: courseCode, Query: professor? | CourseRatingSummaryResponse |  |  | 404 COURSE_NOT_FOUND |
| (6) 시간표 저장·조회·수정 | ------------- |  | No |  |  |  |  |  |
| (6-1) 시간표 생성 | POST | /api/v1/timetables | No | TimetableCreateRequest | TimetableCreateResponse | application/json |  | 400 INVALID_TIMETABLE, 401 UNAUTHORIZED, 409 SECTION_CONFLICT |
| (6-2) 내 시간표 목록 조회 | GET | /api/v1/timetables | No | Query: semester?, favorite?, page?, size? | TimetableListResponse |  |  | 401 UNAUTHORIZED |
| (6-3) 시간표 상세 조회 | GET | /api/v1/timetables/{timetableId} | No | Path: timetableId | TimetableDetailResponse |  |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND |
| (6-4) 시간표 이름·조건 변경 | PATCH | /api/v1/timetables/{timetableId} | No | TimetableUpdateRequest | TimetableUpdateResponse | application/json |  | 400 INVALID_REQUEST, 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND |
| (6-5) 시간표 강의 구성 변경 | PATCH | /api/v1/timetables/{timetableId}/sections | No | TimetableSectionUpdateRequest | TimetableSectionUpdateResponse | application/json |  | 400 INVALID_SECTION, 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND, 409 SECTION_CONFLICT |
| (6-6) 시간표 삭제 | DELETE | /api/v1/timetables/{timetableId} | No |  | TimetableDeleteResponse |  |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND |
| (6-7) 시간표 복사 | POST | /api/v1/timetables/{timetableId}/copy | No | TimetableCopyRequest | TimetableCopyResponse | application/json |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND |
| (6-8) 시간표 즐겨찾기 변경 | PATCH | /api/v1/timetables/{timetableId}/favorite | No | TimetableFavoriteUpdateRequest | TimetableFavoriteUpdateResponse | application/json |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND |
| (6-9) 이전 학기 시간표 조회 | GET | /api/v1/timetables/history | No | Query: semester? | TimetableHistoryResponse |  |  | 401 UNAUTHORIZED |
| (6-10) 시간표 공유 링크 생성 | POST | /api/v1/timetables/{timetableId}/shares | No | TimetableShareCreateRequest | TimetableShareCreateResponse | application/json |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 TIMETABLE_NOT_FOUND |
| (6-11) 공유 시간표 조회 | GET | /api/v1/shared-timetables/{shareCode} | No | Path: shareCode | SharedTimetableResponse |  |  | 404 SHARE_NOT_FOUND, 410 SHARE_EXPIRED |
| (6-12) 공유 시간표 내 계정에 복사 | POST | /api/v1/shared-timetables/{shareCode}/copy | No | SharedTimetableCopyRequest | SharedTimetableCopyResponse | application/json |  | 401 UNAUTHORIZED, 404 SHARE_NOT_FOUND, 410 SHARE_EXPIRED |
| (7) 시간표 자동 편성 | ------------- |  | No |  |  |  |  |  |
| (7-1) 자동 편성 작업 생성 | POST | /api/v1/optimizations | Yes | OptimizationCreateRequest | OptimizationCreateResponse | application/json |  | 400 INVALID_CONDITION, 409 DATASET_VERSION_MISMATCH, 422 INFEASIBLE_INPUT, 429 RATE_LIMITED |
| (7-2) 자동 편성 상태·결과 조회 | GET | /api/v1/optimizations/{jobId} | Yes | Path: jobId | OptimizationResultResponse |  |  | 404 JOB_NOT_FOUND |
| (7-3) 자동 편성 작업 취소 | DELETE | /api/v1/optimizations/{jobId} | Yes | Path: jobId | OptimizationCancelResponse |  |  | 404 JOB_NOT_FOUND, 409 JOB_ALREADY_COMPLETED |
| (7-4) 시간표 후보 비교 | POST | /api/v1/optimizations/compare | No | CandidateCompareRequest | CandidateCompareResponse | application/json |  | 400 INVALID_CANDIDATE, 404 SECTION_NOT_FOUND |
| (8) 이수과목 | ------------- |  | No |  |  |  |  |  |
| (8-1) 내 이수과목 목록 조회 | GET | /api/v1/users/me/completed-courses | No | Query: status?, semester?, category? | CompletedCourseListResponse |  |  | 401 UNAUTHORIZED |
| (8-2) 이수과목 직접 등록 | POST | /api/v1/users/me/completed-courses | No | CompletedCourseCreateRequest | CompletedCourseCreateResponse | application/json |  | 400 INVALID_COURSE, 401 UNAUTHORIZED, 409 COURSE_ALREADY_REGISTERED |
| (8-3) 이수과목 수정 | PATCH | /api/v1/users/me/completed-courses/{completedCourseId} | No | CompletedCourseUpdateRequest | CompletedCourseUpdateResponse | application/json |  | 400 INVALID_REQUEST, 401 UNAUTHORIZED, 404 COMPLETED_COURSE_NOT_FOUND |
| (8-4) 이수과목 삭제 | DELETE | /api/v1/users/me/completed-courses/{completedCourseId} | No |  | CompletedCourseDeleteResponse |  |  | 401 UNAUTHORIZED, 404 COMPLETED_COURSE_NOT_FOUND |
| (8-5) 현재 시간표를 수강 중 과목으로 등록 | POST | /api/v1/users/me/completed-courses/import-timetable | No | TimetableCourseImportRequest | TimetableCourseImportResponse | application/json |  | 401 UNAUTHORIZED, 404 TIMETABLE_NOT_FOUND, 409 COURSE_ALREADY_REGISTERED |
| (8-6) 이수학점 요약 조회 | GET | /api/v1/users/me/completed-courses/summary | No |  | CompletedCreditSummaryResponse |  |  | 401 UNAUTHORIZED |
| (9) OCR | ------------- |  | No |  |  |  |  |  |
| (9-1) 시간표·성적표 OCR 요청 | POST | /api/v1/ocr/jobs | No | OcrJobCreateRequest | OcrJobCreateResponse | multipart/form-data |  | 400 INVALID_DOCUMENT_TYPE, 401 UNAUTHORIZED, 413 FILE_TOO_LARGE, 415 UNSUPPORTED_FILE_TYPE, 429 RATE_LIMITED |
| (9-2) OCR 처리 상태·결과 조회 | GET | /api/v1/ocr/jobs/{jobId} | No | Path: jobId | OcrJobResultResponse |  |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 OCR_JOB_NOT_FOUND, 422 OCR_FAILED |
| (9-3) OCR 결과 확정 | POST | /api/v1/ocr/jobs/{jobId}/confirm | No | OcrResultConfirmRequest | OcrResultConfirmResponse | application/json |  | 400 INVALID_OCR_RESULT, 401 UNAUTHORIZED, 403 FORBIDDEN, 404 OCR_JOB_NOT_FOUND, 409 COURSE_ALREADY_REGISTERED |
| (9-4) OCR 작업 삭제 | DELETE | /api/v1/ocr/jobs/{jobId} | No |  | OcrJobDeleteResponse |  |  | 401 UNAUTHORIZED, 403 FORBIDDEN, 404 OCR_JOB_NOT_FOUND |
| (10) 졸업요건 | ------------- |  | No |  |  |  |  |  |
| (10-1) 졸업요건 규칙 조회 | GET | /api/v1/requirements/rules | No | Query: admissionYear, departmentId, studentType, programPath | RequirementRuleListResponse |  |  | 400 INVALID_PROFILE, 404 REQUIREMENT_RULE_NOT_FOUND |
| (10-2) 내 졸업요건 점검 | POST | /api/v1/requirements/evaluate | No | RequirementEvaluationRequest | RequirementEvaluationResponse | application/json |  | 400 INVALID_PROFILE, 401 UNAUTHORIZED, 422 INCOMPLETE_DATA |
| (10-3) 부족 과목 추천 | GET | /api/v1/requirements/recommendations | No | Query: semester, admissionYear, departmentId, studentType, programPath | RequirementRecommendationResponse |  |  | 401 UNAUTHORIZED, 404 REQUIREMENT_RULE_NOT_FOUND, 404 SEMESTER_NOT_FOUND |
| (10-4) 졸업요건 공식 근거 조회 | GET | /api/v1/requirements/sources/{sourceId} | No | Path: sourceId | RequirementSourceResponse |  |  | 404 SOURCE_NOT_FOUND |
| (11) 시스템 | ------------- |  | No |  |  |  |  |  |
| (11-1) 서버 생존 상태 확인 | GET | /api/v1/health/live | Yes |  | HealthLiveResponse |  |  | 503 SERVICE_UNAVAILABLE |
| (11-2) 서비스 준비 상태 확인 | GET | /api/v1/health/ready | Yes |  | HealthReadyResponse |  |  | 503 SERVICE_NOT_READY |


---

## DTO(데이터 전달 객체)

| 이름 | API 분류 | 태그 | 필드 |
| --- | --- | --- | --- |
| OtpStartRequest | API Request | DTO(요청 객체) | studentNumber |
| OtpStartResponse | API Response | DTO(응답 객체) | message, cooldownSeconds, expiresInSeconds |
| OtpVerifyRequest | API Request | DTO(요청 객체) | studentNumber, code |
| OtpVerifyResponse | API Response | DTO(응답 객체) | authenticated, user, isNewUser, expiresAt |
| AuthSessionResponse | API Response | DTO(응답 객체) | authenticated, user, expiresAt |
| LogoutResponse | API Response | DTO(응답 객체) | message |
| UserInfoResponse | API Response | DTO(응답 객체) | id, studentNumber, name, grade, department, createdAt |
| UserUpdateRequest | API Request | DTO(요청 객체) | name?, grade?, departmentId? |
| UserUpdateResponse | API Response | DTO(응답 객체) | 변경된 user |
| ConsentCreateRequest | API Request | DTO(요청 객체) | consentVersion, agreed |
| ConsentCreateResponse | API Response | DTO(응답 객체) | consentId, consentVersion, agreedAt |
| ConsentListResponse | API Response | DTO(응답 객체) | consents[] |
| UserDeleteResponse | API Response | DTO(응답 객체) | message, deletedAt |
| DepartmentListResponse | API Response | DTO(응답 객체) | departments[] |
| DepartmentDetailResponse | API Response | DTO(응답 객체) | department |
| SemesterListResponse | API Response | DTO(응답 객체) | semesters[], activeSemester |
| SemesterVersionResponse | API Response | DTO(응답 객체) | semester, datasetVersion, updatedAt |
| CourseListResponse | API Response | DTO(응답 객체) | courses[], page, size, total |
| PopularCourseListResponse | API Response | DTO(응답 객체) | 인기 점수가 적용된 courses[] |
| RatedCourseListResponse | API Response | DTO(응답 객체) | 평균 별점이 적용된 courses[] |
| NamedCourseListResponse | API Response | DTO(응답 객체) | 정렬된 courses[] |
| CourseDetailResponse | API Response | DTO(응답 객체) | course, sections[], ratingSummary |
| CourseSectionListResponse | API Response | DTO(응답 객체) | sections[] |
| SectionDetailResponse | API Response | DTO(응답 객체) | section, sessions[] |
| AlternativeSectionListResponse | API Response | DTO(응답 객체) | alternatives[], conflicts[] |
| CourseReviewListResponse | API Response | DTO(응답 객체) | reviews[], ratingSummary, page, total |
| CourseReviewCreateRequest | API Request | DTO(요청 객체) | professor, semester, rating, content |
| CourseReviewCreateResponse | API Response | DTO(응답 객체) | 생성된 review, ratingSummary |
| CourseReviewUpdateRequest | API Request | DTO(요청 객체) | rating?, content? |
| CourseReviewUpdateResponse | API Response | DTO(응답 객체) | 변경된 review, ratingSummary |
| CourseReviewDeleteResponse | API Response | DTO(응답 객체) | message, ratingSummary |
| MyReviewListResponse | API Response | DTO(응답 객체) | reviews[], page, total |
| CourseRatingSummaryResponse | API Response | DTO(응답 객체) | averageRating, reviewCount, popularityScore |
| TimetableCreateRequest | API Request | DTO(요청 객체) | name, semester, sections[], preferences? |
| TimetableCreateResponse | API Response | DTO(응답 객체) | 생성된 timetable |
| TimetableListResponse | API Response | DTO(응답 객체) | timetables[], page, total |
| TimetableDetailResponse | API Response | DTO(응답 객체) | timetable, sections[], metrics, conflicts[] |
| TimetableUpdateRequest | API Request | DTO(요청 객체) | name?, preferences? |
| TimetableUpdateResponse | API Response | DTO(응답 객체) | 변경된 timetable |
| TimetableSectionUpdateRequest | API Request | DTO(요청 객체) | sections[] |
| TimetableSectionUpdateResponse | API Response | DTO(응답 객체) | sections[], metrics, conflicts[] |
| TimetableDeleteResponse | API Response | DTO(응답 객체) | message |
| TimetableCopyRequest | API Request | DTO(요청 객체) | name? |
| TimetableCopyResponse | API Response | DTO(응답 객체) | 복사된 timetable |
| TimetableFavoriteUpdateRequest | API Request | DTO(요청 객체) | favorite |
| TimetableFavoriteUpdateResponse | API Response | DTO(응답 객체) | timetableId, favorite |
| TimetableHistoryResponse | API Response | DTO(응답 객체) | 학기별 timetables[] |
| TimetableShareCreateRequest | API Request | DTO(요청 객체) | expiresAt? |
| TimetableShareCreateResponse | API Response | DTO(응답 객체) | shareCode, shareUrl, expiresAt |
| SharedTimetableResponse | API Response | DTO(응답 객체) | timetable, sections[], metrics |
| SharedTimetableCopyRequest | API Request | DTO(요청 객체) | name? |
| SharedTimetableCopyResponse | API Response | DTO(응답 객체) | 복사된 timetable |
| OptimizationCreateRequest | API Request | DTO(요청 객체) | semester, datasetVersion, requiredCourseCodes[], candidateCourseCodes[], excludedCourseCodes[], lockedSectionIds[], professorConstraints[], minCredits, maxCredits, targetCredits, preferredDaysOff[], excludedDays[], avoidBefore?, avoidAfter?, minGapMinutes?, maxGapMinutes?, minLunchMinutes?, maxDailyMinutes?, candidateCount |
| OptimizationCreateResponse | API Response | DTO(응답 객체) | jobId, status, createdAt |
| OptimizationResultResponse | API Response | DTO(응답 객체) | status, candidates[], relaxationSuggestions[], error? |
| OptimizationCancelResponse | API Response | DTO(응답 객체) | jobId, status=CANCELLED |
| CandidateCompareRequest | API Request | DTO(요청 객체) | currentSectionIds[], candidateSectionIds[][] |
| CandidateCompareResponse | API Response | DTO(응답 객체) | 후보별 metrics, added[], removed[], swapped[], conflicts[] |
| CompletedCourseListResponse | API Response | DTO(응답 객체) | completedCourses[], creditSummary |
| CompletedCourseCreateRequest | API Request | DTO(요청 객체) | courseCode?, courseName, credits, category, area?, semester?, status |
| CompletedCourseCreateResponse | API Response | DTO(응답 객체) | 생성된 completedCourse |
| CompletedCourseUpdateRequest | API Request | DTO(요청 객체) | courseName?, credits?, category?, area?, semester?, status? |
| CompletedCourseUpdateResponse | API Response | DTO(응답 객체) | 변경된 completedCourse |
| CompletedCourseDeleteResponse | API Response | DTO(응답 객체) | message |
| TimetableCourseImportRequest | API Request | DTO(요청 객체) | timetableId, status=IN_PROGRESS |
| TimetableCourseImportResponse | API Response | DTO(응답 객체) | importedCourses[], skippedCourses[] |
| CompletedCreditSummaryResponse | API Response | DTO(응답 객체) | totalCredits, majorCredits, liberalCredits, areaCredits |
| OcrJobCreateRequest | API Request | DTO(요청 객체) | Multipart: image, documentType=TIMETABLE 또는 TRANSCRIPT |
| OcrJobCreateResponse | API Response | DTO(응답 객체) | jobId, status, uploadedAt |
| OcrJobResultResponse | API Response | DTO(응답 객체) | status, recognizedCourses[], warnings[], originalDeleted |
| OcrResultConfirmRequest | API Request | DTO(요청 객체) | courses[] |
| OcrResultConfirmResponse | API Response | DTO(응답 객체) | savedCourses[], skippedCourses[] |
| OcrJobDeleteResponse | API Response | DTO(응답 객체) | message, deletedAt |
| RequirementRuleListResponse | API Response | DTO(응답 객체) | rules[], sources[], manualReviewItems[] |
| RequirementEvaluationRequest | API Request | DTO(요청 객체) | admissionYear, departmentId, studentType, programPath, completedCourses[]? |
| RequirementEvaluationResponse | API Response | DTO(응답 객체) | creditStatus, areaStatus[], requiredCourseStatus[], missingRequirements[], manualReviewItems[] |
| RequirementRecommendationResponse | API Response | DTO(응답 객체) | missingRequirements[], recommendedCourses[] |
| RequirementSourceResponse | API Response | DTO(응답 객체) | sourceId, title, url, effectiveDate, verifiedAt |
| HealthLiveResponse | API Response | DTO(응답 객체) | status, version |
| HealthReadyResponse | API Response | DTO(응답 객체) | status, database, catalog, optimizer |
