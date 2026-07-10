import { canPlace } from './conflicts'
import { isAcademicProfileAuthoritative } from './profile'
import type { AcademicProfile, MajorRequiredCourses, Section } from '../types'

export function canApplyMajorRequirements(profile: AcademicProfile, requirements: MajorRequiredCourses): boolean {
  return profile.entryType === 'FRESHMAN' && profile.admissionYear === requirements.cohortAdmissionYear && isAcademicProfileAuthoritative(profile)
}

export function recommendedSection(sections: Section[], active: Section[], sectionGroup: AcademicProfile['sectionGroup'] = 'UNKNOWN'): Section | null {
  const parity = sectionGroup === 'ODD' ? 1 : sectionGroup === 'EVEN' ? 0 : null
  return [...sections].sort((left, right) => {
    const leftScore = (canPlace(left, active) ? 0 : 100) + (left.sessions.length ? 0 : 20) + (parity !== null && Number(left.sectionCode) % 2 !== parity ? 5 : 0)
    const rightScore = (canPlace(right, active) ? 0 : 100) + (right.sessions.length ? 0 : 20) + (parity !== null && Number(right.sectionCode) % 2 !== parity ? 5 : 0)
    return leftScore - rightScore || left.sectionCode.localeCompare(right.sectionCode, 'ko')
  })[0] ?? null
}
