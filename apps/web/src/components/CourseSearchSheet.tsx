import { useEffect, useMemo, useRef, useState } from 'react'
import type { Day, PlanItem, Section } from '../types'
import { formatSession } from '../domain/time'
import { CheckIcon, CloseIcon, SearchIcon } from './Icons'

interface Props {
  open: boolean
  sections: Section[]
  items: PlanItem[]
  onClose: () => void
  onAdd: (section: Section) => void
}

export function CourseSearchSheet({ open, sections, items, onClose, onAdd }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('전체')
  const [day, setDay] = useState<'전체' | Day>('전체')
  const categories = useMemo(() => ['전체', ...Array.from(new Set(sections.map((section) => section.category))).sort((a, b) => a.localeCompare(b, 'ko'))], [sections])
  const selectedIds = useMemo(() => new Set(items.map((item) => item.sectionId)), [items])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
      requestAnimationFrame(() => inputRef.current?.focus())
    } else if (!open && dialog.open) dialog.close()
  }, [open])

  const groups = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('ko')
    const matched = sections.filter((section) => {
      const haystack = `${section.name} ${section.professor ?? ''} ${section.courseCode} ${section.category}`.toLocaleLowerCase('ko')
      return (!normalized || haystack.includes(normalized)) && (category === '전체' || section.category === category) && (day === '전체' || section.sessions.some((session) => session.day === day))
    })
    const grouped = new Map<string, Section[]>()
    for (const section of matched) grouped.set(section.courseCode, [...(grouped.get(section.courseCode) ?? []), section])
    return Array.from(grouped.values()).slice(0, 60)
  }, [category, day, query, sections])

  return <dialog className="sheet search-sheet" ref={dialogRef} onClose={onClose} onCancel={(event) => { event.preventDefault(); onClose() }} aria-labelledby="search-title">
    <div className="sheet-header">
      <div><h2 id="search-title">과목 추가</h2><p>{sections.length.toLocaleString()}개 분반 · 검색 결과 {groups.length}개 과목</p></div>
      <button type="button" className="icon-button" onClick={onClose} aria-label="과목 검색 닫기"><CloseIcon /></button>
    </div>
    <div className="search-controls">
      <label className="search-field"><span className="sr-only">과목명, 교수, 과목코드 검색</span><SearchIcon /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="과목명, 교수, 과목코드" /></label>
      <div className="filter-row">
        <label><span>이수구분</span><select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
        <label><span>요일</span><select value={day} onChange={(event) => setDay(event.target.value as '전체' | Day)}>{['전체', '월', '화', '수', '목', '금', '토'].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
      </div>
    </div>
    <div className="search-results" aria-live="polite">
      {groups.length === 0 && <div className="empty-result"><strong>검색 결과가 없습니다.</strong><p>검색어나 필터를 바꿔 보세요.</p></div>}
      {groups.map((group) => {
        const first = group[0]
        if (!first) return null
        return <section className="course-group" key={first.courseCode}>
          <div className="course-group-title"><div><h3>{first.name}</h3><p>{first.courseCode} · {first.category} · {first.credits}학점</p></div><span>{group.length}개 분반</span></div>
          <div className="section-options">
            {group.map((section) => {
              const selected = selectedIds.has(section.id)
              return <button className={`section-option ${selected ? 'selected' : ''}`} type="button" key={section.id} onClick={() => onAdd(section)} disabled={selected}>
                <span className="section-number">{section.sectionCode}분반</span>
                <span><strong>{section.professor ?? '교수 미정'}</strong><small>{section.sessions.length ? section.sessions.map(formatSession).join(' / ') : '수업시간 미정'}</small></span>
                {selected ? <span className="selected-label"><CheckIcon />추가됨</span> : <span className="add-label">추가</span>}
              </button>
            })}
          </div>
        </section>
      })}
    </div>
  </dialog>
}
