import type { CommonRule } from '../types'

export const GENERAL_EXCEPTION_UNITS = new Set(['간호학과'])

export type StudentType = 'DOMESTIC' | 'OTHER'

export function requirementApplies(rule: CommonRule, year: number, path: string, department: string, studentType: StudentType): boolean {
  if (rule.admissionYears?.start && year < rule.admissionYears.start) return false
  if (rule.admissionYears?.end && year > rule.admissionYears.end) return false
  if (rule.scope.studentType === 'DOMESTIC' && studentType !== 'DOMESTIC') return false
  if (rule.scope.programPath && rule.scope.programPath !== path) return false
  if (rule.scope.academicUnit === 'GENERAL_EXCEPTIONS_EXCLUDED' && GENERAL_EXCEPTION_UNITS.has(department)) return false
  if (rule.scope.academicUnit && rule.scope.academicUnit !== 'GENERAL_EXCEPTIONS_EXCLUDED' && rule.scope.academicUnit !== department) return false
  return true
}

export function applicableRules(rules: CommonRule[], year: number, path: string, department: string, studentType: StudentType): CommonRule[] {
  return rules.filter((rule) => requirementApplies(rule, year, path, department, studentType))
}

const normalizedCourseName = (name: string) => name.normalize('NFKC').replaceAll(/\s/g, '').toLocaleLowerCase('ko')

export function completedCourseMatches(completedNames: string[], requiredName: string): boolean {
  const required = normalizedCourseName(requiredName)
  return completedNames.some((name) => normalizedCourseName(name) === required)
}

export function academicUnitOverrideStatus(values: Record<string, number>, liberalCredits: number, majorCredits: number): boolean | null {
  const majorMinimum = (values.majorFoundation ?? 0) + (values.majorRequired ?? 0) + (values.majorElectiveMin ?? 0)
  if (liberalCredits < (values.liberalMin ?? 0) || majorCredits < majorMinimum) return false
  // An aggregate major-credit input cannot prove each required subcategory.
  // Even a plausible total therefore remains a manual-review result.
  return null
}
