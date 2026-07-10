import { useMemo, useRef, useState } from 'react'
import type { DragEvent } from 'react'
import type { ConflictEdge, Section } from '../types'
import type { CandidatePreviewState } from '../domain/candidateDiff'
import { minutesToTime, timeToMinutes, timetableBounds } from '../domain/time'

interface Props {
  sections: Section[]
  conflicts: ConflictEdge[]
  lockedIds: Set<string>
  onSelect: (section: Section) => void
  previewStatusById?: ReadonlyMap<string, CandidatePreviewState>
  dragEnabled?: boolean
  dragAlternativesById?: ReadonlyMap<string, readonly Section[]>
  onReplace?: (source: Section, replacement: Section) => void
}

const COLOR_CLASSES = ['course-0', 'course-1', 'course-2', 'course-3', 'course-4', 'course-5']

function colorFor(code: string): string {
  let hash = 0
  for (const char of code) hash = (hash * 31 + char.charCodeAt(0)) | 0
  return COLOR_CLASSES[Math.abs(hash) % COLOR_CLASSES.length] ?? COLOR_CLASSES[0]!
}

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

export function TimetableGrid({ sections, conflicts, lockedIds, onSelect, previewStatusById, dragEnabled = false, dragAlternativesById, onReplace }: Props) {
  const [dragSource, setDragSource] = useState<Section | null>(null)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const suppressClickUntil = useRef(0)
  const sessions = sections.flatMap((section) => section.sessions.map((session) => ({ section, session })))
  const dragAlternatives = dragSource ? (dragAlternativesById?.get(dragSource.id) ?? []).filter((section) => section.sessions.length > 0) : []
  const boundSessions = [...sessions.map(({ session }) => session), ...dragAlternatives.flatMap((section) => section.sessions)]
  const bounds = timetableBounds(boundSessions)
  const rows = Array.from({ length: (bounds.end - bounds.start) / 30 }, (_, index) => bounds.start + index * 30)
  const conflictIds = useMemo(() => new Set(conflicts.flatMap((edge) => [edge.leftId, edge.rightId])), [conflicts])
  const totalHeight = rows.length * 28

  const endDrag = () => {
    suppressClickUntil.current = Date.now() + 400
    setDragSource(null)
    setDropTargetId(null)
  }

  const dropReplacement = (event: DragEvent<HTMLElement>, replacement: Section) => {
    event.preventDefault()
    if (!dragSource || !dragAlternatives.some((candidate) => candidate.id === replacement.id) || !onReplace) return
    onReplace(dragSource, replacement)
    setAnnouncement(`${dragSource.name} ${replacement.sectionCode}분반으로 교체했습니다.`)
    endDrag()
  }

  return <section className="timetable-section" aria-labelledby="timetable-title">
    <div className="section-heading timetable-heading">
      <div><h1 id="timetable-title" tabIndex={-1}>내 시간표</h1><p>{sections.length ? `${sections.length}개 분반` : '과목을 추가해 시간표를 시작하세요'}</p></div>
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
            className={`course-block ${colorFor(section.courseCode)} ${conflictIds.has(section.id) ? 'conflict' : ''} ${previewState ? `preview-${previewState}` : ''} ${dragSource?.id === section.id ? 'drag-source' : ''}`}
            style={{ top, height, left: `calc(${dayIndex} * 100% / ${bounds.days.length})`, width: `calc(100% / ${bounds.days.length})` }}
            draggable={draggable}
            onDragStart={(event) => {
              if (!draggable) { event.preventDefault(); return }
              suppressClickUntil.current = Date.now() + 800
              event.dataTransfer.effectAllowed = 'move'
              event.dataTransfer.setData('text/plain', section.id)
              setAnnouncement(`${section.name} 분반 교체를 시작했습니다. 표시된 분반 시간에 놓으세요.`)
              setDragSource(section)
            }}
            onDragEnd={endDrag}
            onClick={() => { if (!previewState && Date.now() >= suppressClickUntil.current) onSelect(section) }}
            aria-disabled={previewState ? true : undefined}
            aria-describedby={draggable ? 'timetable-drag-instructions' : undefined}
            tabIndex={previewState ? -1 : undefined}
            aria-label={`${section.name} ${session.day} ${session.start}부터 ${session.end}${lockedIds.has(section.id) ? ', 잠김' : ''}${conflictIds.has(section.id) ? ', 충돌' : ''}${previewState ? `, ${PREVIEW_LABELS[previewState]}` : ''}${draggable ? ', 드래그하여 충돌 없는 다른 분반으로 교체' : ''}`}
          >
            <strong>{section.name}</strong><span>{session.start}</span><span>{session.room ?? section.professor ?? '장소 미정'}</span>
            {lockedIds.has(section.id) && <span className="block-state">잠김</span>}
            {previewState && <span className="block-state">{PREVIEW_BADGES[previewState]}</span>}
          </button>
        })}
        {dragAlternatives.flatMap((section) => section.sessions.map((session) => {
          const dayIndex = bounds.days.indexOf(session.day)
          if (dayIndex < 0) return null
          const top = ((timeToMinutes(session.start) - bounds.start) / 30) * 28
          const height = Math.max(28, ((timeToMinutes(session.end) - timeToMinutes(session.start)) / 30) * 28)
          return <div
            className={`section-drop-slot ${dropTargetId === section.id ? 'active' : ''}`}
            data-drop-section-id={section.id}
            key={`drop-${section.id}-${session.day}-${session.start}`}
            style={{ top, height, left: `calc(${dayIndex} * 100% / ${bounds.days.length})`, width: `calc(100% / ${bounds.days.length})` }}
            onDragEnter={() => setDropTargetId(section.id)}
            onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; setDropTargetId(section.id) }}
            onDrop={(event) => dropReplacement(event, section)}
            aria-label={`${section.name} ${section.sectionCode}분반 교체 위치, ${session.day} ${session.start}부터 ${session.end}`}
          ><strong>{section.sectionCode}분반으로 교체</strong><span>{session.start}</span></div>
        }))}
      </div>
    </div>
    <p className="sr-only" id="timetable-drag-instructions">데스크톱에서는 수업 블록을 끌어 표시되는 공식 분반 시간에 놓으세요. 임의 시간이나 위치로는 옮길 수 없습니다. 클릭하거나 Enter를 누르면 동일한 교체 목록을 열 수 있습니다.</p>
    <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
    <div className="sr-only" aria-label="요일별 수업 목록">
      {bounds.days.map((day) => <section key={day}><h2>{day}요일</h2><ul>{sessions.filter(({ session }) => session.day === day).map(({ section, session }) => <li key={section.id}>{section.name}, {session.start}부터 {session.end}, {session.room ?? '강의실 미정'}{previewStatusById?.get(section.id) ? `, ${PREVIEW_LABELS[previewStatusById.get(section.id)!]}` : ''}</li>)}</ul></section>)}
    </div>
  </section>
}
