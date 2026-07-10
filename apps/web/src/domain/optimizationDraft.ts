import type { DraftSnapshot } from '../types'

export function optimizationDraftFingerprint(draft: DraftSnapshot): string {
  const items = draft.items
    .map(({ sectionId, role, locked }) => ({ sectionId, role, locked }))
    .sort((left, right) => left.sectionId.localeCompare(right.sectionId) || left.role.localeCompare(right.role) || Number(left.locked) - Number(right.locked))
  const preferences = {
    ...draft.preferences,
    preferredFreeDays: [...draft.preferences.preferredFreeDays].sort(),
  }
  return `optimization-draft-v1:${JSON.stringify({ semester: draft.semester, dataVersion: draft.dataVersion, items, preferences })}`
}
