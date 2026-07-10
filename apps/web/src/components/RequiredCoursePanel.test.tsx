import { describe, expect, it } from 'vitest'
import type { AcademicProfile, MajorRequiredCourses, Section } from '../types'
import { canApplyMajorRequirements, recommendedSection } from '../domain/requiredCourse'

const section = (id: string, sectionCode: string, day: '월' | '화', start: string, end: string, courseCode = 'A'): Section => ({ id, courseCode, sectionCode, name: '필수', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [{ day, start, end, room: null, building: null }] })

describe('required section recommendation', () => {
  it('prefers a conflict-free section before section-number order', () => {
    const active = [section('active', '01', '월', '09:00', '10:00', 'B')]
    const conflict = section('conflict', '01', '월', '09:30', '10:30')
    const free = section('free', '02', '화', '09:00', '10:00')
    expect(recommendedSection([conflict, free], active)?.id).toBe('free')
  })

  it('uses the configured parity only as a tie-break preference', () => {
    const odd = section('odd', '01', '월', '11:00', '12:00')
    const even = section('even', '02', '화', '11:00', '12:00')
    expect(recommendedSection([odd, even], [], 'EVEN')?.id).toBe('even')
  })
})

describe('major requirement cohort boundary', () => {
  const requirements = { cohortAdmissionYear: 2026 } as MajorRequiredCourses
  const profile = { admissionYear: 2026, entryType: 'FRESHMAN' } as AcademicProfile

  it('applies only to the matching freshman cohort', () => {
    expect(canApplyMajorRequirements(profile, requirements)).toBe(true)
    expect(canApplyMajorRequirements({ ...profile, admissionYear: 2025 }, requirements)).toBe(false)
    expect(canApplyMajorRequirements({ ...profile, entryType: 'TRANSFER' }, requirements)).toBe(false)
  })
})
