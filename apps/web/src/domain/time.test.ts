import { describe, expect, it } from 'vitest'
import type { Session } from '../types'
import { sessionsOverlap, timeToMinutes, timetableBounds } from './time'

const session = (day: Session['day'], start: string, end: string): Session => ({ day, start, end, room: null, building: null })

describe('half-open timetable intervals', () => {
  it('does not treat a back-to-back class as a conflict', () => {
    expect(sessionsOverlap(session('월', '09:30', '11:30'), session('월', '11:30', '13:30'))).toBe(false)
  })
  it('detects a real overlap but not another day', () => {
    expect(sessionsOverlap(session('화', '09:30', '11:30'), session('화', '11:00', '12:00'))).toBe(true)
    expect(sessionsOverlap(session('화', '09:30', '11:30'), session('수', '10:00', '11:00'))).toBe(false)
  })
  it('expands the grid for Saturday and late classes', () => {
    const bounds = timetableBounds([session('토', '18:30', '22:00')])
    expect(bounds.days).toContain('토')
    expect(bounds.end).toBe(22 * 60)
  })
  it('rejects malformed times', () => expect(() => timeToMinutes('9:30')).toThrow('잘못된 시간 형식'))
})
