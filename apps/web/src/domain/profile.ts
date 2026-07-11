import type { AcademicBasis, AcademicProfile } from '../types'

export const PROFILE_STORAGE_KEY = 'pl-timetabler:profile:v2'
export const LEGACY_PROFILE_STORAGE_KEY = 'pl-timetabler:profile:v1'
export const ONBOARDING_STORAGE_KEY = 'pl-timetabler:onboarding:v1'
export const ACTIVE_SEMESTER = '2026-1'
export const ACTIVE_SEMESTER_YEAR = 2026

export type AcademicProgression = 'UNSPECIFIED' | 'CONSISTENT' | 'DELAYED' | 'ACCELERATED' | 'TRANSFER'

export function expectedFreshmanGrade(admissionYear: number, activeSemesterYear = ACTIVE_SEMESTER_YEAR): AcademicProfile['currentGrade'] | null {
  const expected = activeSemesterYear - admissionYear + 1
  return [1, 2, 3, 4].includes(expected) ? expected as AcademicProfile['currentGrade'] : null
}

export function academicProgression(profile: AcademicProfile): AcademicProgression {
  const basis = profile.academicBasis
  if (!basis) return 'UNSPECIFIED'
  if (basis.entryType === 'TRANSFER') return 'TRANSFER'
  const expected = expectedFreshmanGrade(basis.admissionYear)
  if (expected === null) return 'DELAYED'
  if (profile.currentGrade === expected) return 'CONSISTENT'
  return profile.currentGrade < expected ? 'DELAYED' : 'ACCELERATED'
}

export function isAcademicProfileConsistent(profile: AcademicProfile): boolean {
  const progression = academicProgression(profile)
  return progression === 'CONSISTENT' || progression === 'TRANSFER'
}

export function isAcademicProfileAuthoritative(profile: AcademicProfile): boolean {
  const progression = academicProgression(profile)
  return progression === 'CONSISTENT' || progression === 'TRANSFER' || progression === 'DELAYED' && profile.academicBasis?.gradeMismatchAcknowledged === true
}

function normalizeBasis(value: unknown): AcademicBasis | null {
  if (!value || typeof value !== 'object') return null
  const basis = value as Partial<AcademicBasis>
  const valid = Number.isInteger(basis.admissionYear)
    && basis.admissionYear! >= 2000
    && basis.admissionYear! <= new Date().getFullYear()
    && (basis.entryType === 'FRESHMAN' || basis.entryType === 'TRANSFER')
    && (basis.studentType === 'DOMESTIC' || basis.studentType === 'INTERNATIONAL' || basis.studentType === 'UNKNOWN')
    && (basis.sectionGroup === 'ODD' || basis.sectionGroup === 'EVEN' || basis.sectionGroup === 'UNKNOWN')
    && (basis.gradeMismatchAcknowledged === undefined || typeof basis.gradeMismatchAcknowledged === 'boolean')
  return valid ? basis as AcademicBasis : null
}

function normalizeProfile(value: unknown): AcademicProfile | null {
  if (!value || typeof value !== 'object') return null
  const profile = value as Partial<AcademicProfile>
  const basis = profile.academicBasis === null ? null : normalizeBasis(profile.academicBasis)
  const valid = profile.schemaVersion === 2
    && typeof profile.department === 'string'
    && profile.department.length > 0
    && [1, 2, 3, 4].includes(profile.currentGrade ?? 0)
    && (profile.academicBasis === null || basis !== null)
    && typeof profile.updatedAt === 'string'
  return valid ? { ...profile, academicBasis: basis } as AcademicProfile : null
}

function migrateLegacyProfile(value: unknown): AcademicProfile | null {
  if (!value || typeof value !== 'object') return null
  const legacy = value as Record<string, unknown>
  const basis = normalizeBasis({
    admissionYear: legacy.admissionYear,
    entryType: legacy.entryType,
    studentType: legacy.studentType ?? 'UNKNOWN',
    sectionGroup: legacy.sectionGroup,
    gradeMismatchAcknowledged: legacy.gradeMismatchAcknowledged,
  })
  if (legacy.schemaVersion !== 1 || typeof legacy.department !== 'string' || !legacy.department || ![1, 2, 3, 4].includes(Number(legacy.currentGrade)) || typeof legacy.updatedAt !== 'string' || !basis) return null
  return { schemaVersion: 2, department: legacy.department, currentGrade: legacy.currentGrade as AcademicProfile['currentGrade'], academicBasis: basis, updatedAt: legacy.updatedAt }
}

export function loadAcademicProfile(): AcademicProfile | null {
  try {
    const current: unknown = JSON.parse(localStorage.getItem(PROFILE_STORAGE_KEY) ?? 'null')
    const normalized = normalizeProfile(current)
    if (normalized) return normalized
    const legacy: unknown = JSON.parse(localStorage.getItem(LEGACY_PROFILE_STORAGE_KEY) ?? 'null')
    const migrated = migrateLegacyProfile(legacy)
    if (migrated) saveAcademicProfile(migrated)
    return migrated
  } catch {
    return null
  }
}

export function saveAcademicProfile(profile: AcademicProfile): void {
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile))
  localStorage.removeItem(LEGACY_PROFILE_STORAGE_KEY)
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'complete')
}

export function clearAcademicProfile(): void {
  localStorage.removeItem(PROFILE_STORAGE_KEY)
  localStorage.removeItem(LEGACY_PROFILE_STORAGE_KEY)
}

export function hasCompletedOnboarding(): boolean {
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'complete'
}

export function completeOnboardingWithoutProfile(): void {
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'complete')
}

export function createAcademicProfile(input: Omit<AcademicProfile, 'schemaVersion' | 'updatedAt'>): AcademicProfile {
  return { schemaVersion: 2, ...input, updatedAt: new Date().toISOString() }
}

// No department-level odd/even assignment rule is present in the verified
// 2026 handbook data yet. Keep the capability data-driven rather than guessing.
export function supportsSectionGroup(department: string): boolean {
  void department
  return false
}
