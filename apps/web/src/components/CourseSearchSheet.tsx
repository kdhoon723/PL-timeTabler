import { useEffect, useMemo, useRef, useState } from 'react'
import type { AcademicProfile, CourseRole, Day, PlanItem, Section } from '../types'
import { canPlace } from '../domain/conflicts'
import { formatSession } from '../domain/time'
import { CheckIcon, CloseIcon, SearchIcon } from './Icons'

interface Props {
  open: boolean
  initialMode?: CourseSearchMode
  destination?: CourseSearchDestination
  sections: Section[]
  items: PlanItem[]
  profile: AcademicProfile | null
  onClose: () => void
  onAdd: (section: Section, role?: CourseRole) => void
}

export type CourseSearchMode = 'ALL' | 'MAJOR' | 'LIBERAL'
export type CourseSearchDestination = 'TIMETABLE' | 'CANDIDATES'

const LIBERAL_ELECTIVE_CATEGORY = '교양선택 전체'

function normalizeAcademicUnit(value: string): string {
  return value.normalize('NFKC').replace(/\([^)]*\)$/u, '').replace(/[\s·∙・,._-]/gu, '').replace(/공통$/u, '')
}

function academicUnitFromCategory(category: string): string | null {
  if (!category.startsWith('전공(') || !category.endsWith(')')) return null
  const slash = category.lastIndexOf('/')
  return slash < 0 ? null : category.slice(slash + 1, -1)
}

