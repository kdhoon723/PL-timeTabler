import { beforeEach, describe, expect, it } from 'vitest'
import { LEGACY_PROFILE_STORAGE_KEY, PROFILE_STORAGE_KEY, completeOnboardingWithoutProfile, createAcademicProfile, expectedFreshmanGrade, hasCompletedOnboarding, isAcademicProfileAuthoritative, isAcademicProfileConsistent, loadAcademicProfile, saveAcademicProfile } from './profile'

const basis = (admissionYear = 2026) => ({ admissionYear, entryType: 'FRESHMAN' as const, studentType: 'DOMESTIC' as const, sectionGroup: 'UNKNOWN' as const })

describe('academic profile persistence', () => {
  beforeEach(() => localStorage.clear())

  it('persists a basic planning profile without inventing an academic basis', () => {
    const profile = createAcademicProfile({ department: '컴퓨터공학전공', currentGrade: 3, academicBasis: null })
    saveAcademicProfile(profile)
    expect(loadAcademicProfile()).toEqual(profile)
    expect(hasCompletedOnboarding()).toBe(true)
  })

  it('allows guest use without inventing a profile', () => {
    completeOnboardingWithoutProfile()
    expect(hasCompletedOnboarding()).toBe(true)
    expect(loadAcademicProfile()).toBeNull()
  })

  it('ignores corrupted or out-of-range stored profiles', () => {
    localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify({ schemaVersion: 2, department: '컴퓨터공학전공', currentGrade: 9, academicBasis: null, updatedAt: '2026-07-11T00:00:00Z' }))
    expect(loadAcademicProfile()).toBeNull()
  })

  it('migrates explicitly entered v1 values into the optional academic basis', () => {
    localStorage.setItem(LEGACY_PROFILE_STORAGE_KEY, JSON.stringify({ schemaVersion: 1, department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 1, entryType: 'FRESHMAN', sectionGroup: 'UNKNOWN', updatedAt: '2026-07-10T00:00:00.000Z' }))
    const migrated = loadAcademicProfile()
    expect(migrated).toMatchObject({ schemaVersion: 2, department: '컴퓨터공학전공', academicBasis: { admissionYear: 2026, entryType: 'FRESHMAN', studentType: 'UNKNOWN' } })
    expect(localStorage.getItem(LEGACY_PROFILE_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(PROFILE_STORAGE_KEY)).not.toBeNull()
  })

  it('never authorizes accelerated progression through a leave-return acknowledgement', () => {
    const profile = createAcademicProfile({ department: '컴퓨터공학전공', currentGrade: 3, academicBasis: basis() })
    expect(expectedFreshmanGrade(profile.academicBasis!.admissionYear)).toBe(1)
    expect(isAcademicProfileConsistent(profile)).toBe(false)
    expect(isAcademicProfileAuthoritative(profile)).toBe(false)
    expect(isAcademicProfileAuthoritative({ ...profile, academicBasis: { ...profile.academicBasis!, gradeMismatchAcknowledged: true } })).toBe(false)
  })

  it('allows acknowledged delayed and older-than-four-year progression', () => {
    const delayed = createAcademicProfile({ department: '컴퓨터공학전공', currentGrade: 1, academicBasis: basis(2024) })
    const older = createAcademicProfile({ department: '컴퓨터공학전공', currentGrade: 4, academicBasis: basis(2021) })
    expect(isAcademicProfileAuthoritative(delayed)).toBe(false)
    expect(isAcademicProfileAuthoritative({ ...delayed, academicBasis: { ...delayed.academicBasis!, gradeMismatchAcknowledged: true } })).toBe(true)
    expect(isAcademicProfileAuthoritative(older)).toBe(false)
    expect(isAcademicProfileAuthoritative({ ...older, academicBasis: { ...older.academicBasis!, gradeMismatchAcknowledged: true } })).toBe(true)
  })

  it('keeps a consistent basis authoritative and exempts transfer entry', () => {
    const consistent = createAcademicProfile({ department: '컴퓨터공학전공', currentGrade: 1, academicBasis: basis() })
    const transfer = { ...consistent, currentGrade: 4 as const, academicBasis: { ...consistent.academicBasis!, entryType: 'TRANSFER' as const } }
    expect(isAcademicProfileAuthoritative(consistent)).toBe(true)
    expect(isAcademicProfileConsistent(transfer)).toBe(true)
  })
})
