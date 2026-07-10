import type { ConflictEdge, PlanItem, Section } from '../types'
import { sessionsOverlap } from './time'

export function activeItems(items: PlanItem[]): PlanItem[] {
  return items.filter((item) => item.role === 'must' || item.role === 'want')
}

export function findConflicts(items: PlanItem[], sectionById: Map<string, Section>): ConflictEdge[] {
  const active = activeItems(items)
  const result: ConflictEdge[] = []
  for (let leftIndex = 0; leftIndex < active.length; leftIndex += 1) {
    const leftItem = active[leftIndex]
    const left = leftItem ? sectionById.get(leftItem.sectionId) : undefined
    if (!left) continue
    for (let rightIndex = leftIndex + 1; rightIndex < active.length; rightIndex += 1) {
      const rightItem = active[rightIndex]
      const right = rightItem ? sectionById.get(rightItem.sectionId) : undefined
      if (!right) continue
      for (const leftSession of left.sessions) {
        const rightSession = right.sessions.find((session) => sessionsOverlap(leftSession, session))
        if (rightSession) {
          result.push({ leftId: left.id, rightId: right.id, leftName: left.name, rightName: right.name, sessions: [leftSession, rightSession] })
          break
        }
      }
    }
  }
  return result
}

export function canPlace(section: Section, selected: Section[], exceptId?: string): boolean {
  return selected.filter((other) => other.id !== exceptId).every((other) =>
    section.courseCode === other.courseCode || section.sessions.every((session) => other.sessions.every((otherSession) => !sessionsOverlap(session, otherSession))),
  )
}

export function findAlternatives(section: Section, catalog: Section[], selected: Section[]): Section[] {
  return catalog
    .filter((candidate) => candidate.courseCode === section.courseCode && candidate.id !== section.id)
    .filter((candidate) => canPlace(candidate, selected, section.id))
    .sort((left, right) => left.sectionCode.localeCompare(right.sectionCode, 'ko'))
}
