import { describe, expect, it } from 'vitest'
import type { CommonRule } from '../types'
import { academicUnitOverrideStatus, applicableRules, completedCourseMatches } from '../domain/requirements'

const common = (id: string, kind: string): CommonRule => ({
  id,
  kind,
  admissionYears: { start: 2025 },
  scope: { academicUnit: 'GENERAL_EXCEPTIONS_EXCLUDED' },
  sourceRefs: [],
})

describe('graduation requirement safety boundaries', () => {
  it('uses the nursing override without applying generic liberal or major rules', () => {
    const rules: CommonRule[] = [
      common('generic-liberal', 'LIBERAL_TOTAL'),
      common('generic-major', 'PRIMARY_MAJOR_CREDITS'),
      { ...common('nursing-from-2025', 'ACADEMIC_UNIT_OVERRIDE'), scope: { academicUnit: '간호학과' } },
    ]
    expect(applicableRules(rules, 2026, 'ADVANCED_MAJOR', '간호학과', 'DOMESTIC').map((rule) => rule.id)).toEqual(['nursing-from-2025'])
    expect(applicableRules(rules, 2026, 'ADVANCED_MAJOR', '컴퓨터공학전공', 'DOMESTIC').map((rule) => rule.id)).toEqual(['generic-liberal', 'generic-major'])
  })

  it('does not apply domestic-only rules to students on a separate international track', () => {
    const domestic = { ...common('domestic-required', 'REQUIRED_COURSE_GROUP'), scope: { studentType: 'DOMESTIC' } }
    expect(applicableRules([domestic], 2026, 'ADVANCED_MAJOR', '국제학부', 'OTHER')).toEqual([])
  })

  it('does not count a longer, similarly named course as the required course', () => {
    expect(completedCourseMatches(['고급사고와표현실습'], '사고와표현')).toBe(false)
    expect(completedCourseMatches([' 사고와 표현 '], '사고와표현')).toBe(true)
  })

  it('never marks an aggregate nursing-major total as fully verified', () => {
    const values = { liberalMin: 25, liberalMax: 42, majorFoundation: 18, majorRequired: 78, majorElectiveMin: 5 }
    expect(academicUnitOverrideStatus(values, 30, 101)).toBeNull()
    expect(academicUnitOverrideStatus(values, 24, 101)).toBe(false)
  })
})
