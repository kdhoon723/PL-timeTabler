import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AcademicProfile, CommonRules, MajorRequiredCourses, Section } from '../types'
import { canApplyMajorRequirements, recommendedSection } from '../domain/requiredCourse'
import { RequiredCoursePanel } from './RequiredCoursePanel'

afterEach(cleanup)

const section = (id: string, sectionCode: string, day: '월' | '화', start: string, end: string, courseCode = 'A', name = '필수', credits = 3): Section => ({ id, courseCode, sectionCode, name, professor: null, category: '전공', credits, rawTime: null, sessions: [{ day, start, end, room: null, building: null }] })

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
  const profile = { admissionYear: 2026, currentGrade: 1, entryType: 'FRESHMAN' } as AcademicProfile

  it('applies only to the matching freshman cohort', () => {
    expect(canApplyMajorRequirements(profile, requirements)).toBe(true)
    expect(canApplyMajorRequirements({ ...profile, admissionYear: 2025 }, requirements)).toBe(false)
    expect(canApplyMajorRequirements({ ...profile, entryType: 'TRANSFER' }, requirements)).toBe(false)
    expect(canApplyMajorRequirements({ ...profile, currentGrade: 3 }, requirements)).toBe(false)
    expect(canApplyMajorRequirements({ ...profile, currentGrade: 3, gradeMismatchAcknowledged: true }, requirements)).toBe(true)
  })
})

describe('required course progress', () => {
  const profile: AcademicProfile = { schemaVersion: 1, department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 3, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN', gradeMismatchAcknowledged: true, updatedAt: '2026-07-11T00:00:00Z' }
  const operatingSystems = section('561041-01', '01', '월', '13:30', '15:00', '561041', '운영체제론', 3)
  const computing = section('922601-01', '01', '화', '11:30', '13:30', '922601', 'AI시대의컴퓨팅사고', 2)
  const catalog = [operatingSystems, computing]
  const majorRequired: MajorRequiredCourses = { schemaVersion: 1, asOf: '2026-07-11', cohortAdmissionYear: 2026, source: 'test', method: 'test', programs: [{ academicUnit: '컴퓨터공학전공', status: 'AVAILABLE', manualReviewReason: null, handbookPages: [77], courses: [{ courseCode: '561041', name: '운영체제론', grade: 3, semesters: [1], handbookPage: 77 }] }] }
  const rules: CommonRules = { schemaVersion: 1, asOf: '2026-07-11', resultLabel: 'test', statuses: [], manualReviewReasons: [], rules: [{ id: 'required', admissionYears: { start: 2025 }, scope: { studentType: 'DOMESTIC', academicUnit: 'GENERAL_EXCEPTIONS_EXCLUDED' }, kind: 'REQUIRED_COURSE_GROUP', courses: [{ name: 'AI시대의컴퓨팅사고', credits: 2 }], sourceRefs: ['test'] }] }

  it('withholds automatic required-course options for an unconfirmed mismatch', async () => {
    render(<RequiredCoursePanel profile={{ ...profile, gradeMismatchAcknowledged: undefined }} rules={rules} majorRequired={majorRequired} catalog={catalog} items={[]} sectionById={new Map(catalog.map((value) => [value.id, value]))} onEditProfile={() => undefined} onAddRequired={() => undefined} />)

    const toggle = screen.getByRole('button', { name: /필수 과목 먼저/ })
    expect(toggle).toHaveTextContent('0/0개')
    await userEvent.click(toggle)
    expect(screen.getByText(/현재 학년 조합을 확인하기 전에는 전공필수를 자동 판정하지 않습니다/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '시간표에 배치' })).not.toBeInTheDocument()
  })

  it('starts collapsed with accurate course and credit progress plus a clear next action', async () => {
    render(<RequiredCoursePanel profile={profile} rules={rules} majorRequired={majorRequired} catalog={catalog} items={[{ sectionId: operatingSystems.id, role: 'must', locked: false }]} sectionById={new Map(catalog.map((value) => [value.id, value]))} onEditProfile={() => undefined} onAddRequired={() => undefined} />)

    const toggle = screen.getByRole('button', { name: /필수 과목 먼저/ })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(toggle).toHaveTextContent('1/2개')
    expect(toggle).toHaveTextContent('3/5학점')
    expect(toggle).toHaveTextContent('다음: 필수 분반 확인')
    expect(screen.queryByText('운영체제론')).not.toBeInTheDocument()

    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('운영체제론')).toBeInTheDocument()
  })

  it('places a required section through the expanded keyboard/tap alternative', async () => {
    const onAddRequired = vi.fn()
    render(<RequiredCoursePanel profile={profile} rules={rules} majorRequired={majorRequired} catalog={catalog} items={[]} sectionById={new Map(catalog.map((value) => [value.id, value]))} onEditProfile={() => undefined} onAddRequired={onAddRequired} />)
    await userEvent.click(screen.getByRole('button', { name: /필수 과목 먼저/ }))
    await userEvent.click(screen.getAllByRole('button', { name: '시간표에 배치' })[0]!)
    expect(onAddRequired).toHaveBeenCalled()
  })
})
