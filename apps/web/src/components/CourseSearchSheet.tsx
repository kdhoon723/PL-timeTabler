import { useEffect, useMemo, useRef, useState } from 'react'
import type { AcademicProfile, Day, PlanItem, Section } from '../types'
import { canPlace } from '../domain/conflicts'
import { recommendedSection } from '../domain/requiredCourse'
import { formatSession } from '../domain/time'
import { CheckIcon, CloseIcon, SearchIcon } from './Icons'

interface Props {
  open: boolean
  sections: Section[]
  items: PlanItem[]
  profile: AcademicProfile | null
  onClose: () => void
  onAdd: (section: Section) => void
}

function normalizeAcademicUnit(value: string): string {
  return value.normalize('NFKC').replace(/\([^)]*\)$/u, '').replace(/[\s·∙・,._-]/gu, '').replace(/공통$/u, '')
}

function academicUnitFromCategory(category: string): string | null {
  if (!category.startsWith('전공(') || !category.endsWith(')')) return null
  const slash = category.lastIndexOf('/')
  return slash < 0 ? null : category.slice(slash + 1, -1)
}

export function CourseSearchSheet({ open, sections, items, profile, onClose, onAdd }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
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
    return ['전체', ...(preferredCategory ? [preferredCategory] : []), ...sorted.filter((value) => value !== preferredCategory)]
  }, [preferredCategory, sections])
  const selectedIds = useMemo(() => new Set(items.map((item) => item.sectionId)), [items])
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
    if (!categories.includes(category)) setCategory('전체')
  }, [categories, category])

  const groups = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('ko')
    const matched = sections.filter((section) => {
      const haystack = `${section.name} ${section.professor ?? ''} ${section.courseCode} ${section.category}`.toLocaleLowerCase('ko')
      return (!normalized || haystack.includes(normalized)) && (category === '전체' || section.category === category) && (day === '전체' || section.sessions.some((session) => session.day === day))
    })
    const grouped = new Map<string, Section[]>()
    for (const section of matched) grouped.set(section.courseCode, [...(grouped.get(section.courseCode) ?? []), section])
    return Array.from(grouped.values()).slice(0, 20)
  }, [category, day, query, sections])

  const closeSheet = () => {
    setExpandedCourseCode(null)
    onClose()
  }

  return <dialog className="sheet search-sheet" ref={dialogRef} onClose={closeSheet} onCancel={(event) => { event.preventDefault(); closeSheet() }} aria-labelledby="search-title">
    <div className="sheet-header">
      <div><h2 id="search-title">과목 추가</h2><p>{sections.length.toLocaleString()}개 분반 · 검색 결과 {groups.length}개 과목</p></div>
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
        const recommendationPool = currentSection ? group.filter((section) => section.id !== currentSection.id) : group
        const suggested = recommendedSection(recommendationPool.length ? recommendationPool : group, comparisonSections)
        const titleId = `course-${first.courseCode}-title`
        const sectionsId = `course-${first.courseCode}-sections`
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
              const isSuggested = suggested?.id === section.id
              const action = current ? '현재 분반' : planned ? '계획에 있음' : replacement ? '교체' : '추가'
              const states = [isSuggested ? '추천' : null, conflict ? '충돌' : null, timeUnknown ? '시간 미정' : null, action].filter((value): value is string => !!value)
              return <button aria-label={`${section.sectionCode}분반 ${section.professor ?? '교수 미정'} ${states.join(' ')}`} className={`section-option ${planned ? 'selected' : ''} ${conflict ? 'conflict' : ''}`} type="button" key={section.id} onClick={() => onAdd(section)} disabled={current || planned}>
                <span className="section-number">{section.sectionCode}분반</span>
                <span><strong>{section.professor ?? '교수 미정'}</strong><small>{section.sessions.length ? section.sessions.map(formatSession).join(' / ') : '수업시간 미정'}</small><span className="section-statuses">{isSuggested && <span>추천</span>}{conflict && <span className="danger-text">충돌</span>}{timeUnknown && <span>시간 미정</span>}</span></span>
                {current || planned ? <span className="selected-label"><CheckIcon />{action}</span> : <span className="add-label">{action}</span>}
              </button>
            })}
          </div>}
        </section>
      })}
    </div>
  </dialog>
}