export function CourseSearchSheet({ open, initialMode = 'ALL', destination = 'TIMETABLE', sections, items, profile, onClose, onAdd }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wasOpenRef = useRef(false)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('전체')
  const [day, setDay] = useState<'전체' | Day>('전체')
  const [expandedCourseCode, setExpandedCourseCode] = useState<string | null>(null)
  const preferredCategory = useMemo(() => {
    if (!profile) return null
    const department = normalizeAcademicUnit(profile.department)
    return Array.from(new Set(sections.map((section) => section.category))).find((value) => {
      const academicUnit = academicUnitFromCategory(value)
      return academicUnit ? normalizeAcademicUnit(academicUnit) === department : false
    }) ?? null
  }, [profile, sections])
  const preferredSectionCount = useMemo(() => preferredCategory ? sections.filter((section) => section.category === preferredCategory).length : 0, [preferredCategory, sections])
  const categories = useMemo(() => {
    const sorted = Array.from(new Set(sections.map((section) => section.category))).sort((a, b) => a.localeCompare(b, 'ko'))
    const hasLiberalElectives = sorted.some((value) => value.startsWith('교양선택'))
    return ['전체', ...(preferredCategory ? [preferredCategory] : []), ...(hasLiberalElectives ? [LIBERAL_ELECTIVE_CATEGORY] : []), ...sorted.filter((value) => value !== preferredCategory)]
  }, [preferredCategory, sections])
  const selectedIds = useMemo(() => new Set(items.map((item) => item.sectionId)), [items])
  const plannedCourseCodes = useMemo(() => new Set(items.filter((item) => item.role !== 'exclude').map((item) => sections.find((section) => section.id === item.sectionId)?.courseCode).filter((value): value is string => !!value)), [items, sections])
  const activeSections = useMemo(() => {
    const sectionById = new Map(sections.map((section) => [section.id, section]))
    return items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section)
  }, [items, sections])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
      requestAnimationFrame(() => inputRef.current?.focus())
    } else if (!open && dialog.open) dialog.close()
  }, [open])

  useEffect(() => {
    if (open && !wasOpenRef.current) {
      const initialCategory = initialMode === 'MAJOR' && preferredCategory
        ? preferredCategory
        : initialMode === 'LIBERAL'
          ? LIBERAL_ELECTIVE_CATEGORY
          : '전체'
      setCategory(categories.includes(initialCategory) ? initialCategory : '전체')
      setQuery('')
      setDay('전체')
      setExpandedCourseCode(null)
    }
    wasOpenRef.current = open
  }, [categories, initialMode, open, preferredCategory])

  useEffect(() => {
    if (!categories.includes(category)) setCategory('전체')
  }, [categories, category])

  const groups = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('ko')
    const matched = sections.filter((section) => {
      const haystack = `${section.name} ${section.professor ?? ''} ${section.courseCode} ${section.category}`.toLocaleLowerCase('ko')
      const categoryMatches = category === '전체'
        || category === LIBERAL_ELECTIVE_CATEGORY && section.category.startsWith('교양선택')
        || section.category === category
      return (!normalized || haystack.includes(normalized)) && categoryMatches && (day === '전체' || section.sessions.some((session) => session.day === day))
    })
    const grouped = new Map<string, Section[]>()
    for (const section of matched) grouped.set(section.courseCode, [...(grouped.get(section.courseCode) ?? []), section])
    return Array.from(grouped.values()).slice(0, 20)
  }, [category, day, query, sections])

  const closeSheet = () => {
    setExpandedCourseCode(null)
    onClose()
  }

  const candidateMode = destination === 'CANDIDATES'

  return <dialog className="sheet search-sheet" ref={dialogRef} onClose={closeSheet} onCancel={(event) => { event.preventDefault(); closeSheet() }} aria-labelledby="search-title">
    <div className="sheet-header">
      <div><h2 id="search-title">{candidateMode ? '자동완성 후보 담기' : '과목 추가'}</h2><p>{candidateMode ? '과목만 담으면 분반은 조건에 맞게 조합해요.' : `${sections.length.toLocaleString()}개 분반 · 검색 결과 ${groups.length}개 과목`}</p></div>
      <button type="button" className="icon-button" onClick={closeSheet} aria-label="과목 검색 닫기"><CloseIcon /></button>
    </div>
    <div className="search-controls">
      <label className="search-field"><span className="sr-only">과목명, 교수, 과목코드 검색</span><SearchIcon /><input ref={inputRef} value={query} onChange={(event) => { setQuery(event.target.value); setExpandedCourseCode(null) }} placeholder="과목명, 교수, 과목코드" /></label>
      {profile && preferredCategory && <button type="button" className={`major-filter-shortcut ${category === preferredCategory ? 'selected' : ''}`} aria-pressed={category === preferredCategory} onClick={() => { setCategory((value) => value === preferredCategory ? '전체' : preferredCategory); setExpandedCourseCode(null) }}><span><small>내 전공</small><strong>{profile.department}</strong></span><span>{preferredSectionCount}개 분반</span></button>}
      <div className="filter-row">
        <label><span>이수구분</span><select value={category} onChange={(event) => { setCategory(event.target.value); setExpandedCourseCode(null) }}>{categories.map((value) => <option value={value} key={value}>{value === preferredCategory && profile ? `내 전공 · ${profile.department}` : value}</option>)}</select></label>
        <label><span>요일</span><select value={day} onChange={(event) => { setDay(event.target.value as '전체' | Day); setExpandedCourseCode(null) }}>{['전체', '월', '화', '수', '목', '금', '토'].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
      </div>
    </div>
    <div className="search-results" aria-live="polite">
      {groups.length === 0 && <div className="empty-result"><strong>검색 결과가 없습니다.</strong><p>검색어나 필터를 바꿔 보세요.</p></div>}
      {groups.map((group) => {
        const first = group[0]
        if (!first) return null
        const expanded = expandedCourseCode === first.courseCode
        const currentSection = activeSections.find((section) => section.courseCode === first.courseCode)
        const comparisonSections = activeSections.filter((section) => section.id !== currentSection?.id)
        const titleId = `course-${first.courseCode}-title`
        const sectionsId = `course-${first.courseCode}-sections`
        const coursePlanned = plannedCourseCodes.has(first.courseCode)
        if (candidateMode) return <section className="course-group candidate-course-group" key={first.courseCode} aria-labelledby={titleId}>
          <div className="candidate-course-row">
            <button type="button" className="course-group-toggle" id={titleId} aria-expanded={expanded} aria-controls={sectionsId} onClick={() => setExpandedCourseCode((value) => value === first.courseCode ? null : first.courseCode)}>
              <span><strong>{first.name}</strong><small>{first.courseCode} · {first.category} · {first.credits}학점</small></span><span>{group.length}개 분반</span>
            </button>
            <button type="button" className="candidate-course-add" aria-label={`${first.name} ${coursePlanned ? '후보에 담김' : '후보로 담기'}`} disabled={coursePlanned} onClick={() => onAdd(first, 'backup')}>{coursePlanned ? '담김' : '후보로 담기'}</button>
          </div>
          {expanded && <ul className="candidate-section-preview" id={sectionsId}>{group.map((section) => <li key={section.id}><strong>{section.sectionCode}분반 · {section.professor ?? '교수 미정'}</strong><span>{section.sessions.length ? section.sessions.map(formatSession).join(' / ') : '수업시간 미정'}</span></li>)}</ul>}
        </section>
        return <section className="course-group" key={first.courseCode} aria-labelledby={titleId}>
          <button type="button" className="course-group-toggle" id={titleId} aria-expanded={expanded} aria-controls={sectionsId} onClick={() => setExpandedCourseCode((value) => value === first.courseCode ? null : first.courseCode)}>
            <span><strong>{first.name}</strong><small>{first.courseCode} · {first.category} · {first.credits}학점</small></span><span>{group.length}개 분반 보기</span>
          </button>
          {expanded && <div className="section-options" id={sectionsId}>
            {group.map((section) => {
              const current = currentSection?.id === section.id
              const planned = selectedIds.has(section.id)
              const replacement = !!currentSection && !current
              const conflict = !current && !canPlace(section, comparisonSections)
              const timeUnknown = section.sessions.length === 0
              const action = current ? '현재 분반' : planned ? '계획에 있음' : replacement ? '교체' : '추가'
              const states = [conflict ? '충돌' : null, timeUnknown ? '시간 미정' : null, action].filter((value): value is string => !!value)
              return <button aria-label={`${section.sectionCode}분반 ${section.professor ?? '교수 미정'} ${states.join(' ')}`} className={`section-option ${planned ? 'selected' : ''} ${conflict ? 'conflict' : ''}`} type="button" key={section.id} onClick={() => onAdd(section)} disabled={current || planned}>
                <span className="section-number">{section.sectionCode}분반</span>
                <span><strong>{section.professor ?? '교수 미정'}</strong><small>{section.sessions.length ? section.sessions.map(formatSession).join(' / ') : '수업시간 미정'}</small>{(conflict || timeUnknown) && <span className="section-statuses">{conflict && <span className="danger-text">충돌</span>}{timeUnknown && <span>시간 미정</span>}</span>}</span>
                {current || planned ? <span className="selected-label"><CheckIcon />{action}</span> : <span className="add-label">{action}</span>}
              </button>
            })}
          </div>}
        </section>
      })}
    </div>
  </dialog>
}
