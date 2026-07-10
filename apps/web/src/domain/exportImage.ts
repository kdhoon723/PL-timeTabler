import type { Section } from '../types'
import { timeToMinutes, timetableBounds } from './time'

export interface TimetableExportLayout {
  days: ReturnType<typeof timetableBounds>['days']
  start: number
  end: number
}

export function timetableExportLayout(sections: readonly Section[]): TimetableExportLayout {
  return timetableBounds(sections.flatMap((section) => section.sessions))
}

export function exportTimetablePng(sections: readonly Section[], semester: string): void {
  const canvas = document.createElement('canvas')
  canvas.width = 1200
  canvas.height = 760
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const { days, start, end } = timetableExportLayout(sections)
  const left = 90
  const right = 30
  const top = 100
  const height = 610
  const cellWidth = (canvas.width - left - right) / days.length

  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#16181D'
  ctx.font = '600 32px sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText(`${semester.replace('-', '학년도 ')}학기 시간표`, 48, 54)
  ctx.font = '500 20px sans-serif'
  ctx.textAlign = 'center'
  days.forEach((day, index) => ctx.fillText(day, left + index * cellWidth + cellWidth / 2, 90))

  ctx.strokeStyle = '#DCE0E6'
  for (let index = 0; index <= days.length; index += 1) {
    ctx.beginPath()
    ctx.moveTo(left + index * cellWidth, top)
    ctx.lineTo(left + index * cellWidth, top + height)
    ctx.stroke()
  }
  for (let minute = start; minute <= end; minute += 60) {
    const y = top + ((minute - start) / (end - start)) * height
    ctx.beginPath()
    ctx.moveTo(left, y)
    ctx.lineTo(left + days.length * cellWidth, y)
    ctx.stroke()
    ctx.fillStyle = '#555D6B'
    ctx.font = '16px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(`${Math.floor(minute / 60)}:${String(minute % 60).padStart(2, '0')}`, left - 12, y + 5)
  }

  sections.forEach((section, sectionIndex) => section.sessions.forEach((session) => {
    const dayIndex = days.indexOf(session.day)
    if (dayIndex < 0) return
    const x = left + dayIndex * cellWidth + 3
    const y = top + ((timeToMinutes(session.start) - start) / (end - start)) * height
    const blockHeight = ((timeToMinutes(session.end) - timeToMinutes(session.start)) / (end - start)) * height
    ctx.fillStyle = ['#E8EEFC', '#E8F3EC', '#F2EDF8', '#F8EEE8', '#E8F2F5', '#F5F0E5'][sectionIndex % 6] ?? '#E8EEFC'
    ctx.fillRect(x, y + 2, cellWidth - 6, Math.max(2, blockHeight - 4))
    ctx.save()
    ctx.beginPath()
    ctx.rect(x + 4, y + 4, cellWidth - 14, Math.max(2, blockHeight - 8))
    ctx.clip()
    ctx.fillStyle = '#16181D'
    ctx.textAlign = 'left'
    ctx.font = '600 16px sans-serif'
    ctx.fillText(section.name, x + 9, y + 26)
    ctx.font = '14px sans-serif'
    ctx.fillText(`${session.start} ${session.room ?? ''}`, x + 9, y + 48)
    ctx.restore()
  }))

  const link = document.createElement('a')
  link.download = `PL-시간표-${semester}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}
