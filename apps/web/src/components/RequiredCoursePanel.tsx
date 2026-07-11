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
  onBrowseMajor: () => void
  onBrowseLiberal: () => void
  initiallyExpanded?: boolean
}

interface RequiredOption {
  key: string
  name: string
  code: string | null
  source: 'MAJOR' | 'LIBERAL'
  handbookPage?: number
  credits: number
  sections: Section[]
  referenceOnly?: boolean
}

function normalizeName(value: string): string {
  return value.normalize('NFKC').replaceAll(/\s/g, '').toLocaleLowerCase('ko')
}

export function RequiredCoursePanel({ profile, rules, majorRequired, catalog, items, sectionById, onEditProfile, onAddRequired, onBrowseMajor, onBrowseLiberal, initiallyExpanded = false }: Props) {
  const [expanded, setExpanded] = useState(initiallyExpanded)
  const [sectionChoice, setSectionChoice] = useState<Record<string, string>>({})
  const basis = profile?.academicBasis ?? null
  const active = useMemo(() => items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section), [items, sectionById])
  const selectedCodes = useMemo(() => new Set(active.map((section) => section.courseCode)), [active])
  const profileAuthoritative = !!profile && isAcademicProfileAuthoritative(profile)
  const progression = profile ? academicProgression(profile) : 'UNSPECIFIED'
  const majorRequirementsApplicable = !!profile && !!majorRequired && canApplyMajorRequirements(profile, majorRequired)
  const majorProgram = profile ? majorRequired?.programs.find((program) => program.academicUnit === profile.department) ?? null : null
  const useMajorReference = !majorRequirementsApplicable && profileAuthoritative && basis?.entryType === 'FRESHMAN' && majorProgram?.status === 'AVAILABLE'
  const options = useMemo<RequiredOption[]>(() => {
    if (!profile || !profileAuthoritative) return []
    const byCode = new Map<string, Section[]>()
    for (const section of catalog) byCode.set(section.courseCode, [...(byCode.get(section.courseCode) ?? []), section])
    const major = (majorRequirementsApplicable || useMajorReference ? majorProgram?.courses ?? [] : [])
      .filter((course) => course.grade === profile.currentGrade && course.semesters.includes(1))
      .map((course) => {
        const sections = byCode.get(course.courseCode) ?? []
        return { key: `major-${course.courseCode}`, name: course.name, code: course.courseCode, source: 'MAJOR' as const, handbookPage: course.handbookPage, credits: sections[0]?.credits ?? 0, sections, referenceOnly: useMajorReference }
      })
    const studentType = basis?.studentType === 'DOMESTIC' ? 'DOMESTIC' : 'OTHER'
    const liberalRule = basis?.entryType === 'FRESHMAN' && basis.studentType !== 'UNKNOWN' ? applicableRules(rules?.rules ?? [], basis.admissionYear, 'ADVANCED_MAJOR', profile.department, studentType).find((rule) => rule.kind === 'REQUIRED_COURSE_GROUP') : null
    const liberal = (liberalRule?.courses ?? []).map((course) => {
      const required = normalizeName(course.name)
      const sections = catalog.filter((section) => normalizeName(section.name) === required || (required === 'lct' && normalizeName(section.name).startsWith('lct')))
      return { key: `liberal-${course.name}`, name: course.name, code: sections[0]?.courseCode ?? null, source: 'LIBERAL' as const, credits: course.credits, sections }
    })
    return [...major, ...liberal]
  }, [basis, catalog, majorProgram, majorRequirementsApplicable, profile, profileAuthoritative, rules, useMajorReference])
  const majorOptions = options.filter((option) => option.source === 'MAJOR')
  const liberalOptions = options.filter((option) => option.source === 'LIBERAL')
  const selectedCount = options.filter((option) => option.code && selectedCodes.has(option.code)).length
  const totalCredits = options.reduce((sum, option) => sum + option.credits, 0)
  const selectedCredits = options.filter((option) => option.code && selectedCodes.has(option.code)).reduce((sum, option) => sum + option.credits, 0)
  const nextAction = options.length === 0 || selectedCount === options.length ? '전공선택 찾기' : '필수 분반 확인'

  if (!profile) return <section className="required-panel profile-prompt"><div><span className="step-badge">1</span><div><h2>필수 과목부터 확인하세요</h2><p>학과와 학년을 설정하면 공식 교육과정편람의 전공필수를 바로 연결합니다.</p></div></div><button type="button" className="secondary-button" onClick={onEditProfile}>내 학과 설정</button></section>

  const renderOption = (option: RequiredOption) => {
    const selected = !!option.code && selectedCodes.has(option.code)
    const groupPreference = supportsSectionGroup(profile.department) ? basis?.sectionGroup : 'UNKNOWN'
    const recommended = recommendedSection(option.sections, active, groupPreference)
    const chosenId = sectionChoice[option.key] ?? recommended?.id ?? ''
    const chosen = option.sections.find((section) => section.id === chosenId) ?? recommended
    return <article className={`required-option ${selected ? 'selected' : ''}`} key={option.key}><div className="required-option-main"><span className="required-state">{selected ? <CheckIcon /> : option.referenceOnly ? '참고' : option.source === 'MAJOR' ? '전필' : '교필'}</span><span><strong>{option.name}</strong><small>{option.code ?? '과목코드 확인 중'}{option.handbookPage ? ` · 편람 ${option.handbookPage}쪽` : ''}</small></span></div>{option.sections.length ? <div className="required-option-action"><select aria-label={`${option.name} 분반`} value={chosenId} onChange={(event) => setSectionChoice((current) => ({ ...current, [option.key]: event.target.value }))}>{option.sections.map((section) => <option value={section.id} key={section.id}>{section.sectionCode}분반 · {section.professor ?? '교수 미정'} · {section.sessions.map(formatSession).join(' / ') || '시간 미정'}</option>)}</select><button type="button" className={selected ? 'secondary-button' : 'primary-button'} onClick={() => chosen && onAddRequired(chosen)}>{selected ? '분반 변경' : '시간표에 배치'}</button></div> : <span className="unavailable-label">1학기 미개설</span>}</article>
  }

  return <section className="required-panel" aria-labelledby="required-panel-title"><button type="button" className="required-panel-heading" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}><span className="step-badge">1</span><span><strong id="required-panel-title">필수 과목 먼저</strong><small>{profile.department} · {profile.currentGrade}학년 · {selectedCount}/{options.length}개 · {selectedCredits}/{totalCredits}학점</small><small className="required-next-action">다음: {nextAction}</small></span><span aria-hidden="true">{expanded ? '−' : '+'}</span></button>{expanded && <div className="required-panel-body">
    <nav className="planner-steps" aria-label="시간표 만들기 순서"><span className="active">1 필수</span><button type="button" onClick={onBrowseMajor}>2 전공선택</button><button type="button" onClick={onBrowseLiberal}>3 교양선택</button></nav>
    <div className="required-note"><p>분반을 고르면 시간표에 바로 추가돼요.</p><button type="button" className="text-button" onClick={onEditProfile}>설정 변경</button></div>
    {!basis ? <div className="academic-basis-prompt"><strong>입학연도를 추가할까요?</strong><p>설정하지 않아도 다음 단계로 갈 수 있어요.</p><button type="button" className="secondary-button" onClick={onEditProfile}>입학연도 추가</button></div>
      : !profileAuthoritative ? <div className="required-status"><strong>{progression === 'ACCELERATED' ? '입학연도와 학년이 맞지 않아 필수과목을 표시하지 않았어요.' : '입학연도와 현재 학년을 확인해 주세요.'}</strong><button type="button" className="secondary-button" onClick={onEditProfile}>입학연도 수정</button></div>
        : <div className="required-groups"><section><h3>{useMajorReference ? `확인 가능한 ${majorRequired?.cohortAdmissionYear} 기준 · ${profile.currentGrade}학년 전공필수` : `${basis.admissionYear} 입학 · ${profile.currentGrade}학년 전공필수`}</h3>{useMajorReference && <p className="required-reference-note">입학연도별 차이가 있을 수 있어 참고용으로 보여드려요.</p>}{majorProgram?.status === 'MANUAL_REVIEW' ? <p className="muted-copy">전공과목 검색에서 학년별 개설 과목을 확인해 보세요.</p> : majorOptions.length ? <div>{majorOptions.map(renderOption)}</div> : majorRequirementsApplicable ? <p className="muted-copy">이번 학기 전공필수가 없어요.</p> : <p className="muted-copy">전공과목 검색에서 학년별 개설 과목을 확인해 보세요.</p>}</section><section><h3>교양필수</h3>{basis.entryType === 'TRANSFER' ? <p className="muted-copy">편입생은 인정학점 결과를 확인해 주세요.</p> : basis.studentType === 'UNKNOWN' ? <p className="muted-copy">학생 구분을 설정해 주세요.</p> : basis.studentType === 'INTERNATIONAL' ? <p className="muted-copy">외국인 학생 기준은 별도 확인이 필요해요.</p> : liberalOptions.length ? <div>{liberalOptions.map(renderOption)}</div> : <p className="muted-copy">자동으로 추가할 교양필수가 없어요.</p>}</section></div>}
    <div className="planner-next-actions"><button type="button" className="primary-button" onClick={onBrowseMajor}>전공선택 찾기</button><button type="button" className="secondary-button" onClick={onBrowseLiberal}>교양선택 찾기</button></div>
    <details className="required-disclaimer"><summary>필수과목 판정 기준</summary><p>편입·학과 변경·재수강·대체과목은 학교 확인이 필요해요.</p></details>
  </div>}</section>
}
