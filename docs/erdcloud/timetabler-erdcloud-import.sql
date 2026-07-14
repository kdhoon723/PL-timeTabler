-- TimeTabler production ERD
-- ERDCloud의 'DDL 가져오기'에서 PostgreSQL로 선택해 사용합니다.
-- ERD 표시 호환성을 위해 PK, FK, 타입, NULL 여부, 기본값과 컬럼 설명만 포함합니다.
-- UNIQUE, CHECK, INDEX, 삭제 정책은 실제 마이그레이션에서 별도로 적용해야 합니다.

CREATE TABLE departments (
    department_id BIGSERIAL PRIMARY KEY,
    department_code VARCHAR(30) NOT NULL,
    department_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE users (
    user_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    department_id BIGINT NOT NULL,
    school_email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    student_number VARCHAR(30) NOT NULL,
    current_grade SMALLINT,
    admission_year SMALLINT,
    entry_type VARCHAR(20),
    student_type VARCHAR(20),
    role VARCHAR(20) DEFAULT 'USER' NOT NULL,
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_users_department_id FOREIGN KEY (department_id) REFERENCES departments (department_id)
);

CREATE TABLE user_oauth_accounts (
    oauth_account_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    provider VARCHAR(30) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_user_oauth_accounts_user_id FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE auth_sessions (
    session_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_auth_sessions_user_id FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE user_consents (
    consent_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    document_version VARCHAR(30) NOT NULL,
    is_agreed BOOLEAN NOT NULL,
    agreed_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT fk_user_consents_user_id FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE semesters (
    semester_id BIGSERIAL PRIMARY KEY,
    year SMALLINT NOT NULL,
    term VARCHAR(20) NOT NULL,
    catalog_version VARCHAR(64),
    is_active BOOLEAN DEFAULT true NOT NULL,
    starts_at DATE,
    ends_at DATE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE course_categories (
    category_id BIGSERIAL PRIMARY KEY,
    category_code VARCHAR(30) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL
);

CREATE TABLE curriculum_areas (
    curriculum_area_id BIGSERIAL PRIMARY KEY,
    area_code VARCHAR(30) NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL
);

CREATE TABLE courses (
    course_id BIGSERIAL PRIMARY KEY,
    department_id BIGINT,
    category_id BIGINT,
    curriculum_area_id BIGINT,
    course_code VARCHAR(30) NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    recommended_grade SMALLINT,
    credit NUMERIC(3,1) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_courses_department_id FOREIGN KEY (department_id) REFERENCES departments (department_id),
    CONSTRAINT fk_courses_category_id FOREIGN KEY (category_id) REFERENCES course_categories (category_id),
    CONSTRAINT fk_courses_curriculum_area_id FOREIGN KEY (curriculum_area_id) REFERENCES curriculum_areas (curriculum_area_id)
);

CREATE TABLE course_sections (
    section_id BIGSERIAL PRIMARY KEY,
    semester_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    section_code VARCHAR(20) NOT NULL,
    professor VARCHAR(100),
    capacity INTEGER,
    enrollment_count INTEGER DEFAULT 0 NOT NULL,
    section_group VARCHAR(50),
    status VARCHAR(20) DEFAULT 'OPEN' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_course_sections_semester_id FOREIGN KEY (semester_id) REFERENCES semesters (semester_id),
    CONSTRAINT fk_course_sections_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id)
);

CREATE TABLE course_section_targets (
    section_target_id BIGSERIAL PRIMARY KEY,
    section_id BIGINT NOT NULL,
    department_id BIGINT NOT NULL,
    target_grade SMALLINT,
    description VARCHAR(200),
    CONSTRAINT fk_course_section_targets_section_id FOREIGN KEY (section_id) REFERENCES course_sections (section_id),
    CONSTRAINT fk_course_section_targets_department_id FOREIGN KEY (department_id) REFERENCES departments (department_id)
);

CREATE TABLE course_schedules (
    schedule_id BIGSERIAL PRIMARY KEY,
    section_id BIGINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    classroom VARCHAR(100),
    CONSTRAINT fk_course_schedules_section_id FOREIGN KEY (section_id) REFERENCES course_sections (section_id)
);

CREATE TABLE timetable_generation_jobs (
    job_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    semester_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    request_snapshot JSONB NOT NULL,
    requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    CONSTRAINT fk_timetable_generation_jobs_user_id FOREIGN KEY (user_id) REFERENCES users (user_id),
    CONSTRAINT fk_timetable_generation_jobs_semester_id FOREIGN KEY (semester_id) REFERENCES semesters (semester_id)
);

CREATE TABLE timetables (
    timetable_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    semester_id BIGINT NOT NULL,
    generation_job_id UUID,
    title VARCHAR(100) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    variant_number INTEGER,
    status VARCHAR(20) DEFAULT 'DRAFT' NOT NULL,
    is_favorite BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_timetables_user_id FOREIGN KEY (user_id) REFERENCES users (user_id),
    CONSTRAINT fk_timetables_semester_id FOREIGN KEY (semester_id) REFERENCES semesters (semester_id),
    CONSTRAINT fk_timetables_generation_job_id FOREIGN KEY (generation_job_id) REFERENCES timetable_generation_jobs (job_id)
);

CREATE TABLE timetable_items (
    timetable_item_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timetable_id UUID NOT NULL,
    section_id BIGINT NOT NULL,
    role VARCHAR(20),
    section_locked BOOLEAN DEFAULT false NOT NULL,
    professor_locked BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_timetable_items_timetable_id FOREIGN KEY (timetable_id) REFERENCES timetables (timetable_id),
    CONSTRAINT fk_timetable_items_section_id FOREIGN KEY (section_id) REFERENCES course_sections (section_id)
);

CREATE TABLE timetable_preferences (
    preference_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timetable_id UUID NOT NULL,
    minimum_credit NUMERIC(3,1),
    maximum_credit NUMERIC(3,1),
    minimum_gap_minutes SMALLINT,
    maximum_gap_minutes SMALLINT,
    earliest_start_time TIME,
    latest_end_time TIME,
    lunch_start_time TIME,
    lunch_end_time TIME,
    compact_schedule BOOLEAN DEFAULT false NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_timetable_preferences_timetable_id FOREIGN KEY (timetable_id) REFERENCES timetables (timetable_id)
);

CREATE TABLE timetable_excluded_days (
    excluded_day_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    preference_id UUID NOT NULL,
    day_of_week SMALLINT NOT NULL,
    CONSTRAINT fk_timetable_excluded_days_preference_id FOREIGN KEY (preference_id) REFERENCES timetable_preferences (preference_id)
);

CREATE TABLE timetable_constraints (
    constraint_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timetable_id UUID NOT NULL,
    course_id BIGINT,
    section_id BIGINT,
    constraint_type VARCHAR(30) NOT NULL,
    professor_name VARCHAR(100),
    priority SMALLINT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_timetable_constraints_timetable_id FOREIGN KEY (timetable_id) REFERENCES timetables (timetable_id),
    CONSTRAINT fk_timetable_constraints_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id),
    CONSTRAINT fk_timetable_constraints_section_id FOREIGN KEY (section_id) REFERENCES course_sections (section_id)
);

CREATE TABLE favorite_courses (
    favorite_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    course_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_favorite_courses_user_id FOREIGN KEY (user_id) REFERENCES users (user_id),
    CONSTRAINT fk_favorite_courses_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id)
);

CREATE TABLE user_completed_courses (
    completed_course_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    course_id BIGINT,
    semester_id BIGINT,
    curriculum_area_id BIGINT,
    course_name_snapshot VARCHAR(200) NOT NULL,
    course_code_snapshot VARCHAR(30),
    credit NUMERIC(3,1) NOT NULL,
    grade_result VARCHAR(10),
    input_source VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_user_completed_courses_user_id FOREIGN KEY (user_id) REFERENCES users (user_id),
    CONSTRAINT fk_user_completed_courses_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id),
    CONSTRAINT fk_user_completed_courses_semester_id FOREIGN KEY (semester_id) REFERENCES semesters (semester_id),
    CONSTRAINT fk_user_completed_courses_curriculum_area_id FOREIGN KEY (curriculum_area_id) REFERENCES curriculum_areas (curriculum_area_id)
);

CREATE TABLE ocr_import_jobs (
    ocr_job_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    storage_object_key VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL,
    raw_result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMPTZ,
    CONSTRAINT fk_ocr_import_jobs_user_id FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE ocr_import_items (
    ocr_item_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ocr_job_id UUID NOT NULL,
    course_id BIGINT,
    detected_course_name VARCHAR(200) NOT NULL,
    detected_course_code VARCHAR(30),
    detected_credit NUMERIC(3,1),
    confidence NUMERIC(5,4),
    is_confirmed BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_ocr_import_items_ocr_job_id FOREIGN KEY (ocr_job_id) REFERENCES ocr_import_jobs (ocr_job_id),
    CONSTRAINT fk_ocr_import_items_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id)
);

CREATE TABLE course_metrics (
    course_metric_id BIGSERIAL PRIMARY KEY,
    course_id BIGINT NOT NULL,
    timetable_add_count INTEGER DEFAULT 0 NOT NULL,
    favorite_count INTEGER DEFAULT 0 NOT NULL,
    view_count INTEGER DEFAULT 0 NOT NULL,
    popularity_score NUMERIC(12,4) DEFAULT 0 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_course_metrics_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id)
);

