import type { Day, PlanMetrics, Section } from '../types'
import { timeToMinutes } from './time'

export function computeMetrics(sections: Section[]): PlanMetrics {
  const byDay = new Map<Day, Array<{ start: number; end: number }>>()
  for (const section of sections) {
    for (const session of section.sessions) {
      const entries = byDay.get(session.day) ?? []
      entries.push({ start: timeToMinutes(session.start), end: timeToMinutes(session.end) })
      byDay.set(session.day, entries)
    }
  }
  let totalGapMinutes = 0
  let earliest: number | null = null
  let latest: number | null = null
  const dailyMinutes: Partial<Record<Day, number>> = {}
  for (const [day, entries] of byDay) {
    entries.sort((left, right) => left.start - right.start)
    let dayMinutes = 0
    for (let index = 0; index < entries.length; index += 1) {
      const current = entries[index]
      if (!current) continue
      dayMinutes += current.end - current.start
      earliest = earliest === null ? current.start : Math.min(earliest, current.start)
      latest = latest === null ? current.end : Math.max(latest, current.end)
      const next = entries[index + 1]
      if (next) totalGapMinutes += Math.max(0, next.start - current.end)
    }
    dailyMinutes[day] = dayMinutes
  }
  const format = (value: number | null) => value === null ? null : `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
  return {
    credits: Array.from(new Map(sections.map((section) => [section.courseCode, section])).values()).reduce((sum, section) => sum + section.credits, 0),
    campusDays: byDay.size,
    totalGapMinutes,
    earliest: format(earliest),
    latest: format(latest),
    dailyMinutes,
  }
}
