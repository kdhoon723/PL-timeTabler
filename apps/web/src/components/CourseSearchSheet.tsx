import { useEffect, useMemo, useRef, useState } from 'react'
import type { AcademicProfile, CourseRole, CourseStats, Day, PlanItem, Section } from '../types'
import { canPlace } from '../domain/conflicts'
import { formatSession } from '../domain/time'
import { useSheetSwipeDismiss } from '../hooks/useSheetSwipeDismiss'
import { CheckIcon, CloseIcon, SearchIcon } from './Icons'

interface Props {
  open: boolean
  initialMode?: CourseSearchMode
  destination?: CourseSearchDestination
  sections: Section[]
  items: PlanItem[]
  profile: AcademicProfile | null
  courseStats?: ReadonlyMap<string, CourseStats>
  onClose: () => void
  onAdd: (section: Section, role?: CourseRole) => void
  onReviews?: (section: Section) => void
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

type CourseSort = 'NAME_ASC' | 'NAME_DESC' | 'POPULARITY' | 'RATING' | 'REVIEWS'

export function CourseSearchSheet({ open, initialMode = 'ALL', destination = 'TIMETABLE', sections, items, profile, courseStats, onClose, onAdd, onReviews }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const wasOpenRef = useRef(false)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('전체')
  const [day, setDay] = useState<'전체' | Day>('전체')
  const [grade, setGrade] = useState<'전체' | '1' | '2' | '3' | '4'>('전체')
  const [sort, setSort] = useState<CourseSort>('NAME_ASC')
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false)
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
      setGrade('전체')
      setSort('NAME_ASC')
      setAdvancedFiltersOpen(false)
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
      const sectionGrade = courseStats?.get(section.courseCode)?.grade
      return (!normalized || haystack.includes(normalized)) && categoryMatches && (day === '전체' || section.sessions.some((session) => session.day === day)) && (grade === '전체' || sectionGrade === Number(grade))
    })
    const grouped = new Map<string, Section[]>()
    for (const section of matched) grouped.set(section.courseCode, [...(grouped.get(section.courseCode) ?? []), section])
    const result = Array.from(grouped.values())
    result.sort((left, right) => {
      const a = left[0]!
      const b = right[0]!
      const aStats = courseStats?.get(a.courseCode)
      const bStats = courseStats?.get(b.courseCode)
      if (sort === 'NAME_DESC') return b.name.localeCompare(a.name, 'ko') || b.courseCode.localeCompare(a.courseCode)
      if (sort === 'POPULARITY') return (bStats?.popularityScore ?? 0) - (aStats?.popularityScore ?? 0) || a.name.localeCompare(b.name, 'ko')
      if (sort === 'RATING') return (bStats?.averageRating ?? 0) - (aStats?.averageRating ?? 0) || (bStats?.reviewCount ?? 0) - (aStats?.reviewCount ?? 0) || a.name.localeCompare(b.name, 'ko')
      if (sort === 'REVIEWS') return (bStats?.reviewCount ?? 0) - (aStats?.reviewCount ?? 0) || (bStats?.averageRating ?? 0) - (aStats?.averageRating ?? 0) || a.name.localeCompare(b.name, 'ko')
      return a.name.localeCompare(b.name, 'ko') || a.courseCode.localeCompare(b.courseCode)
    })
    return result.slice(0, 20)
  }, [category, courseStats, day, grade, query, sections, sort])

  const closeSheet = () => {
    setExpandedCourseCode(null)
    onClose()
  }

  const candidateMode = destination === 'CANDIDATES'
  const liberalFilterAvailable = categories.includes(LIBERAL_ELECTIVE_CATEGORY)
  const activeFilterCount = Number(category !== '전체') + Number(day !== '전체') + Number(grade !== '전체')

  const toggleCategory = (nextCategory: string) => {
    setCategory((value) => value === nextCategory ? '전체' : nextCategory)
    setExpandedCourseCode(null)
  }

  const resetFilters = () => {
    setCategory('전체')
    setDay('전체')
    setGrade('전체')
    setExpandedCourseCode(null)
  }
  const sheetDrag = useSheetSwipeDismiss(dialogRef, closeSheet)

  return <dialog className="sheet search-sheet" ref={dialogRef} onClose={closeSheet} onCancel={(event) => { event.preventDefault(); closeSheet() }} aria-labelledby="search-title">
    <div className="sheet-header" {...sheetDrag}>
      <div><h2 id="search-title">{candidateMode ? '자동완성 후보 담기' : '과목 추가'}</h2><p>{candidateMode ? '과목만 담으면 분반은 조건에 맞게 조합해요.' : `${sections.length.toLocaleString()}개 분반 · 검색 결과 ${groups.length}개 과목`}</p></div>
      <button type="button" className="icon-button" onClick={closeSheet} aria-label="과목 검색 닫기"><CloseIcon /></button>
    </div>
    <div className="search-controls">
      <label className="search-field"><span className="sr-only">과목명, 교수, 과목코드 검색</span><SearchIcon /><input ref={inputRef} value={query} onChange={(event) => { setQuery(event.target.value); setExpandedCourseCode(null) }} placeholder="과목명, 교수, 과목코드" /></label>
      <div className="search-filter-toolbar" aria-label="빠른 필터">
        {profile && preferredCategory && <button type="button" className={`search-filter-chip ${category === preferredCategory ? 'selected' : ''}`} aria-label={`내 전공 ${profile.department} ${preferredSectionCount}개 분반`} aria-pressed={category === preferredCategory} onClick={() => toggleCategory(preferredCategory)}>내 전공</button>}
        {liberalFilterAvailable && <button type="button" className={`search-filter-chip ${category === LIBERAL_ELECTIVE_CATEGORY ? 'selected' : ''}`} aria-label="교양선택 빠른 필터" aria-pressed={category === LIBERAL_ELECTIVE_CATEGORY} onClick={() => toggleCategory(LIBERAL_ELECTIVE_CATEGORY)}>교양선택</button>}
        <button type="button" className={`search-filter-chip ${advancedFiltersOpen || activeFilterCount > 0 ? 'selected' : ''}`} aria-expanded={advancedFiltersOpen} onClick={() => setAdvancedFiltersOpen((value) => !value)}>세부 필터{activeFilterCount > 0 ? ` ${activeFilterCount}` : ''}</button>
        {activeFilterCount > 0 && <button type="button" className="search-filter-reset" onClick={resetFilters}>필터 초기화</button>}
      </div>
      {advancedFiltersOpen && <div className="filter-row">
        <label><span>이수구분</span><select value={category} onChange={(event) => { setCategory(event.target.value); setExpandedCourseCode(null) }}>{categories.map((value) => <option value={value} key={value}>{value === preferredCategory && profile ? `내 전공 · ${profile.department}` : value}</option>)}</select></label>
        <label><span>요일</span><select value={day} onChange={(event) => { setDay(event.target.value as '전체' | Day); setExpandedCourseCode(null) }}>{['전체', '월', '화', '수', '목', '금', '토'].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
        <label><span>학년</span><select value={grade} onChange={(event) => { setGrade(event.target.value as typeof grade); setExpandedCourseCode(null) }}><option value="전체">전체</option><option value="1">1학년</option><option value="2">2학년</option><option value="3">3학년</option><option value="4">4학년</option></select></label>
        <label><span>정렬</span><select value={sort} onChange={(event) => setSort(event.target.value as CourseSort)}><option value="NAME_ASC">이름순</option><option value="NAME_DESC">이름 역순</option><option value="POPULARITY">인기순</option><option value="RATING">평점순</option><option value="REVIEWS">리뷰 많은 순</option></select></label>
      </div>}
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
        const stats = courseStats?.get(first.courseCode)
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
            <span><strong>{first.name}</strong><small>{first.courseCode} · {first.category} · {first.credits}학점{stats?.reviewCount ? ` · ★ ${stats.averageRating.toFixed(1)} (${stats.reviewCount})` : ''}</small></span><span>{group.length}개 분반 보기</span>
          </button>
          {onReviews && <button type="button" className="course-review-link" onClick={() => onReviews(first)}>리뷰</button>}
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
