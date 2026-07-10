import { useMemo } from 'react'
import type { ConflictEdge, Section } from '../types'
import { minutesToTime, timeToMinutes, timetableBounds } from '../domain/time'

interface Props {
  sections: Section[]
  conflicts: ConflictEdge[]
  lockedIds: Set<string>
  onSelect: (section: Section) => void
}

const COLOR_CLASSES = ['course-0', 'course-1', 'course-2', 'course-3', 'course-4', 'course-5']

function colorFor(code: string): string {
  let hash = 0
  for (const char of code) hash = (hash * 31 + char.charCodeAt(0)) | 0
  return COLOR_CLASSES[Math.abs(hash) % COLOR_CLASSES.length] ?? COLOR_CLASSES[0]!
}

export function TimetableGrid({ sections, conflicts, lockedIds, onSelect }: Props) {
  const sessions = sections.flatMap((section) => section.sessions.map((session) => ({ section, session })))
  const bounds = timetableBounds(sessions.map(({ session }) => session))
  const rows = Array.from({ length: (bounds.end - bounds.start) / 30 }, (_, index) => bounds.start + index * 30)
  const conflictIds = useMemo(() => new Set(conflicts.flatMap((edge) => [edge.leftId, edge.rightId])), [conflicts])
  const totalHeight = rows.length * 28

  return <section className="timetable-section" aria-labelledby="timetable-title">
    <div className="section-heading timetable-heading">
      <div><h1 id="timetable-title">내 시간표</h1><p>{sections.length ? `${sections.length}개 분반` : '과목을 추가해 시간표를 시작하세요'}</p></div>
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
          return <button
            type="button"
            key={`${section.id}-${session.day}-${session.start}`}
            className={`course-block ${colorFor(section.courseCode)} ${conflictIds.has(section.id) ? 'conflict' : ''}`}
            style={{ top, height, left: `calc(${dayIndex} * 100% / ${bounds.days.length})`, width: `calc(100% / ${bounds.days.length})` }}
            onClick={() => onSelect(section)}
            aria-label={`${section.name} ${session.day} ${session.start}부터 ${session.end}${lockedIds.has(section.id) ? ', 잠김' : ''}${conflictIds.has(section.id) ? ', 충돌' : ''}`}
          >
            <strong>{section.name}</strong><span>{session.start}</span><span>{session.room ?? section.professor ?? '장소 미정'}</span>
            {lockedIds.has(section.id) && <span className="block-state">잠김</span>}
          </button>
        })}
      </div>
    </div>
    <div className="sr-only" aria-label="요일별 수업 목록">
      {bounds.days.map((day) => <section key={day}><h2>{day}요일</h2><ul>{sessions.filter(({ session }) => session.day === day).map(({ section, session }) => <li key={section.id}>{section.name}, {session.start}부터 {session.end}, {session.room ?? '강의실 미정'}</li>)}</ul></section>)}
    </div>
  </section>
}
