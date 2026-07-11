import { useEffect, useMemo, useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { DAYS, type ConflictEdge, type Section } from '../types'
import type { CandidatePreviewState } from '../domain/candidateDiff'
import { minutesToTime, timeToMinutes, timetableBounds } from '../domain/time'

interface Props {
  sections: Section[]
  conflicts: ConflictEdge[]
  lockedIds: Set<string>
  professorLockedIds?: Set<string>
  onSelect: (section: Section) => void
  previewStatusById?: ReadonlyMap<string, CandidatePreviewState>
  dragEnabled?: boolean
  dragAlternativesById?: ReadonlyMap<string, readonly Section[]>
  onReplace?: (source: Section, replacement: Section) => void
}

const COLOR_CLASSES = Array.from({ length: 20 }, (_, index) => `course-${index}`)

const PREVIEW_LABELS: Record<CandidatePreviewState, string> = {
  kept: '미리보기에서 유지',
  added: '미리보기에서 추가',
  removed: '미리보기에서 제외',
  'swapped-in': '미리보기에서 교체 후 분반',
  'swapped-out': '미리보기에서 교체 전 분반',
}

const PREVIEW_BADGES: Record<CandidatePreviewState, string> = {
  kept: '유지',
  added: '추가',
  removed: '제외',
  'swapped-in': '교체 후',
  'swapped-out': '교체 전',
}

interface DropSlotGroup {
  key: string
  day: Section['sessions'][number]['day']
  start: string
  end: string
  sections: Section[]
}

interface DropChooser {
  source: Section
  slot: DropSlotGroup
}

export function TimetableGrid({ sections, conflicts, lockedIds, professorLockedIds = new Set(), onSelect, previewStatusById, dragEnabled = false, dragAlternativesById, onReplace }: Props) {
  const [dragSource, setDragSource] = useState<Section | null>(null)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [dropChooser, setDropChooser] = useState<DropChooser | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const suppressClickUntil = useRef(0)
  const dragReturnFocusRef = useRef<HTMLButtonElement | null>(null)
  const firstChoiceRef = useRef<HTMLButtonElement | null>(null)
  const timetableTitleRef = useRef<HTMLHeadingElement | null>(null)
  const sessions = sections.flatMap((section) => section.sessions.map((session) => ({ section, session })))
  const colorByCourse = useMemo(() => {
    const firstWeeklySlot = new Map<string, { slot: number, appearance: number }>()
    sections.forEach((section, appearance) => {
      const slot = Math.min(...section.sessions.map((session) => DAYS.indexOf(session.day) * 24 * 60 + timeToMinutes(session.start)))
      const current = firstWeeklySlot.get(section.courseCode)
      if (!current || slot < current.slot) firstWeeklySlot.set(section.courseCode, { slot, appearance })
    })
    return new Map([...firstWeeklySlot.entries()]
      .sort(([, left], [, right]) => left.slot - right.slot || left.appearance - right.appearance)
      .map(([courseCode], index) => [courseCode, COLOR_CLASSES[index % COLOR_CLASSES.length] ?? COLOR_CLASSES[0]!]))
  }, [sections])
  const dragAlternatives = dragSource ? (dragAlternativesById?.get(dragSource.id) ?? []).filter((section) => section.sessions.length > 0) : []
  const boundSessions = [...sessions.map(({ session }) => session), ...dragAlternatives.flatMap((section) => section.sessions)]
  const bounds = timetableBounds(boundSessions)
  const rows = Array.from({ length: (bounds.end - bounds.start) / 30 }, (_, index) => bounds.start + index * 30)
  const conflictIds = useMemo(() => new Set(conflicts.flatMap((edge) => [edge.leftId, edge.rightId])), [conflicts])
  const dropSlotGroups = useMemo(() => {
    const groups = new Map<string, DropSlotGroup>()
    for (const section of dragAlternatives) {
      for (const session of section.sessions) {
        const key = `${session.day}-${session.start}-${session.end}`
        const group = groups.get(key) ?? { key, day: session.day, start: session.start, end: session.end, sections: [] }
        if (!group.sections.some((candidate) => candidate.id === section.id)) group.sections.push(section)
        groups.set(key, group)
      }
    }
    return [...groups.values()]
  }, [dragAlternatives])
  const resultingSectionCount = useMemo(() => new Set(sections
    .filter((section) => {
      const state = previewStatusById?.get(section.id)
      return state !== 'removed' && state !== 'swapped-out'
    })
    .map((section) => section.id)).size, [previewStatusById, sections])
  const totalHeight = rows.length * 28

  useEffect(() => {
    if (dropChooser) firstChoiceRef.current?.focus()
  }, [dropChooser])

  const endDrag = () => {
    suppressClickUntil.current = Date.now() + 400
    setDragSource(null)
    setDropTargetId(null)
  }

  const closeDropChooser = () => {
    setDropChooser(null)
    dragReturnFocusRef.current?.focus()
  }

  const chooseReplacement = (replacement: Section) => {
    if (!dropChooser || !onReplace) return
    onReplace(dropChooser.source, replacement)
    setAnnouncement(`${dropChooser.source.name} ${replacement.sectionCode}분반으로 교체했습니다.`)
    setDropChooser(null)
    timetableTitleRef.current?.focus()
  }

  const dropReplacement = (event: DragEvent<HTMLElement>, slot: DropSlotGroup) => {
    event.preventDefault()
    if (!dragSource || !slot.sections.every((replacement) => dragAlternatives.some((candidate) => candidate.id === replacement.id)) || !onReplace) return
    if (slot.sections.length > 1) {
      suppressClickUntil.current = Date.now() + 400
      setDropChooser({ source: dragSource, slot })
      setDragSource(null)
      setDropTargetId(null)
      return
    }
    const replacement = slot.sections[0]!
    onReplace(dragSource, replacement)
    setAnnouncement(`${dragSource.name} ${replacement.sectionCode}분반으로 교체했습니다.`)
    endDrag()
  }

  return <section className="timetable-section" aria-labelledby="timetable-title">
    <div className="section-heading timetable-heading">
      <div><h1 ref={timetableTitleRef} id="timetable-title" tabIndex={-1}>내 시간표</h1><p>{resultingSectionCount ? `${resultingSectionCount}개 분반` : '과목을 추가해 시간표를 시작하세요'}</p></div>
      {conflicts.length > 0 && <span className="status danger">충돌 {conflicts.length}건</span>}
    </div>
    <div className="timetable-grid" style={{ '--day-count': bounds.days.length } as React.CSSProperties}>
      <div className="grid-corner" />
      {bounds.days.map((day) => <div className="day-heading" key={day}>{day}</div>)}
      <div className="time-axis" style={{ height: totalHeight }}>
        {rows.map((minute, index) => index % 2 === 0 && <span key={minute} style={{ top: index * 28 }}>{minutesToTime(minute)}</span>)}
      </div>
      <div className="grid-body" style={{ height: totalHeight }}>
        {rows.map((minute, index) => <div className={`grid-line ${index % 2 ? 'minor' : ''}`} style={{ top: index * 28 }} key={minute} />)}
        {bounds.days.slice(1).map((day, index) => <div className="day-line" style={{ left: `${((index + 1) / bounds.days.length) * 100}%` }} key={day} />)}
        {sessions.map(({ section, session }) => {
          const dayIndex = bounds.days.indexOf(session.day)
          if (dayIndex < 0) return null
          const top = ((timeToMinutes(session.start) - bounds.start) / 30) * 28
          const height = Math.max(28, ((timeToMinutes(session.end) - timeToMinutes(session.start)) / 30) * 28)
          const previewState = previewStatusById?.get(section.id)
          const sectionAlternatives = (dragAlternativesById?.get(section.id) ?? []).filter((candidate) => candidate.sessions.length > 0)
          const draggable = dragEnabled && !previewStatusById && !lockedIds.has(section.id) && sectionAlternatives.length > 0 && !!onReplace
          return <button
            type="button"
            key={`${section.id}-${session.day}-${session.start}`}
            className={`course-block ${colorByCourse.get(section.courseCode) ?? COLOR_CLASSES[0]} ${conflictIds.has(section.id) ? 'conflict' : ''} ${previewState ? `preview-${previewState}` : ''} ${dragSource?.id === section.id ? 'drag-source' : ''}`}
            style={{ top, height, left: `calc(${dayIndex} * 100% / ${bounds.days.length})`, width: `calc(100% / ${bounds.days.length})` }}
            draggable={draggable}
            onDragStart={(event) => {
              if (!draggable) { event.preventDefault(); return }
              suppressClickUntil.current = Date.now() + 800
              event.dataTransfer.effectAllowed = 'move'
              event.dataTransfer.setData('text/plain', section.id)
              dragReturnFocusRef.current = event.currentTarget
              setDropChooser(null)
              setAnnouncement(`${section.name} 분반 교체를 시작했습니다. 표시된 분반 시간에 놓으세요.`)
              setDragSource(section)
            }}
            onDragEnd={endDrag}
            onClick={() => { if (!previewState && Date.now() >= suppressClickUntil.current) onSelect(section) }}
            aria-disabled={previewState ? true : undefined}
            aria-describedby={draggable ? 'timetable-drag-instructions' : undefined}
            tabIndex={previewState ? -1 : undefined}
            aria-label={`${section.name} ${session.day} ${session.start}부터 ${session.end}${lockedIds.has(section.id) ? ', 현재 수업 유지' : professorLockedIds.has(section.id) ? ', 교수 유지' : ''}${conflictIds.has(section.id) ? ', 충돌' : ''}${previewState ? `, ${PREVIEW_LABELS[previewState]}` : ''}${draggable ? ', 드래그하여 충돌 없는 다른 분반으로 교체' : ''}`}
          >
            <strong>{section.name}</strong><span>{session.start}</span><span>{session.room ?? section.professor ?? '장소 미정'}</span>
            {lockedIds.has(section.id) && <span className="block-state">유지</span>}
            {!lockedIds.has(section.id) && professorLockedIds.has(section.id) && <span className="block-state">교수</span>}
            {previewState && <span className="block-state">{PREVIEW_BADGES[previewState]}</span>}
          </button>
        })}
        {dropSlotGroups.map((slot) => {
          const dayIndex = bounds.days.indexOf(slot.day)
          if (dayIndex < 0) return null
          const top = ((timeToMinutes(slot.start) - bounds.start) / 30) * 28
          const height = Math.max(28, ((timeToMinutes(slot.end) - timeToMinutes(slot.start)) / 30) * 28)
          const singletonSection = slot.sections.length === 1 ? slot.sections[0] : null
          const targetId = singletonSection ? `section:${singletonSection.id}` : `slot:${slot.key}`
          return <div
            className={`section-drop-slot ${dropTargetId === targetId ? 'active' : ''}`}
            data-drop-section-id={singletonSection?.id}
            data-drop-slot-key={slot.key}
            key={`drop-${slot.key}`}
            style={{ top, height, left: `calc(${dayIndex} * 100% / ${bounds.days.length})`, width: `calc(100% / ${bounds.days.length})` }}
            onDragEnter={() => setDropTargetId(targetId)}
            onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; setDropTargetId(targetId) }}
            onDrop={(event) => dropReplacement(event, slot)}
            aria-label={singletonSection ? `${singletonSection.name} ${singletonSection.sectionCode}분반 교체 위치, ${slot.day} ${slot.start}부터 ${slot.end}` : `${slot.day} ${slot.start} 같은 시간 공식 분반 ${slot.sections.length}개 선택 위치`}
          ><strong>{singletonSection ? `${singletonSection.sectionCode}분반으로 교체` : `${slot.sections.length}개 분반 중 선택`}</strong><span>{slot.start}</span></div>
        })}
      </div>
    </div>
    {dropChooser && <div className="section-drop-chooser" role="dialog" aria-labelledby="drop-chooser-title" onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); closeDropChooser() } }}>
      <div><h2 id="drop-chooser-title">같은 시간 분반 선택</h2><p>{dropChooser.slot.day} {dropChooser.slot.start}–{dropChooser.slot.end} 공식 개설 분반입니다.</p></div>
      <div className="drop-choice-list">{dropChooser.slot.sections.map((section, index) => <button ref={index === 0 ? firstChoiceRef : undefined} type="button" key={section.id} onClick={() => chooseReplacement(section)} aria-label={`${section.sectionCode}분반 선택`}><span><strong>{section.sectionCode}분반 · {section.professor ?? '교수 미정'}</strong><small>{section.sessions.map((session) => `${session.day} ${session.start}–${session.end}`).join(' / ')}</small></span><span>선택</span></button>)}</div>
      <button type="button" className="secondary-button" onClick={closeDropChooser}>취소</button>
    </div>}
    <p className="sr-only" id="timetable-drag-instructions">데스크톱에서는 수업 블록을 끌어 표시되는 공식 분반 시간에 놓으세요. 임의 시간이나 위치로는 옮길 수 없습니다. 클릭하거나 Enter를 누르면 동일한 교체 목록을 열 수 있습니다.</p>
    <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
    <div className="sr-only" aria-label="요일별 수업 목록">
      {bounds.days.map((day) => <section key={day}><h2>{day}요일</h2><ul>{sessions.filter(({ session }) => session.day === day).map(({ section, session }) => <li key={section.id}>{section.name}, {session.start}부터 {session.end}, {session.room ?? '강의실 미정'}{previewStatusById?.get(section.id) ? `, ${PREVIEW_LABELS[previewStatusById.get(section.id)!]}` : ''}</li>)}</ul></section>)}
    </div>
  </section>
}
