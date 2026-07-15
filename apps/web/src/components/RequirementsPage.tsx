import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createCompletedCourse,
  deleteCompletedCourse,
  loadCommonRules,
  loadCompletedCourses,
  loadDepartmentSources,
  updateCompletedCourse,
} from '../api/client'
import { academicUnitOverrideStatus, applicableRules, completedCourseMatches, type StudentType } from '../domain/requirements'
import type { AcademicProfile, CommonRules, CompletedCourse, CompletedCourseStatus, DepartmentSource, MajorRequiredCourses, Section } from '../types'
import { CheckIcon, WarningIcon } from './Icons'

interface Props { catalog: Section[]; profile: AcademicProfile | null; majorRequired?: MajorRequiredCourses | null; authenticated?: boolean; onBack: () => void; onAddCourse: (section: Section) => void }

const SOURCE_URLS: Record<string, string> = {
  'regulations-2-1-01': 'https://www.daejin.ac.kr/regltn/daejin/2/631/download.do',
  'regulations-2-1-02': 'https://www.daejin.ac.kr/regltn/daejin/2/612/download.do',
  'curriculum-guide-2026': 'https://www.daejin.ac.kr/bbs/daejin/188/458095/artclView.do',
}

const KIND_LABEL: Record<string, string> = {
  TOTAL_CREDITS: '졸업 총학점', REGISTERED_SEMESTERS: '등록 학기', GRADUATION_GPA: '졸업 평점', ADVISOR_COUNSELING: '지도교수 상담', LIBERAL_TOTAL: '교양 이수학점', REQUIRED_COURSE_GROUP: '교양 필수과목', PRIMARY_MAJOR_CREDITS: '주전공 이수학점', MAJOR_CREDIT_PAIR: '전공별 이수학점', ACADEMIC_UNIT_OVERRIDE: '학과별 예외 기준',
}
const LIBERAL_AREAS = ['제1영역:인간과소통', '제2영역:사회와경제', '제3영역:과학과기술', '제4영역:예술과문화', '제5영역:융합과혁신', '제6영역:AI·디지털리터러시']
const COMPLETION_CATEGORIES = ['전공필수', '전공선택', '교양필수', '교양선택', '교직', '일반선택']
const COMPLETION_TERMS = [{ code: '1', label: '1학기' }, { code: '2', label: '2학기' }, { code: '11', label: '여름계절' }, { code: '22', label: '겨울계절' }]
const CURRENT_YEAR = new Date().getFullYear()

