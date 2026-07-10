import type { DraftSnapshot, PlanItem, Preferences, Section } from '../types'
import { DEFAULT_PREFERENCES, normalizeDraftSnapshot } from '../domain/draftSchema'
import { decodeDraft } from '../domain/share'

export { DEFAULT_PREFERENCES } from '../domain/draftSchema'

export function emptyDraft(): DraftSnapshot {
  return { schemaVersion: 1, semester: '2026-1', dataVersion: null, items: [], preferences: { ...DEFAULT_PREFERENCES, preferredFreeDays: [] }, updatedAt: new Date().toISOString() }
}

export interface HistoryState {
  past: DraftSnapshot[]
  present: DraftSnapshot
  future: DraftSnapshot[]
}

export type DraftAction =
  | { type: 'LOAD'; snapshot: DraftSnapshot }
  | { type: 'CATALOG'; dataVersion: string; validIds: ReadonlySet<string> }
  | { type: 'ADD'; item: PlanItem }
  | { type: 'REMOVE'; sectionId: string }
  | { type: 'SWAP'; fromId: string; toId: string }
  | { type: 'PATCH_ITEM'; sectionId: string; patch: Partial<Omit<PlanItem, 'sectionId'>> }
  | { type: 'ITEMS'; items: PlanItem[] }
  | { type: 'PREFERENCES'; preferences: Preferences }
  | { type: 'APPLY'; items: PlanItem[] }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR' }

const stamp = (snapshot: DraftSnapshot): DraftSnapshot => ({ ...snapshot, updatedAt: new Date().toISOString() })

function change(state: HistoryState, present: DraftSnapshot): HistoryState {
  return { past: [...state.past.slice(-39), state.present], present: stamp(present), future: [] }
}

export function draftReducer(state: HistoryState, action: DraftAction): HistoryState {
  switch (action.type) {
    case 'LOAD': return { past: [], present: action.snapshot, future: [] }
    case 'CATALOG': {
      const hydrate = (snapshot: DraftSnapshot): DraftSnapshot => ({
        ...snapshot,
        dataVersion: action.dataVersion,
        items: snapshot.items.filter((item) => action.validIds.has(item.sectionId)),
      })
      return {
        past: state.past.map(hydrate),
        present: stamp(hydrate(state.present)),
        future: state.future.map(hydrate),
      }
    }
    case 'ADD': {
      const existing = state.present.items.find((item) => item.sectionId === action.item.sectionId)
      if (existing) return state
      return change(state, { ...state.present, items: [...state.present.items, action.item] })
    }
    case 'REMOVE': return change(state, { ...state.present, items: state.present.items.filter((item) => item.sectionId !== action.sectionId) })
    case 'SWAP': return change(state, { ...state.present, items: state.present.items.map((item) => item.sectionId === action.fromId ? { ...item, sectionId: action.toId } : item) })
    case 'PATCH_ITEM': return change(state, { ...state.present, items: state.present.items.map((item) => item.sectionId === action.sectionId ? { ...item, ...action.patch } : item) })
    case 'ITEMS': return change(state, { ...state.present, items: action.items })
    case 'PREFERENCES': return change(state, { ...state.present, preferences: action.preferences })
    case 'APPLY': {
      const activeIds = new Set(action.items.map((item) => item.sectionId))
      const passive = state.present.items.filter((item) => item.role === 'backup' || item.role === 'exclude')
      return change(state, { ...state.present, items: [...action.items, ...passive.filter((item) => !activeIds.has(item.sectionId))] })
    }
    case 'UNDO': {
      const previous = state.past.at(-1)
      if (!previous) return state
      return { past: state.past.slice(0, -1), present: previous, future: [state.present, ...state.future] }
    }
    case 'REDO': {
      const next = state.future[0]
      if (!next) return state
      return { past: [...state.past, state.present], present: next, future: state.future.slice(1) }
    }
    case 'CLEAR': return change(state, { ...emptyDraft(), semester: state.present.semester, dataVersion: state.present.dataVersion })
  }
}

export function planItemsForCandidate(
  sectionIds: readonly string[],
  currentItems: readonly PlanItem[],
  sectionById: ReadonlyMap<string, Section>,
): PlanItem[] {
  const currentById = new Map(currentItems.map((item) => [item.sectionId, item]))
  const mustCourseCodes = new Set(currentItems
    .filter((item) => item.role === 'must')
    .map((item) => sectionById.get(item.sectionId)?.courseCode)
    .filter((value): value is string => !!value))
  return sectionIds.map((sectionId) => {
    const current = currentById.get(sectionId)
    const courseCode = sectionById.get(sectionId)?.courseCode
    return {
      sectionId,
      role: courseCode && mustCourseCodes.has(courseCode) ? 'must' : 'want',
      locked: current?.locked ?? false,
    }
  })
}

export function itemsWithCourseRole(
  sectionId: string,
  role: PlanItem['role'],
  currentItems: readonly PlanItem[],
  sectionById: ReadonlyMap<string, Section>,
): PlanItem[] {
  const courseCode = sectionById.get(sectionId)?.courseCode
  if (!courseCode) return [...currentItems]
  if (role === 'exclude') {
    return [
      ...currentItems.filter((item) => sectionById.get(item.sectionId)?.courseCode !== courseCode),
      { sectionId, role, locked: false },
    ]
  }
  const withoutCourseExclusion = currentItems.filter((item) => !(item.role === 'exclude' && sectionById.get(item.sectionId)?.courseCode === courseCode))
  const isActiveRole = role === 'must' || role === 'want'
  const next = withoutCourseExclusion.map<PlanItem>((item) => {
    if (item.sectionId === sectionId) return { ...item, role, locked: isActiveRole && item.locked }
    if (isActiveRole && sectionById.get(item.sectionId)?.courseCode === courseCode && (item.role === 'must' || item.role === 'want')) {
      return { ...item, role: 'backup', locked: false }
    }
    return item
  })
  return next.some((item) => item.sectionId === sectionId) ? next : [...next, { sectionId, role, locked: false }]
}

export function itemsWithAppliedBackup(
  sectionId: string,
  currentItems: readonly PlanItem[],
  sectionById: ReadonlyMap<string, Section>,
): PlanItem[] {
  const courseCode = sectionById.get(sectionId)?.courseCode
  if (!courseCode) return [...currentItems]
  const active = currentItems.find((item) => item.sectionId !== sectionId
    && sectionById.get(item.sectionId)?.courseCode === courseCode
    && (item.role === 'must' || item.role === 'want'))
  return currentItems.map((item) => {
    if (item.sectionId === sectionId) return { ...item, role: active?.role ?? 'want', locked: active?.locked ?? false }
    if (item.sectionId === active?.sectionId) return { ...item, role: 'backup', locked: false }
    return item
  })
}

export function loadSavedDraft(): DraftSnapshot {
  const query = new URLSearchParams(location.search).get('plan')
  if (query) {
    const parsed = decodeDraft(query)
    if (parsed) return parsed
  }
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem('pl-timetabler:draft:v1') ?? 'null')
    const normalized = normalizeDraftSnapshot(parsed)
    if (normalized) return normalized
  } catch { /* corrupted storage starts safely */ }
  return emptyDraft()
}
