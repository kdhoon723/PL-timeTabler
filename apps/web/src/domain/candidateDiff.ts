import type { PlanItem, Section } from '../types'

export type CandidatePreviewState = 'kept' | 'added' | 'removed' | 'swapped-in' | 'swapped-out'

export interface CandidateSwap {
  from: Section
  to: Section
}

export interface CandidateDiff {
  kept: Section[]
  added: Section[]
  removed: Section[]
  swaps: CandidateSwap[]
  previewSections: Array<{ section: Section; state: CandidatePreviewState }>
}

export function diffCandidate(
  candidateSectionIds: readonly string[],
  currentItems: readonly PlanItem[],
  sectionById: ReadonlyMap<string, Section>,
): CandidateDiff {
  const current = currentItems
    .filter((item) => item.role === 'must' || item.role === 'want')
    .map((item) => sectionById.get(item.sectionId))
    .filter((section): section is Section => !!section)
  const candidate = candidateSectionIds
    .map((sectionId) => sectionById.get(sectionId))
    .filter((section): section is Section => !!section)
  const currentIds = new Set(current.map((section) => section.id))
  const candidateIds = new Set(candidate.map((section) => section.id))
  const kept = candidate.filter((section) => currentIds.has(section.id))
  const removedPool = current.filter((section) => !candidateIds.has(section.id))
  const addedPool = candidate.filter((section) => !currentIds.has(section.id))
  const usedAdded = new Set<string>()
  const swaps: CandidateSwap[] = []

  for (const from of removedPool) {
    const to = addedPool.find((section) => !usedAdded.has(section.id) && section.courseCode === from.courseCode)
    if (!to) continue
    usedAdded.add(to.id)
    swaps.push({ from, to })
  }

  const swappedFromIds = new Set(swaps.map(({ from }) => from.id))
  const added = addedPool.filter((section) => !usedAdded.has(section.id))
  const removed = removedPool.filter((section) => !swappedFromIds.has(section.id))
  return {
    kept,
    added,
    removed,
    swaps,
    previewSections: [
      ...kept.map((section) => ({ section, state: 'kept' as const })),
      ...swaps.flatMap(({ from, to }) => [
        { section: from, state: 'swapped-out' as const },
        { section: to, state: 'swapped-in' as const },
      ]),
      ...removed.map((section) => ({ section, state: 'removed' as const })),
      ...added.map((section) => ({ section, state: 'added' as const })),
    ],
  }
}
