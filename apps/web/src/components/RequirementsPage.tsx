import { useEffect, useMemo, useState } from 'react'
import { loadCommonRules } from '../api/client'
import type { CommonRule, CommonRules, Section } from '../types'
import { CheckIcon, WarningIcon } from './Icons'

interface Props { catalog: Section[]; onBack: () => void; onAddCourse: (section: Section) => void }

const SOURCE_URLS: Record<string, string> = {
  'regulations-2-1-01': 'https://www.daejin.ac.kr/regltn/daejin/2/631/download.do',
  'regulations-2-1-02': 'https://www.daejin.ac.kr/regltn/daejin/2/612/download.do',
  'curriculum-guide-2026': 'https://www.daejin.ac.kr/bbs/daejin/188/458095/artclView.do',
}

const KIND_LABEL: Record<string, string> = {
  TOTAL_CREDITS: '졸업 총학점', REGISTERED_SEMESTERS: '등록 학기', GRADUATION_GPA: '졸업 평점', ADVISOR_COUNSELING: '지도교수 상담', LIBERAL_TOTAL: '교양 이수학점', REQUIRED_COURSE_GROUP: '교양 필수과목', PRIMARY_MAJOR_CREDITS: '주전공 이수학점', MAJOR_CREDIT_PAIR: '전공별 이수학점', ACADEMIC_UNIT_OVERRIDE: '학과별 예외 기준',
}

function applies(rule: CommonRule, year: number, path: string, department: string): boolean {
  if (rule.admissionYears?.start && year < rule.admissionYears.start) return false
  if (rule.admissionYears?.end && year > rule.admissionYears.end) return false
  if (rule.scope.programPath && rule.scope.programPath !== path) return false
  if (rule.scope.academicUnit && rule.scope.academicUnit !== 'GENERAL_EXCEPTIONS_EXCLUDED' && rule.scope.academicUnit !== department) return false
  return true
}

