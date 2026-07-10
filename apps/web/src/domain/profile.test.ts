import { beforeEach, describe, expect, it } from 'vitest'
import { completeOnboardingWithoutProfile, createAcademicProfile, hasCompletedOnboarding, loadAcademicProfile, saveAcademicProfile } from './profile'

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
})
