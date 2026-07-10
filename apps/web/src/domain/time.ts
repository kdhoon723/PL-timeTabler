import type { Day, Session } from '../types'

export function timeToMinutes(value: string): number {
  const match = /^(\d{2}):(\d{2})$/.exec(value)
  if (!match) throw new Error(`잘못된 시간 형식: ${value}`)
  return Number(match[1]) * 60 + Number(match[2])
}

export function minutesToTime(value: number): string {
  const hours = Math.floor(value / 60)
  const minutes = value % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

export function sessionsOverlap(left: Session, right: Session): boolean {
  if (left.day !== right.day) return false
  return timeToMinutes(left.start) < timeToMinutes(right.end) && timeToMinutes(right.start) < timeToMinutes(left.end)
}

export function formatSession(session: Session): string {
  const place = session.room ? ` · ${session.building ?? ''} ${session.room}`.trimEnd() : ''
  return `${session.day} ${session.start}–${session.end}${place}`
}

export function timetableBounds(sessions: Session[]): { start: number; end: number; days: Day[] } {
  const dayOrder: Day[] = ['월', '화', '수', '목', '금', '토']
  const start = sessions.length ? Math.min(8 * 60 + 30, ...sessions.map((session) => timeToMinutes(session.start))) : 8 * 60 + 30
  const end = sessions.length ? Math.max(18 * 60 + 30, ...sessions.map((session) => timeToMinutes(session.end))) : 18 * 60 + 30
  const hasSaturday = sessions.some((session) => session.day === '토')
  return { start: Math.floor(start / 30) * 30, end: Math.ceil(end / 30) * 30, days: dayOrder.slice(0, hasSaturday ? 6 : 5) }
}