CREATE TABLE curriculum_rule_sets (
    rule_set_id BIGSERIAL PRIMARY KEY,
    department_id BIGINT NOT NULL,
    admission_year_from SMALLINT NOT NULL,
    admission_year_to SMALLINT NOT NULL,
    entry_type VARCHAR(20),
    student_type VARCHAR(20),
    rule_set_name VARCHAR(200) NOT NULL,
    version VARCHAR(30) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    effective_from DATE,
    effective_to DATE,
    CONSTRAINT fk_curriculum_rule_sets_department_id FOREIGN KEY (department_id) REFERENCES departments (department_id)
);

CREATE TABLE graduation_requirements (
    requirement_id BIGSERIAL PRIMARY KEY,
    rule_set_id BIGINT NOT NULL,
    category_id BIGINT,
    curriculum_area_id BIGINT,
    requirement_type VARCHAR(30) NOT NULL,
    required_credit NUMERIC(4,1),
    required_course_count INTEGER,
    description TEXT NOT NULL,
    display_order INTEGER DEFAULT 0 NOT NULL,
    CONSTRAINT fk_graduation_requirements_rule_set_id FOREIGN KEY (rule_set_id) REFERENCES curriculum_rule_sets (rule_set_id),
    CONSTRAINT fk_graduation_requirements_category_id FOREIGN KEY (category_id) REFERENCES course_categories (category_id),
    CONSTRAINT fk_graduation_requirements_curriculum_area_id FOREIGN KEY (curriculum_area_id) REFERENCES curriculum_areas (curriculum_area_id)
);

