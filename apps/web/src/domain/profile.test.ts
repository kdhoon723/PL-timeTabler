import { beforeEach, describe, expect, it } from 'vitest'
import { completeOnboardingWithoutProfile, createAcademicProfile, expectedFreshmanGrade, hasCompletedOnboarding, isAcademicProfileAuthoritative, isAcademicProfileConsistent, loadAcademicProfile, saveAcademicProfile } from './profile'

describe('academic profile persistence', () => {
  beforeEach(() => localStorage.clear())

  it('persists a validated profile and completes onboarding', () => {
    const profile = createAcademicProfile({ department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 1, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN' })
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
    localStorage.setItem('pl-timetabler:profile:v1', JSON.stringify({ schemaVersion: 1, department: '컴퓨터공학전공', admissionYear: 1999, currentGrade: 9 }))
    expect(loadAcademicProfile()).toBeNull()
  })

  it('migrates profiles saved before student classification existed to unknown', () => {
    localStorage.setItem('pl-timetabler:profile:v1', JSON.stringify({ schemaVersion: 1, department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 1, entryType: 'FRESHMAN', sectionGroup: 'UNKNOWN', updatedAt: '2026-07-10T00:00:00.000Z' }))
    expect(loadAcademicProfile()?.studentType).toBe('UNKNOWN')
  })

  it('requires an acknowledgement before an unusual freshman grade is authoritative', () => {
    const profile = createAcademicProfile({ department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 3, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN' })

    expect(expectedFreshmanGrade(profile.admissionYear)).toBe(1)
    expect(isAcademicProfileConsistent(profile)).toBe(false)
    expect(isAcademicProfileAuthoritative(profile)).toBe(false)
    expect(isAcademicProfileAuthoritative({ ...profile, gradeMismatchAcknowledged: true })).toBe(true)
  })

  it('keeps old consistent profiles authoritative and exempts transfer entry', () => {
    const consistent = createAcademicProfile({ department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 1, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN' })
    const transfer = { ...consistent, currentGrade: 4 as const, entryType: 'TRANSFER' as const }

    expect(isAcademicProfileAuthoritative(consistent)).toBe(true)
    expect(isAcademicProfileConsistent(transfer)).toBe(true)
  })
})
