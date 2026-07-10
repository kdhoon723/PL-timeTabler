import type { DraftSnapshot, PlanItem, Preferences } from '../types'

export const DEFAULT_PREFERENCES: Preferences = {
  targetCredits: 18,
  minCredits: 15,
  maxCredits: 21,
  preferredFreeDays: [],
  avoidBefore: null,
  avoidAfter: null,
  minLunchMinutes: 60,
  maxDailyMinutes: 360,
  compactness: 70,
  minimizeChanges: true,
}

export function emptyDraft(): DraftSnapshot {
  return { schemaVersion: 1, semester: '2026-1', dataVersion: null, items: [], preferences: DEFAULT_PREFERENCES, updatedAt: new Date().toISOString() }
}

export interface HistoryState {
  past: DraftSnapshot[]
  present: DraftSnapshot
  future: DraftSnapshot[]
}

export type DraftAction =
  | { type: 'LOAD'; snapshot: DraftSnapshot }
  | { type: 'ADD'; item: PlanItem }
  | { type: 'REMOVE'; sectionId: string }
  | { type: 'SWAP'; fromId: string; toId: string }
  | { type: 'PATCH_ITEM'; sectionId: string; patch: Partial<Omit<PlanItem, 'sectionId'>> }
  | { type: 'PREFERENCES'; preferences: Preferences }
  | { type: 'APPLY'; sectionIds: string[] }
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
    case 'ADD': {
      const existing = state.present.items.find((item) => item.sectionId === action.item.sectionId)
      if (existing) return state
      return change(state, { ...state.present, items: [...state.present.items, action.item] })
    }
    case 'REMOVE': return change(state, { ...state.present, items: state.present.items.filter((item) => item.sectionId !== action.sectionId) })
    case 'SWAP': return change(state, { ...state.present, items: state.present.items.map((item) => item.sectionId === action.fromId ? { ...item, sectionId: action.toId } : item) })
    case 'PATCH_ITEM': return change(state, { ...state.present, items: state.present.items.map((item) => item.sectionId === action.sectionId ? { ...item, ...action.patch } : item) })
    case 'PREFERENCES': return change(state, { ...state.present, preferences: action.preferences })
    case 'APPLY': {
      const current = new Map(state.present.items.map((item) => [item.sectionId, item]))
      const activeIds = new Set(action.sectionIds)
      const passive = state.present.items.filter((item) => item.role === 'backup' || item.role === 'exclude')
      const active = action.sectionIds.map((sectionId) => current.get(sectionId) ?? { sectionId, role: 'want' as const, locked: false })
      return change(state, { ...state.present, items: [...active, ...passive.filter((item) => !activeIds.has(item.sectionId))] })
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

export function loadSavedDraft(): DraftSnapshot {
  const query = new URLSearchParams(location.search).get('plan')
  if (query) {
    try {
      const binary = atob(query.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - query.length % 4) % 4))
      const parsed = JSON.parse(new TextDecoder().decode(Uint8Array.from(binary, (char) => char.charCodeAt(0)))) as DraftSnapshot
      if (parsed.schemaVersion === 1) return parsed
    } catch { /* fall through */ }
  }
  try {
    const parsed = JSON.parse(localStorage.getItem('pl-timetabler:draft:v1') ?? 'null') as DraftSnapshot | null
    if (parsed?.schemaVersion === 1) return parsed
  } catch { /* corrupted storage starts safely */ }
  return emptyDraft()
}