CREATE TABLE requirement_courses (
    requirement_course_id BIGSERIAL PRIMARY KEY,
    requirement_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL,
    is_mandatory BOOLEAN DEFAULT true NOT NULL,
    CONSTRAINT fk_requirement_courses_requirement_id FOREIGN KEY (requirement_id) REFERENCES graduation_requirements (requirement_id),
    CONSTRAINT fk_requirement_courses_course_id FOREIGN KEY (course_id) REFERENCES courses (course_id)
);

COMMENT ON COLUMN departments.department_id IS '학과 식별자';
COMMENT ON COLUMN departments.department_code IS '학과 코드; UNIQUE';
COMMENT ON COLUMN departments.department_name IS '학과명';
COMMENT ON COLUMN departments.is_active IS '사용 여부';
COMMENT ON COLUMN departments.created_at IS '생성 일시';
COMMENT ON COLUMN users.user_id IS '사용자 식별자';
COMMENT ON COLUMN users.department_id IS '소속 학과';
COMMENT ON COLUMN users.school_email IS '학교 이메일; UNIQUE';
COMMENT ON COLUMN users.name IS '사용자 이름';
COMMENT ON COLUMN users.student_number IS '학번; UNIQUE';
COMMENT ON COLUMN users.current_grade IS '현재 학년';
COMMENT ON COLUMN users.admission_year IS '입학 연도';
COMMENT ON COLUMN users.entry_type IS '입학 유형: FRESHMAN/TRANSFER';
COMMENT ON COLUMN users.student_type IS '학생 구분';
COMMENT ON COLUMN users.role IS '권한: USER/ADMIN';
COMMENT ON COLUMN users.email_verified_at IS '이메일 인증 일시';
COMMENT ON COLUMN users.created_at IS '가입 일시';
COMMENT ON COLUMN users.updated_at IS '수정 일시';
COMMENT ON COLUMN users.deleted_at IS '탈퇴 일시';
COMMENT ON COLUMN user_oauth_accounts.oauth_account_id IS '소셜 계정 식별자';
COMMENT ON COLUMN user_oauth_accounts.user_id IS '사용자';
COMMENT ON COLUMN user_oauth_accounts.provider IS '로그인 제공자';
COMMENT ON COLUMN user_oauth_accounts.provider_user_id IS '제공자 사용자 ID; provider와 복합 UNIQUE';
COMMENT ON COLUMN user_oauth_accounts.provider_email IS '제공자 이메일';
COMMENT ON COLUMN user_oauth_accounts.created_at IS '연결 일시';
COMMENT ON COLUMN auth_sessions.session_id IS '세션 식별자';
COMMENT ON COLUMN auth_sessions.user_id IS '사용자';
COMMENT ON COLUMN auth_sessions.refresh_token_hash IS '리프레시 토큰 해시';
COMMENT ON COLUMN auth_sessions.expires_at IS '만료 일시';
COMMENT ON COLUMN auth_sessions.revoked_at IS '폐기 일시';
COMMENT ON COLUMN auth_sessions.last_used_at IS '최근 사용 일시';
COMMENT ON COLUMN auth_sessions.created_at IS '생성 일시';
COMMENT ON COLUMN user_consents.consent_id IS '동의 기록 식별자';
COMMENT ON COLUMN user_consents.user_id IS '사용자';
COMMENT ON COLUMN user_consents.consent_type IS '동의서 종류';
COMMENT ON COLUMN user_consents.document_version IS '동의서 버전';
COMMENT ON COLUMN user_consents.is_agreed IS '동의 여부';
COMMENT ON COLUMN user_consents.agreed_at IS '동의 일시';
COMMENT ON COLUMN user_consents.revoked_at IS '철회 일시';
COMMENT ON COLUMN semesters.semester_id IS '학기 식별자';
COMMENT ON COLUMN semesters.year IS '개설 연도';
COMMENT ON COLUMN semesters.term IS '학기; year와 복합 UNIQUE';
COMMENT ON COLUMN semesters.catalog_version IS '강의 데이터 버전';
COMMENT ON COLUMN semesters.is_active IS '현재 학기 여부';
COMMENT ON COLUMN semesters.starts_at IS '학기 시작일';
COMMENT ON COLUMN semesters.ends_at IS '학기 종료일';
COMMENT ON COLUMN semesters.created_at IS '생성 일시';
COMMENT ON COLUMN course_categories.category_id IS '과목 분류 식별자';
COMMENT ON COLUMN course_categories.category_code IS '분류 코드; UNIQUE';
COMMENT ON COLUMN course_categories.category_name IS '전공/교양/일반선택 등';
COMMENT ON COLUMN course_categories.is_active IS '사용 여부';
COMMENT ON COLUMN curriculum_areas.curriculum_area_id IS '교육영역 식별자';
COMMENT ON COLUMN curriculum_areas.area_code IS '영역 코드; UNIQUE';
COMMENT ON COLUMN curriculum_areas.area_name IS '5영역 등 교육영역';
COMMENT ON COLUMN curriculum_areas.description IS '영역 설명';
COMMENT ON COLUMN curriculum_areas.is_active IS '사용 여부';
COMMENT ON COLUMN courses.course_id IS '과목 식별자';
COMMENT ON COLUMN courses.department_id IS '주관 학과';
COMMENT ON COLUMN courses.category_id IS '과목 분류';
COMMENT ON COLUMN courses.curriculum_area_id IS '교육영역';
COMMENT ON COLUMN courses.course_code IS '과목 코드; UNIQUE';
COMMENT ON COLUMN courses.course_name IS '과목명';
COMMENT ON COLUMN courses.recommended_grade IS '권장 학년';
COMMENT ON COLUMN courses.credit IS '학점';
COMMENT ON COLUMN courses.description IS '과목 설명';
COMMENT ON COLUMN courses.created_at IS '생성 일시';
COMMENT ON COLUMN courses.updated_at IS '수정 일시';
COMMENT ON COLUMN course_sections.section_id IS '개설 분반 식별자';
COMMENT ON COLUMN course_sections.semester_id IS '개설 학기';
COMMENT ON COLUMN course_sections.course_id IS '과목';
COMMENT ON COLUMN course_sections.section_code IS '분반 코드; 학기/과목과 복합 UNIQUE';
COMMENT ON COLUMN course_sections.professor IS '담당 교수';
COMMENT ON COLUMN course_sections.capacity IS '수강 정원';
COMMENT ON COLUMN course_sections.enrollment_count IS '현재 신청 인원';
COMMENT ON COLUMN course_sections.section_group IS '전공 분반 구분';
COMMENT ON COLUMN course_sections.status IS 'OPEN/CLOSED/CANCELLED';
COMMENT ON COLUMN course_sections.created_at IS '생성 일시';
COMMENT ON COLUMN course_sections.updated_at IS '수정 일시';
COMMENT ON COLUMN course_section_targets.section_target_id IS '분반 대상 식별자';
COMMENT ON COLUMN course_section_targets.section_id IS '개설 분반';
COMMENT ON COLUMN course_section_targets.department_id IS '대상 학과';
COMMENT ON COLUMN course_section_targets.target_grade IS '대상 학년';
COMMENT ON COLUMN course_section_targets.description IS '분반 대상 설명';
COMMENT ON COLUMN course_schedules.schedule_id IS '수업시간 식별자';
COMMENT ON COLUMN course_schedules.section_id IS '개설 분반';
COMMENT ON COLUMN course_schedules.day_of_week IS '요일 1~7';
COMMENT ON COLUMN course_schedules.start_time IS '시작 시간';
COMMENT ON COLUMN course_schedules.end_time IS '종료 시간; 시작보다 이후';
COMMENT ON COLUMN course_schedules.classroom IS '강의실';
COMMENT ON COLUMN timetable_generation_jobs.job_id IS '자동 편성 작업 식별자';
COMMENT ON COLUMN timetable_generation_jobs.user_id IS '요청 사용자';
COMMENT ON COLUMN timetable_generation_jobs.semester_id IS '대상 학기';
COMMENT ON COLUMN timetable_generation_jobs.status IS 'QUEUED/RUNNING/SUCCEEDED/FAILED';
COMMENT ON COLUMN timetable_generation_jobs.request_snapshot IS '편성 조건 스냅샷';
COMMENT ON COLUMN timetable_generation_jobs.requested_at IS '요청 일시';
COMMENT ON COLUMN timetable_generation_jobs.started_at IS '시작 일시';
COMMENT ON COLUMN timetable_generation_jobs.completed_at IS '완료 일시';
COMMENT ON COLUMN timetable_generation_jobs.error_message IS '실패 내용';
COMMENT ON COLUMN timetables.timetable_id IS '시간표 식별자';
COMMENT ON COLUMN timetables.user_id IS '소유 사용자';
COMMENT ON COLUMN timetables.semester_id IS '학기';
COMMENT ON COLUMN timetables.generation_job_id IS '생성 작업';
COMMENT ON COLUMN timetables.title IS '시간표 제목';
COMMENT ON COLUMN timetables.source_type IS 'MANUAL/AUTO_GENERATED/COPIED';
COMMENT ON COLUMN timetables.variant_number IS '자동 생성 후보 번호';
COMMENT ON COLUMN timetables.status IS 'DRAFT/SAVED/ARCHIVED';
COMMENT ON COLUMN timetables.is_favorite IS '즐겨찾기 여부';
COMMENT ON COLUMN timetables.created_at IS '생성 일시';
COMMENT ON COLUMN timetables.updated_at IS '수정 일시';
COMMENT ON COLUMN timetable_items.timetable_item_id IS '시간표 항목 식별자';
COMMENT ON COLUMN timetable_items.timetable_id IS '시간표';
COMMENT ON COLUMN timetable_items.section_id IS '선택 분반; 시간표와 복합 UNIQUE';
COMMENT ON COLUMN timetable_items.role IS 'MUST/WANT/BACKUP/EXCLUDE';
COMMENT ON COLUMN timetable_items.section_locked IS '분반 고정 여부';
COMMENT ON COLUMN timetable_items.professor_locked IS '교수 고정 여부';
COMMENT ON COLUMN timetable_items.created_at IS '추가 일시';
COMMENT ON COLUMN timetable_preferences.preference_id IS '편성 선호조건 식별자';
COMMENT ON COLUMN timetable_preferences.timetable_id IS '기준 시간표; UNIQUE';
COMMENT ON COLUMN timetable_preferences.minimum_credit IS '최소 학점';
COMMENT ON COLUMN timetable_preferences.maximum_credit IS '최대 학점';
COMMENT ON COLUMN timetable_preferences.minimum_gap_minutes IS '최소 공강 시간';
COMMENT ON COLUMN timetable_preferences.maximum_gap_minutes IS '최대 공강 시간';
COMMENT ON COLUMN timetable_preferences.earliest_start_time IS '가장 이른 시작';
COMMENT ON COLUMN timetable_preferences.latest_end_time IS '가장 늦은 종료';
COMMENT ON COLUMN timetable_preferences.lunch_start_time IS '점심 시작';
COMMENT ON COLUMN timetable_preferences.lunch_end_time IS '점심 종료';
COMMENT ON COLUMN timetable_preferences.compact_schedule IS '시간표 압축 선호';
COMMENT ON COLUMN timetable_preferences.updated_at IS '수정 일시';
COMMENT ON COLUMN timetable_excluded_days.excluded_day_id IS '제외 요일 식별자';
COMMENT ON COLUMN timetable_excluded_days.preference_id IS '편성 선호조건';
COMMENT ON COLUMN timetable_excluded_days.day_of_week IS '제외 요일 1~7; preference와 복합 UNIQUE';
COMMENT ON COLUMN timetable_constraints.constraint_id IS '편성 제약 식별자';
COMMENT ON COLUMN timetable_constraints.timetable_id IS '기준 시간표';
COMMENT ON COLUMN timetable_constraints.course_id IS '대상 과목';
COMMENT ON COLUMN timetable_constraints.section_id IS '대상 분반';
COMMENT ON COLUMN timetable_constraints.constraint_type IS 'REQUIRED/LOCKED/EXCLUDED/PREFERRED';
COMMENT ON COLUMN timetable_constraints.professor_name IS '대상 교수';
COMMENT ON COLUMN timetable_constraints.priority IS '선호 우선순위';
COMMENT ON COLUMN timetable_constraints.created_at IS '생성 일시';
COMMENT ON COLUMN favorite_courses.favorite_id IS '과목 즐겨찾기 식별자';
COMMENT ON COLUMN favorite_courses.user_id IS '사용자';
COMMENT ON COLUMN favorite_courses.course_id IS '과목; 사용자와 복합 UNIQUE';
COMMENT ON COLUMN favorite_courses.created_at IS '즐겨찾기 일시';
COMMENT ON COLUMN user_completed_courses.completed_course_id IS '이수과목 식별자';
COMMENT ON COLUMN user_completed_courses.user_id IS '사용자';
COMMENT ON COLUMN user_completed_courses.course_id IS '연결 과목';
COMMENT ON COLUMN user_completed_courses.semester_id IS '이수 학기';
COMMENT ON COLUMN user_completed_courses.curriculum_area_id IS '인정 교육영역';
COMMENT ON COLUMN user_completed_courses.course_name_snapshot IS '입력 당시 과목명';
COMMENT ON COLUMN user_completed_courses.course_code_snapshot IS '입력 당시 과목코드';
COMMENT ON COLUMN user_completed_courses.credit IS '인정 학점';
COMMENT ON COLUMN user_completed_courses.grade_result IS '성적';
COMMENT ON COLUMN user_completed_courses.input_source IS 'MANUAL/OCR/TIMETABLE/ADMIN';
COMMENT ON COLUMN user_completed_courses.created_at IS '등록 일시';
COMMENT ON COLUMN ocr_import_jobs.ocr_job_id IS 'OCR 작업 식별자';
COMMENT ON COLUMN ocr_import_jobs.user_id IS '요청 사용자';
COMMENT ON COLUMN ocr_import_jobs.storage_object_key IS '성적표 이미지 저장 경로';
COMMENT ON COLUMN ocr_import_jobs.status IS 'QUEUED/RUNNING/SUCCEEDED/FAILED';
COMMENT ON COLUMN ocr_import_jobs.raw_result IS 'OCR 원본 결과';
COMMENT ON COLUMN ocr_import_jobs.error_message IS '실패 내용';
COMMENT ON COLUMN ocr_import_jobs.created_at IS '요청 일시';
COMMENT ON COLUMN ocr_import_jobs.completed_at IS '완료 일시';
COMMENT ON COLUMN ocr_import_items.ocr_item_id IS 'OCR 인식 항목 식별자';
COMMENT ON COLUMN ocr_import_items.ocr_job_id IS 'OCR 작업';
COMMENT ON COLUMN ocr_import_items.course_id IS '매칭 과목';
COMMENT ON COLUMN ocr_import_items.detected_course_name IS '인식 과목명';
COMMENT ON COLUMN ocr_import_items.detected_course_code IS '인식 과목코드';
COMMENT ON COLUMN ocr_import_items.detected_credit IS '인식 학점';
COMMENT ON COLUMN ocr_import_items.confidence IS '인식 신뢰도';
COMMENT ON COLUMN ocr_import_items.is_confirmed IS '사용자 확인 여부';
COMMENT ON COLUMN ocr_import_items.created_at IS '생성 일시';
COMMENT ON COLUMN course_metrics.course_metric_id IS '과목 집계 식별자';
COMMENT ON COLUMN course_metrics.course_id IS '과목; UNIQUE';
COMMENT ON COLUMN course_metrics.timetable_add_count IS '시간표 추가 횟수';
COMMENT ON COLUMN course_metrics.favorite_count IS '즐겨찾기 수';
COMMENT ON COLUMN course_metrics.view_count IS '조회 수';
COMMENT ON COLUMN course_metrics.popularity_score IS '인기 점수';
COMMENT ON COLUMN course_metrics.updated_at IS '집계 일시';
COMMENT ON COLUMN curriculum_rule_sets.rule_set_id IS '교육과정 규칙 식별자';
COMMENT ON COLUMN curriculum_rule_sets.department_id IS '적용 학과';
COMMENT ON COLUMN curriculum_rule_sets.admission_year_from IS '적용 입학연도 시작';
COMMENT ON COLUMN curriculum_rule_sets.admission_year_to IS '적용 입학연도 종료';
COMMENT ON COLUMN curriculum_rule_sets.entry_type IS '입학 유형';
COMMENT ON COLUMN curriculum_rule_sets.student_type IS '학생 구분';
COMMENT ON COLUMN curriculum_rule_sets.rule_set_name IS '교육과정명';
COMMENT ON COLUMN curriculum_rule_sets.version IS '규칙 버전';
COMMENT ON COLUMN curriculum_rule_sets.is_active IS '사용 여부';
COMMENT ON COLUMN curriculum_rule_sets.effective_from IS '적용 시작일';
COMMENT ON COLUMN curriculum_rule_sets.effective_to IS '적용 종료일';
COMMENT ON COLUMN graduation_requirements.requirement_id IS '졸업요건 식별자';
COMMENT ON COLUMN graduation_requirements.rule_set_id IS '교육과정 규칙';
COMMENT ON COLUMN graduation_requirements.category_id IS '과목 분류 조건';
COMMENT ON COLUMN graduation_requirements.curriculum_area_id IS '교육영역 조건';
COMMENT ON COLUMN graduation_requirements.requirement_type IS 'TOTAL_CREDIT/CATEGORY/AREA/COURSE';
COMMENT ON COLUMN graduation_requirements.required_credit IS '필요 학점';
COMMENT ON COLUMN graduation_requirements.required_course_count IS '필요 과목 수';
COMMENT ON COLUMN graduation_requirements.description IS '요건 설명';
COMMENT ON COLUMN graduation_requirements.display_order IS '표시 순서';
COMMENT ON COLUMN requirement_courses.requirement_course_id IS '필수과목 연결 식별자';
COMMENT ON COLUMN requirement_courses.requirement_id IS '졸업요건';
COMMENT ON COLUMN requirement_courses.course_id IS '대상 과목; 요건과 복합 UNIQUE';
COMMENT ON COLUMN requirement_courses.is_mandatory IS '필수 여부';