export function RequirementsPage({ catalog, onBack, onAddCourse }: Props) {
  const [rules, setRules] = useState<CommonRules | null>(null)
  const [error, setError] = useState(false)
  const [year, setYear] = useState(2026)
  const [department, setDepartment] = useState('일반학과')
  const [path, setPath] = useState('ADVANCED_MAJOR')
  const [completedCredits, setCompletedCredits] = useState(0)
  const [liberalCredits, setLiberalCredits] = useState(0)
  const [majorCredits, setMajorCredits] = useState(0)
  const [completedNames, setCompletedNames] = useState('')
  useEffect(() => { loadCommonRules().then(setRules).catch(() => setError(true)) }, [])
  const applicable = useMemo(() => rules?.rules.filter((rule) => applies(rule, year, path, department)) ?? [], [department, path, rules, year])
  const names = completedNames.split(/[\n,]/).map((value) => value.trim()).filter(Boolean)
  const requiredCourses = applicable.find((rule) => rule.kind === 'REQUIRED_COURSE_GROUP')?.courses ?? []
  const missingCourses = requiredCourses.filter((course) => !names.some((name) => name.replaceAll(' ', '').includes(course.name.replaceAll(' ', ''))))
  const recommendations = missingCourses.flatMap((course) => {
    const normalized = course.name.replaceAll(' ', '').toLocaleLowerCase('ko')
    return catalog.filter((section) => section.name.replaceAll(' ', '').toLocaleLowerCase('ko').includes(normalized) || (normalized === 'lct' && section.name.toLocaleLowerCase('ko').startsWith('lct'))).slice(0, 2)
  })

  return <main className="requirements-page">
    <header className="requirements-header"><button type="button" className="text-button" onClick={onBack}>← 시간표로</button><div><h1>예상 졸업요건 점검</h1><p>개인 이수내역은 이 브라우저 안에서만 계산하며 서버로 전송하지 않습니다.</p></div></header>
    {error && <div className="inline-error" role="alert">졸업요건 데이터를 불러오지 못했습니다.</div>}
    <section className="profile-panel" aria-labelledby="profile-title"><h2 id="profile-title">내 기준 선택</h2><div className="profile-grid">
      <label><span>입학연도</span><select value={year} onChange={(event) => setYear(Number(event.target.value))}>{Array.from({ length: 15 }, (_, index) => 2026 - index).map((value) => <option key={value}>{value}</option>)}</select></label>
      <label><span>학과</span><select value={department} onChange={(event) => setDepartment(event.target.value)}><option>일반학과</option><option>간호학과</option></select></label>
      <label><span>전공 방식</span><select value={path} onChange={(event) => setPath(event.target.value)}><option value="ADVANCED_MAJOR">심화전공</option><option value="DOUBLE_MAJOR">복수전공</option><option value="MINOR">부전공</option><option value="MICRO_MAJOR">마이크로전공</option></select></label>
      <label><span>현재 총 이수학점</span><input type="number" min="0" max="200" value={completedCredits} onChange={(event) => setCompletedCredits(Number(event.target.value))}/></label>
      <label><span>교양 이수학점</span><input type="number" min="0" max="80" value={liberalCredits} onChange={(event) => setLiberalCredits(Number(event.target.value))}/></label>
      <label><span>주전공 이수학점</span><input type="number" min="0" max="150" value={majorCredits} onChange={(event) => setMajorCredits(Number(event.target.value))}/></label>
    </div><label className="completed-field"><span>이수한 필수과목</span><textarea rows={3} value={completedNames} onChange={(event) => setCompletedNames(event.target.value)} placeholder="과목명을 쉼표나 줄바꿈으로 입력"/><small>최종 졸업 판정은 학교 포털과 소속 학과에서 반드시 확인하세요.</small></label></section>
    <section className="rule-results" aria-labelledby="result-title"><div className="section-heading"><div><h2 id="result-title">점검 결과</h2><p>공식 자료로 확정할 수 없는 항목은 ‘확인 필요’로 표시합니다.</p></div><span>기준 {rules?.asOf ?? '불러오는 중'}</span></div>
      {!rules && !error && <p>요건을 불러오는 중입니다…</p>}
      <div className="rule-list">{applicable.map((rule) => {
        const current = rule.kind === 'TOTAL_CREDITS' ? completedCredits : rule.kind === 'LIBERAL_TOTAL' ? liberalCredits : rule.kind === 'PRIMARY_MAJOR_CREDITS' ? majorCredits : null
        const satisfied = current !== null && rule.min !== undefined ? current >= rule.min : rule.kind === 'REQUIRED_COURSE_GROUP' ? missingCourses.length === 0 : null
        return <article key={rule.id} className="rule-item"><div className="rule-status">{satisfied === true ? <span className="status success"><CheckIcon />충족</span> : satisfied === false ? <span className="status warning"><WarningIcon />부족</span> : <span className="status neutral">확인 필요</span>}</div><div className="rule-content"><h3>{KIND_LABEL[rule.kind] ?? rule.kind}</h3>
          {current !== null && rule.min !== undefined && <p><strong>{rule.min}{rule.unit === 'CREDITS' ? '학점' : ''} 중 {Math.min(current, rule.min)}{rule.unit === 'CREDITS' ? '학점' : ''}</strong>{current < rule.min ? ` · ${rule.min - current}학점 부족` : ''}</p>}
          {rule.kind === 'REQUIRED_COURSE_GROUP' && <p><strong>{requiredCourses.length}과목 중 {requiredCourses.length - missingCourses.length}과목 입력</strong>{missingCourses.length ? ` · ${missingCourses.length}과목 확인 필요` : ''}</p>}
          {current === null && rule.kind !== 'REQUIRED_COURSE_GROUP' && <p>개인 기록 또는 학과 예외를 자동으로 확인할 수 없습니다.</p>}
          <details><summary>공식 근거</summary><ul>{rule.sourceRefs.map((ref) => { const key = Object.keys(SOURCE_URLS).find((prefix) => ref.startsWith(prefix)); return <li key={ref}>{key ? <a href={SOURCE_URLS[key]} target="_blank" rel="noreferrer">{ref}</a> : ref}</li> })}</ul></details>
        </div></article>
      })}</div>
    </section>
    {recommendations.length > 0 && <section className="requirement-recommendations"><div className="section-heading"><div><h2>이번 학기 부족 과목</h2><p>입력한 이수내역을 기준으로 개설된 필수과목을 연결했습니다.</p></div></div><div>{recommendations.map((section) => <article key={section.id}><span><strong>{section.name}</strong><small>{section.sectionCode}분반 · {section.professor ?? '교수 미정'} · {section.rawTime ?? '시간 미정'}</small></span><button type="button" onClick={() => onAddCourse(section)}>후보에 추가</button></article>)}</div></section>}
    <aside className="requirements-disclaimer"><WarningIcon /><div><strong>예상 점검 결과입니다.</strong><p>편입학, 학과 변경, 인정학점, 공학인증, 대체과목과 학과별 졸업시험은 추가 확인이 필요할 수 있습니다.</p></div></aside>
  </main>
}