export function RequirementsPage({ catalog, profile, majorRequired = null, authenticated = false, onBack, onAddCourse }: Props) {
  const [rules, setRules] = useState<CommonRules | null>(null)
  const [departments, setDepartments] = useState<DepartmentSource[]>([])
  const [error, setError] = useState(false)
  const [year, setYear] = useState(profile?.academicBasis?.admissionYear ?? 2026)
  const [department, setDepartment] = useState(profile?.department ?? '대순종학과')
  const [path, setPath] = useState('ADVANCED_MAJOR')
  const [studentType, setStudentType] = useState<StudentType>(profile?.academicBasis?.studentType === 'DOMESTIC' ? 'DOMESTIC' : 'OTHER')
  const [completedCredits, setCompletedCredits] = useState(0)
  const [liberalCredits, setLiberalCredits] = useState(0)
  const [majorCredits, setMajorCredits] = useState(0)
  const [completedNames, setCompletedNames] = useState('')
  const [areaCredits, setAreaCredits] = useState<Record<string, number>>({})
  const [completedCourses, setCompletedCourses] = useState<CompletedCourse[]>([])
  const [completedLoading, setCompletedLoading] = useState(false)
  const [completedPending, setCompletedPending] = useState(false)
  const [completedError, setCompletedError] = useState<string | null>(null)
  const [completedNotice, setCompletedNotice] = useState<string | null>(null)
  const [editingCourseId, setEditingCourseId] = useState<string | null>(null)
  const [courseCode, setCourseCode] = useState('')
  const [courseName, setCourseName] = useState('')
  const [courseYear, setCourseYear] = useState(profile?.academicBasis?.admissionYear ?? CURRENT_YEAR)
  const [courseTerm, setCourseTerm] = useState('1')
  const [courseCredits, setCourseCredits] = useState(3)
  const [courseCategory, setCourseCategory] = useState('전공선택')
  const [courseArea, setCourseArea] = useState('')
  const [courseStatus, setCourseStatus] = useState<CompletedCourseStatus>('COMPLETED')
  useEffect(() => {
    Promise.all([loadCommonRules(), loadDepartmentSources()])
      .then(([loadedRules, loadedDepartments]) => {
        setRules(loadedRules)
        setDepartments(loadedDepartments.departments)
        if (!profile && loadedDepartments.departments[0]) setDepartment(loadedDepartments.departments[0].academicUnit)
      })
      .catch(() => setError(true))
  }, [profile])
  const refreshCompletedCourses = useCallback(async () => {
    setCompletedLoading(true)
    try {
      const result = await loadCompletedCourses()
      setCompletedCourses(result.completedCourses)
      setCompletedCredits(result.creditSummary.totalCredits)
      setLiberalCredits(result.creditSummary.liberalCredits)
      setMajorCredits(result.creditSummary.majorCredits)
      setAreaCredits(result.creditSummary.areaCredits)
      setCompletedError(null)
    } catch (caught) {
      setCompletedError(caught instanceof Error ? caught.message : '이전 수강 내역을 불러오지 못했습니다.')
      throw caught
    } finally {
      setCompletedLoading(false)
    }
  }, [])
  useEffect(() => {
    if (!authenticated) {
      setCompletedCourses([])
      return
    }
    refreshCompletedCourses().catch(() => { /* temporary manual inputs remain available */ })
  }, [authenticated, refreshCompletedCourses])

  const resetCourseForm = () => {
    setEditingCourseId(null)
    setCourseCode('')
    setCourseName('')
    setCourseYear(profile?.academicBasis?.admissionYear ?? CURRENT_YEAR)
    setCourseTerm('1')
    setCourseCredits(3)
    setCourseCategory('전공선택')
    setCourseArea('')
    setCourseStatus('COMPLETED')
  }
  const runCompletedMutation = async (action: () => Promise<void>, successMessage: string) => {
    setCompletedPending(true)
    setCompletedError(null)
    setCompletedNotice(null)
    try {
      await action()
      await refreshCompletedCourses()
      setCompletedNotice(successMessage)
    } catch (caught) {
      setCompletedError(caught instanceof Error ? caught.message : '이전 수강 내역을 저장하지 못했습니다.')
    } finally {
      setCompletedPending(false)
    }
  }
  const saveCompletedCourse = () => runCompletedMutation(async () => {
    const values = {
      courseCode: courseCode.trim() || null,
      courseName: courseName.trim(),
      credits: courseCredits,
      category: courseCategory,
      area: courseCategory === '교양선택' ? courseArea || null : null,
      semester: `${courseYear}-${courseTerm}`,
      status: courseStatus,
    }
    if (editingCourseId) await updateCompletedCourse(editingCourseId, values)
    else await createCompletedCourse(values)
    resetCourseForm()
  }, editingCourseId ? '이수과목을 수정했습니다.' : '이수과목을 추가했습니다.')
  const startEditingCourse = (item: CompletedCourse) => {
    const [savedYear, savedTerm] = item.semester?.split('-') ?? []
    setEditingCourseId(item.id)
    setCourseCode(item.courseCode ?? '')
    setCourseName(item.courseName)
    setCourseYear(Number(savedYear) || profile?.academicBasis?.admissionYear || CURRENT_YEAR)
    setCourseTerm(savedTerm && COMPLETION_TERMS.some((term) => term.code === savedTerm) ? savedTerm : '1')
    setCourseCredits(item.credits)
    setCourseCategory(item.category)
    setCourseArea(item.area ?? '')
    setCourseStatus(item.status)
  }
  const applicable = useMemo(() => applicableRules(rules?.rules ?? [], year, path, department, studentType), [department, path, rules, studentType, year])
  const names = [
    ...completedCourses.filter((item) => item.status === 'COMPLETED').map((item) => item.courseName),
    ...completedNames.split(/[\n,]/).map((value) => value.trim()).filter(Boolean),
  ]
  const requiredCourses = applicable.find((rule) => rule.kind === 'REQUIRED_COURSE_GROUP')?.courses ?? []
  const missingCourses = requiredCourses.filter((course) => !completedCourseMatches(names, course.name))
  const majorProgram = year === majorRequired?.cohortAdmissionYear ? majorRequired.programs.find((program) => program.academicUnit === department) : undefined
  const missingMajorRequired = majorProgram?.status === 'AVAILABLE' ? majorProgram.courses.filter((course) => !completedCourseMatches(names, course.name)) : []
  const recommendationNames = [...missingCourses.map((course) => course.name), ...missingMajorRequired.map((course) => course.name)]
  const recommendations = recommendationNames.flatMap((courseName) => {
    const normalized = courseName.replaceAll(' ', '').toLocaleLowerCase('ko')
    return catalog.filter((section) => section.name.replaceAll(' ', '').toLocaleLowerCase('ko').includes(normalized) || (normalized === 'lct' && section.name.toLocaleLowerCase('ko').startsWith('lct'))).slice(0, 2)
  })
  const departmentSource = departments.find((item) => item.academicUnit === department)

  return <main className="requirements-page">
    <header className="requirements-header"><button type="button" className="text-button" onClick={onBack}>← 시간표로</button><div><h1>예상 졸업요건 점검</h1><p>마이페이지의 이수내역과 직접 입력한 값을 기준으로 계산합니다.</p></div></header>
    {error && <div className="inline-error" role="alert">졸업요건 데이터를 불러오지 못했습니다.</div>}
    <section className="profile-panel" aria-labelledby="profile-title"><h2 id="profile-title">내 기준 선택</h2><div className="profile-grid">
      <label><span>입학연도</span><select value={year} onChange={(event) => setYear(Number(event.target.value))}>{Array.from({ length: 15 }, (_, index) => 2026 - index).map((value) => <option key={value}>{value}</option>)}</select></label>
      <label><span>학생 구분</span><select value={studentType} onChange={(event) => setStudentType(event.target.value as StudentType)}><option value="DOMESTIC">국내 학부생</option><option value="OTHER">외국인·별도 기준</option></select></label>
      <label><span>학과·전공</span><select value={department} onChange={(event) => setDepartment(event.target.value)}>{Array.from(new Set(departments.map((item) => item.college))).map((college) => <optgroup key={college} label={college}>{departments.filter((item) => item.college === college).map((item) => <option key={item.academicUnit}>{item.academicUnit}</option>)}</optgroup>)}</select></label>
      <label><span>전공 방식</span><select value={path} onChange={(event) => setPath(event.target.value)}><option value="ADVANCED_MAJOR">심화전공</option><option value="DOUBLE_MAJOR">복수전공</option><option value="MINOR">부전공</option><option value="MICRO_MAJOR">마이크로전공</option></select></label>
      <label><span>현재 총 이수학점</span><input type="number" min="0" max="200" value={completedCredits} onChange={(event) => setCompletedCredits(Number(event.target.value))}/></label>
      <label><span>교양 이수학점</span><input type="number" min="0" max="80" value={liberalCredits} onChange={(event) => setLiberalCredits(Number(event.target.value))}/></label>
      <label><span>주전공 이수학점</span><input type="number" min="0" max="150" value={majorCredits} onChange={(event) => setMajorCredits(Number(event.target.value))}/></label>
    </div>{studentType === 'OTHER' && <p className="source-note">국내학생 전용 교양·필수과목 규칙은 제외했습니다. 국제협력대학 또는 소속 학과의 별도 기준을 확인하세요.</p>}{authenticated && <p className="source-note">아래에 저장한 이수 완료 과목과 학점을 자동으로 반영합니다.</p>}<label className="completed-field"><span>{authenticated ? '추가로 점검에 반영할 과목명' : '이수한 필수과목'}</span><textarea rows={3} value={completedNames} onChange={(event) => setCompletedNames(event.target.value)} placeholder="과목명을 쉼표나 줄바꿈으로 입력"/><small>{authenticated ? '여기에 입력한 과목명은 현재 점검에만 임시 반영됩니다. 학점까지 저장하려면 아래 이수과목 내역에 추가하세요.' : '최종 졸업 판정은 학교 포털과 소속 학과에서 반드시 확인하세요.'}</small></label></section>
    {authenticated && <section className="completed-history" aria-labelledby="completed-history-title">
      <div className="section-heading"><div><h2 id="completed-history-title">이전 수강 내역</h2><p>학기·과목코드·학점·이수구분을 저장하면 졸업요건 계산에 바로 반영됩니다.</p></div><span>이수 완료 {completedCourses.filter((item) => item.status === 'COMPLETED').length}과목</span></div>
      {completedError && <div className="inline-error" role="alert">{completedError}</div>}
      {completedNotice && <p className="completion-notice" role="status">{completedNotice}</p>}
      <div className="completed-form requirements-completed-form">
        <label><span>과목코드</span><input value={courseCode} maxLength={40} onChange={(event) => setCourseCode(event.target.value)} placeholder="예: 012093" /></label>
        <label><span>과목명</span><input value={courseName} maxLength={240} onChange={(event) => setCourseName(event.target.value)} placeholder="포털에 표시된 과목명" /></label>
        <label><span>수강 학년도</span><select value={courseYear} onChange={(event) => setCourseYear(Number(event.target.value))}>{courseYear < 2000 || courseYear > CURRENT_YEAR ? <option>{courseYear}</option> : null}{Array.from({ length: CURRENT_YEAR - 1999 }, (_, index) => CURRENT_YEAR - index).map((value) => <option key={value}>{value}</option>)}</select></label>
        <label><span>학기</span><select value={courseTerm} onChange={(event) => setCourseTerm(event.target.value)}>{COMPLETION_TERMS.map((term) => <option value={term.code} key={term.code}>{term.label}</option>)}</select></label>
        <label><span>학점</span><input type="number" min="0.5" max="30" step="0.5" value={courseCredits} onChange={(event) => setCourseCredits(Number(event.target.value))} /></label>
        <label><span>이수구분</span><select value={courseCategory} onChange={(event) => { const value = event.target.value; setCourseCategory(value); if (value !== '교양선택') setCourseArea('') }}>{!COMPLETION_CATEGORIES.includes(courseCategory) && <option value={courseCategory}>{courseCategory}</option>}{COMPLETION_CATEGORIES.map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
        {courseCategory === '교양선택' && <label><span>교양 영역</span><select value={courseArea} onChange={(event) => setCourseArea(event.target.value)}><option value="">영역 미지정</option>{LIBERAL_AREAS.map((area) => <option key={area}>{area}</option>)}</select></label>}
        <label><span>상태</span><select value={courseStatus} onChange={(event) => setCourseStatus(event.target.value as CompletedCourseStatus)}><option value="COMPLETED">이수 완료</option><option value="IN_PROGRESS">수강 중</option></select></label>
      </div>
      <div className="form-actions">{editingCourseId && <button type="button" className="text-button" onClick={resetCourseForm}>수정 취소</button>}<button type="button" className="primary-button" disabled={completedPending || !courseName.trim() || !courseCategory || courseCredits <= 0} onClick={saveCompletedCourse}>{editingCourseId ? '이수과목 수정' : '이수과목 추가'}</button></div>
      {completedLoading ? <p className="source-note">이전 수강 내역을 불러오는 중입니다…</p> : completedCourses.length === 0 ? <p className="completed-empty">저장된 이수과목이 없습니다.</p> : <div className="saved-card-list completed-course-list">{completedCourses.map((item) => <article key={item.id}><div><strong>{item.courseName}</strong><small>{item.semester ?? '학기 미지정'} · {item.courseCode ? `${item.courseCode} · ` : ''}{item.credits}학점 · {item.category}{item.area ? ` · ${item.area}` : ''}</small></div><div className="card-actions"><span className={`status ${item.status === 'COMPLETED' ? 'success' : 'neutral'}`}>{item.status === 'COMPLETED' ? '이수 완료' : '수강 중'}</span><button type="button" onClick={() => startEditingCourse(item)}>수정</button><button type="button" className="danger-text" disabled={completedPending} onClick={() => runCompletedMutation(async () => { await deleteCompletedCourse(item.id); if (editingCourseId === item.id) resetCourseForm() }, '이수과목을 삭제했습니다.')}>삭제</button></div></article>)}</div>}
    </section>}
    {authenticated && <section className="rule-results" aria-labelledby="area-title"><div className="section-heading"><div><h2 id="area-title">교양 영역 이수 현황</h2><p>영역별 2학점 이상 이수를 기준으로 표시합니다.</p></div></div><div className="area-status-grid">{LIBERAL_AREAS.map((area) => { const credits = areaCredits[area] ?? 0; return <article key={area}><strong>{area}</strong><span className={`status ${credits >= 2 ? 'success' : 'warning'}`}>{credits}학점 · {credits >= 2 ? '충족' : '부족'}</span></article> })}</div></section>}
    <section className="rule-results" aria-labelledby="result-title"><div className="section-heading"><div><h2 id="result-title">점검 결과</h2><p>공식 자료로 확정할 수 없는 항목은 ‘확인 필요’로 표시합니다.</p></div><span>기준 {rules?.asOf ?? '불러오는 중'}</span></div>
      {!rules && !error && <p>요건을 불러오는 중입니다…</p>}
      <div className="rule-list">{applicable.map((rule) => {
        const overrideValues = rule.kind === 'ACADEMIC_UNIT_OVERRIDE' ? rule.values : undefined
        const overrideMajorMinimum = overrideValues ? (overrideValues.majorFoundation ?? 0) + (overrideValues.majorRequired ?? 0) + (overrideValues.majorElectiveMin ?? 0) : null
        const current = rule.kind === 'TOTAL_CREDITS' ? completedCredits : rule.kind === 'LIBERAL_TOTAL' ? liberalCredits : rule.kind === 'PRIMARY_MAJOR_CREDITS' ? majorCredits : null
        const satisfied = overrideValues && overrideMajorMinimum !== null
          ? academicUnitOverrideStatus(overrideValues, liberalCredits, majorCredits)
          : current !== null && rule.min !== undefined ? current >= rule.min : rule.kind === 'REQUIRED_COURSE_GROUP' ? missingCourses.length === 0 : null
        return <article key={rule.id} className="rule-item"><div className="rule-status">{satisfied === true ? <span className="status success"><CheckIcon />충족</span> : satisfied === false ? <span className="status warning"><WarningIcon />부족</span> : <span className="status neutral">확인 필요</span>}</div><div className="rule-content"><h3>{KIND_LABEL[rule.kind] ?? rule.kind}</h3>
          {current !== null && rule.min !== undefined && <p><strong>{rule.min}{rule.unit === 'CREDITS' ? '학점' : ''} 중 {Math.min(current, rule.min)}{rule.unit === 'CREDITS' ? '학점' : ''}</strong>{current < rule.min ? ` · ${rule.min - current}학점 부족` : ''}</p>}
          {rule.kind === 'REQUIRED_COURSE_GROUP' && <p><strong>{requiredCourses.length}과목 중 {requiredCourses.length - missingCourses.length}과목 입력</strong>{missingCourses.length ? ` · ${missingCourses.length}과목 확인 필요` : ''}</p>}
          {overrideValues && overrideMajorMinimum !== null && <p><strong>교양 {overrideValues.liberalMin ?? 0}~{overrideValues.liberalMax ?? '확인'}학점 · 전공 합계 {overrideMajorMinimum}학점</strong><br />현재 입력: 교양 {liberalCredits}학점 · 전공 {majorCredits}학점<br /><small>전공기초·전공필수·전공선택 하위영역은 학과 자료에서 별도로 확인해야 합니다.</small></p>}
          {current === null && rule.kind !== 'REQUIRED_COURSE_GROUP' && !overrideValues && <p>개인 기록 또는 학과 예외를 자동으로 확인할 수 없습니다.</p>}
          <details><summary>공식 근거</summary><ul>{rule.sourceRefs.map((ref) => { const key = Object.keys(SOURCE_URLS).find((prefix) => ref.startsWith(prefix)); return <li key={ref}>{key ? <a href={SOURCE_URLS[key]} target="_blank" rel="noreferrer">{ref}</a> : ref}</li> })}</ul></details>
        </div></article>
      })}</div>
    </section>
    {majorProgram && <section className="rule-results" aria-labelledby="major-required-title"><div className="section-heading"><div><h2 id="major-required-title">전공필수 이수 현황</h2><p>2026 교육과정편람에서 확인된 소속 전공 자료를 사용합니다.</p></div></div>{majorProgram.status === 'AVAILABLE' ? <div className="area-status-grid">{majorProgram.courses.map((course) => { const missing = missingMajorRequired.some((item) => item.courseCode === course.courseCode); return <article key={course.courseCode}><strong>{course.name}</strong><span className={`status ${missing ? 'warning' : 'success'}`}>{missing ? '미이수' : '이수'}</span></article> })}</div> : <p className="source-note">{majorProgram.manualReviewReason ?? '전공필수 과목은 소속 학과 자료에서 직접 확인해야 합니다.'}</p>}</section>}
    {departmentSource && <section className="department-evidence" aria-labelledby="department-evidence-title"><div className="section-heading"><div><h2 id="department-evidence-title">{departmentSource.academicUnit} 공식 확인 자료</h2><p>학과별 전공필수·선수과목은 확인된 공식 자료만 안내하며 자동 확정 판정에는 사용하지 않습니다.</p></div><span>2026-07-10 검수</span></div><dl><div><dt>전공필수 자료</dt><dd>{departmentSource.majorRequiredStatus}</dd></div><div><dt>선수과목 자료</dt><dd>{departmentSource.prerequisiteStatus}</dd></div>{departmentSource.handbookPage && <div><dt>교육과정편람</dt><dd>PDF {departmentSource.handbookPage}쪽</dd></div>}</dl><div className="evidence-actions">{departmentSource.curriculumUrl && <a href={departmentSource.curriculumUrl} target="_blank" rel="noreferrer">학과 교육과정 원문</a>}{departmentSource.graduationUrl && <a href={departmentSource.graduationUrl} target="_blank" rel="noreferrer">졸업요건 원문</a>}</div>{departmentSource.transitionNote && <p className="source-note">{departmentSource.transitionNote}</p>}</section>}
    {recommendations.length > 0 && <section className="requirement-recommendations"><div className="section-heading"><div><h2>이번 학기 부족 과목</h2><p>입력한 이수내역을 기준으로 개설된 필수과목을 연결했습니다.</p></div></div><div>{recommendations.map((section) => <article key={section.id}><span><strong>{section.name}</strong><small>{section.sectionCode}분반 · {section.professor ?? '교수 미정'} · {section.rawTime ?? '시간 미정'}</small></span><button type="button" onClick={() => onAddCourse(section)}>후보에 추가</button></article>)}</div></section>}
    <aside className="requirements-disclaimer"><WarningIcon /><div><strong>예상 점검 결과입니다.</strong><p>편입학, 학과 변경, 인정학점, 공학인증, 대체과목과 학과별 졸업시험은 추가 확인이 필요할 수 있습니다.</p></div></aside>
  </main>
}
