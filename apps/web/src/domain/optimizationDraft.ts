import type { DraftSnapshot } from '../types'

export function optimizationDraftFingerprint(draft: DraftSnapshot): string {
  const items = draft.items
    .map(({ sectionId, role, locked, professorLocked }) => ({ sectionId, role, locked, professorLocked: !!professorLocked }))
    .sort((left, right) => left.sectionId.localeCompare(right.sectionId) || left.role.localeCompare(right.role) || Number(left.locked) - Number(right.locked) || Number(left.professorLocked) - Number(right.professorLocked))
  const preferences = {
    ...draft.preferences,
    preferredFreeDays: [...draft.preferences.preferredFreeDays].sort(),
    excludedDays: [...draft.preferences.excludedDays].sort(),
  }
  return `optimization-draft-v1:${JSON.stringify({ semester: draft.semester, dataVersion: draft.dataVersion, items, preferences })}`
}
