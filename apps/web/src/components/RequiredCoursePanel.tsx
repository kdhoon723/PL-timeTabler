import { useMemo, useState } from 'react'
import { applicableRules } from '../domain/requirements'
import { canApplyMajorRequirements, recommendedSection } from '../domain/requiredCourse'
import { academicProgression, isAcademicProfileAuthoritative, supportsSectionGroup } from '../domain/profile'
import { formatSession } from '../domain/time'
import type { AcademicProfile, CommonRules, MajorRequiredCourses, PlanItem, Section } from '../types'
import { CheckIcon } from './Icons'

interface Props {
  profile: AcademicProfile | null
  rules: CommonRules | null
  majorRequired: MajorRequiredCourses | null
  catalog: Section[]
  items: PlanItem[]
  sectionById: ReadonlyMap<string, Section>
  onEditProfile: () => void
  onAddRequired: (section: Section) => void
}

interface RequiredOption {
  key: string
  name: string
  code: string | null
  source: 'MAJOR' | 'LIBERAL'
  handbookPage?: number
  credits: number
  sections: Section[]
}

function normalizeName(value: string): string {
  return value.normalize('NFKC').replaceAll(/\s/g, '').toLocaleLowerCase('ko')
}

export function RequiredCoursePanel({ profile, rules, majorRequired, catalog, items, sectionById, onEditProfile, onAddRequired }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [sectionChoice, setSectionChoice] = useState<Record<string, string>>({})
  const active = useMemo(() => items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section), [items, sectionById])
  const selectedCodes = useMemo(() => new Set(active.map((section) => section.courseCode)), [active])
  const profileAuthoritative = !!profile && isAcademicProfileAuthoritative(profile)
  const acceleratedProgression = !!profile && academicProgression(profile) === 'ACCELERATED'
  const majorRequirementsApplicable = !!profile && !!majorRequired && canApplyMajorRequirements(profile, majorRequired)
  const options = useMemo<RequiredOption[]>(() => {
    if (!profile || !profileAuthoritative) return []
    const byCode = new Map<string, Section[]>()
    for (const section of catalog) byCode.set(section.courseCode, [...(byCode.get(section.courseCode) ?? []), section])
    const majorProgram = majorRequirementsApplicable ? majorRequired?.programs.find((program) => program.academicUnit === profile.department) : null
    const major = (majorProgram?.courses ?? [])
      .filter((course) => course.grade === profile.currentGrade && course.semesters.includes(1))
      .map((course) => {
        const sections = byCode.get(course.courseCode) ?? []
        return { key: `major-${course.courseCode}`, name: course.name, code: course.courseCode, source: 'MAJOR' as const, handbookPage: course.handbookPage, credits: sections[0]?.credits ?? 0, sections }
      })
    const studentType = profile.studentType === 'DOMESTIC' ? 'DOMESTIC' : 'OTHER'
    const liberalRule = profile.entryType === 'FRESHMAN' && profile.studentType !== 'UNKNOWN' ? applicableRules(rules?.rules ?? [], profile.admissionYear, 'ADVANCED_MAJOR', profile.department, studentType).find((rule) => rule.kind === 'REQUIRED_COURSE_GROUP') : null
    const liberal = (liberalRule?.courses ?? []).map((course) => {
      const required = normalizeName(course.name)
      const sections = catalog.filter((section) => normalizeName(section.name) === required || (required === 'lct' && normalizeName(section.name).startsWith('lct')))
      return { key: `liberal-${course.name}`, name: course.name, code: sections[0]?.courseCode ?? null, source: 'LIBERAL' as const, credits: course.credits, sections }
    })
    return [...major, ...liberal]
  }, [catalog, majorRequired, majorRequirementsApplicable, profile, profileAuthoritative, rules])
  const majorOptions = options.filter((option) => option.source === 'MAJOR')
  const liberalOptions = options.filter((option) => option.source === 'LIBERAL')
  const majorProgram = majorRequirementsApplicable ? majorRequired?.programs.find((program) => program.academicUnit === profile.department) : null
  const selectedCount = options.filter((option) => option.code && selectedCodes.has(option.code)).length
  const totalCredits = options.reduce((sum, option) => sum + option.credits, 0)
  const selectedCredits = options.filter((option) => option.code && selectedCodes.has(option.code)).reduce((sum, option) => sum + option.credits, 0)
  const nextAction = selectedCount === options.length && options.length > 0 ? '전공선택 과목 추가' : '필수 분반 확인'

  if (!profile) return <section className="required-panel profile-prompt"><div><span className="step-badge">1</span><div><h2>필수 과목부터 확인하세요</h2><p>학과와 학년을 설정하면 공식 교육과정편람의 전공필수를 바로 연결합니다.</p></div></div><button type="button" className="secondary-button" onClick={onEditProfile}>내 학과 설정</button></section>

  const renderOption = (option: RequiredOption) => {
    const selected = !!option.code && selectedCodes.has(option.code)
    const groupPreference = supportsSectionGroup(profile.department) ? profile.sectionGroup : 'UNKNOWN'
    const recommended = recommendedSection(option.sections, active, groupPreference)
    const chosenId = sectionChoice[option.key] ?? recommended?.id ?? ''
    const chosen = option.sections.find((section) => section.id === chosenId) ?? recommended
    return <article className={`required-option ${selected ? 'selected' : ''}`} key={option.key}><div className="required-option-main"><span className="required-state">{selected ? <CheckIcon /> : option.source === 'MAJOR' ? '전필' : '교필'}</span><span><strong>{option.name}</strong><small>{option.code ?? '과목코드 확인 중'}{option.handbookPage ? ` · 편람 ${option.handbookPage}쪽` : ''}</small></span></div>{option.sections.length ? <div className="required-option-action"><select aria-label={`${option.name} 분반`} value={chosenId} onChange={(event) => setSectionChoice((current) => ({ ...current, [option.key]: event.target.value }))}>{option.sections.map((section) => <option value={section.id} key={section.id}>{section.sectionCode}분반 · {section.professor ?? '교수 미정'} · {section.sessions.map(formatSession).join(' / ') || '시간 미정'}</option>)}</select><button type="button" className={selected ? 'secondary-button' : 'primary-button'} onClick={() => chosen && onAddRequired(chosen)}>{selected ? '분반 변경' : '시간표에 배치'}</button></div> : <span className="unavailable-label">1학기 미개설</span>}</article>
  }

  return <section className="required-panel" aria-labelledby="required-panel-title"><button type="button" className="required-panel-heading" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}><span className="step-badge">1</span><span><strong id="required-panel-title">필수 과목 먼저</strong><small>{profile.department} · {profile.currentGrade}학년 · {selectedCount}/{options.length}개 · {selectedCredits}/{totalCredits}학점</small><small className="required-next-action">다음: {nextAction}</small></span><span aria-hidden="true">{expanded ? '−' : '+'}</span></button>{expanded && <div className="required-panel-body">
    <div className="planner-steps" aria-label="시간표 만들기 순서"><span className="active">1 필수</span><span>2 전공선택</span><span>3 교양선택</span></div>
    <div className="required-note"><p>자동으로 넣지 않습니다. 원하는 분반을 확인하고 배치하면 시간표에 바로 표시돼요.{profile.sectionGroup !== 'UNKNOWN' && !supportsSectionGroup(profile.department) ? ' 선택한 홀짝 정보는 저장했지만 공식 분반표 확인 전에는 강제하지 않습니다.' : ''}</p><button type="button" className="text-button" onClick={onEditProfile}>학적 정보 변경</button></div>
    <div className="required-groups"><section><h3>{majorRequired?.cohortAdmissionYear ?? 2026} 입학 교육과정 · {profile.currentGrade}학년 전공필수</h3>{!profileAuthoritative ? <p className="muted-copy">{acceleratedProgression ? '현재 학년이 일반 예상보다 높아 학과 확인 전에는 전공필수를 자동 판정하지 않습니다. 학과에 진급·학점 인정 기준을 확인해 주세요.' : '입학연도와 현재 학년 조합을 확인하기 전에는 전공필수를 자동 판정하지 않습니다. 학적 정보에서 현재 학년을 확인해 주세요.'}</p> : !majorRequirementsApplicable ? <p className="muted-copy">현재 자동 판정 가능한 전공필수는 2026 신입학 교육과정입니다. 선택한 입학연도·전형은 임의로 대입하지 않으며, 해당 연도 편람을 직접 확인해야 합니다.</p> : majorProgram?.status === 'MANUAL_REVIEW' ? <p className="muted-copy">{majorProgram.manualReviewReason}</p> : majorOptions.length ? <div>{majorOptions.map(renderOption)}</div> : <p className="muted-copy">공식 편람상 이번 학년 1학기에 표시된 전공필수 과목이 없습니다.</p>}</section><section><h3>입학연도 기준 교양필수</h3>{!profileAuthoritative ? <p className="muted-copy">{acceleratedProgression ? '현재 학년이 일반 예상보다 높아 학과 확인 전에는 입학연도 기준 교양필수를 자동 판정하지 않습니다.' : '현재 학년 확인 전에는 입학연도 기준 교양필수를 자동 판정하지 않습니다.'}</p> : profile.entryType === 'TRANSFER' ? <p className="muted-copy">편입학은 인정학점과 대체 이수 결과에 따라 달라 자동 판정하지 않습니다. 학과와 교양대학 안내를 확인하세요.</p> : profile.studentType === 'UNKNOWN' ? <p className="muted-copy">국내학생 전용 교양필수 적용 여부를 판단하려면 학적 정보에서 학생 구분을 선택하세요.</p> : profile.studentType === 'INTERNATIONAL' ? <p className="muted-copy">국내학생 전용 교양필수는 적용하지 않았습니다. 외국인·기타 학생 기준은 국제교류대학과 교양대학 안내를 확인하세요.</p> : liberalOptions.length ? <div>{liberalOptions.map(renderOption)}</div> : <p className="muted-copy">선택한 입학연도에 자동 적용할 교양필수 기준이 없습니다.</p>}</section></div>
    <p className="required-disclaimer">전공필수는 입학연도별 교육과정이 일치할 때만 표시합니다. 편입·학과 변경·재수강·대체과목은 입학연도 편람과 학과 안내를 함께 확인하세요.</p>
  </div>}</section>
}
