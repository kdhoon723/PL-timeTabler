import type { AcademicProfile } from '../types'

export const PROFILE_STORAGE_KEY = 'pl-timetabler:profile:v1'
export const ONBOARDING_STORAGE_KEY = 'pl-timetabler:onboarding:v1'
export const ACTIVE_SEMESTER = '2026-1'
export const ACTIVE_SEMESTER_YEAR = 2026

type GradeProfile = Pick<AcademicProfile, 'admissionYear' | 'currentGrade' | 'entryType'>

export function expectedFreshmanGrade(admissionYear: number, activeSemesterYear = ACTIVE_SEMESTER_YEAR): AcademicProfile['currentGrade'] | null {
  const expected = activeSemesterYear - admissionYear + 1
  return [1, 2, 3, 4].includes(expected) ? expected as AcademicProfile['currentGrade'] : null
}

export function isAcademicProfileConsistent(profile: GradeProfile): boolean {
  if (profile.entryType === 'TRANSFER') return true
  return expectedFreshmanGrade(profile.admissionYear) === profile.currentGrade
}

export function isAcademicProfileAuthoritative(profile: GradeProfile & Pick<AcademicProfile, 'gradeMismatchAcknowledged'>): boolean {
  return isAcademicProfileConsistent(profile) || profile.gradeMismatchAcknowledged === true
}

function normalizeProfile(value: unknown): AcademicProfile | null {
  if (!value || typeof value !== 'object') return null
  const profile = value as Partial<AcademicProfile>
  const valid = profile.schemaVersion === 1
    && typeof profile.department === 'string'
    && profile.department.length > 0
    && Number.isInteger(profile.admissionYear)
    && profile.admissionYear! >= 2000
    && profile.admissionYear! <= new Date().getFullYear()
    && [1, 2, 3, 4].includes(profile.currentGrade ?? 0)
    && (profile.entryType === 'FRESHMAN' || profile.entryType === 'TRANSFER')
    && (profile.studentType === undefined || profile.studentType === 'DOMESTIC' || profile.studentType === 'INTERNATIONAL' || profile.studentType === 'UNKNOWN')
    && (profile.sectionGroup === 'ODD' || profile.sectionGroup === 'EVEN' || profile.sectionGroup === 'UNKNOWN')
    && (profile.gradeMismatchAcknowledged === undefined || typeof profile.gradeMismatchAcknowledged === 'boolean')
    && typeof profile.updatedAt === 'string'
  if (!valid) return null
  return { ...profile, studentType: profile.studentType ?? 'UNKNOWN' } as AcademicProfile
}

export function loadAcademicProfile(): AcademicProfile | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(PROFILE_STORAGE_KEY) ?? 'null')
    return normalizeProfile(value)
  } catch {
    return null
  }
}

export function saveAcademicProfile(profile: AcademicProfile): void {
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile))
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'complete')
}

export function clearAcademicProfile(): void {
  localStorage.removeItem(PROFILE_STORAGE_KEY)
}

export function hasCompletedOnboarding(): boolean {
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'complete'
}

export function completeOnboardingWithoutProfile(): void {
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'complete')
}

export function createAcademicProfile(input: Omit<AcademicProfile, 'schemaVersion' | 'updatedAt'>): AcademicProfile {
  return { schemaVersion: 1, ...input, updatedAt: new Date().toISOString() }
}

// No department-level odd/even assignment rule is present in the verified
// 2026 handbook data yet. Keep the capability data-driven rather than guessing.
export function supportsSectionGroup(department: string): boolean {
  void department
  return false
}
