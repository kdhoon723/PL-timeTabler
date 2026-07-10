import { describe, expect, it } from 'vitest'
import type { Section } from '../types'
import { draftReducer, emptyDraft, itemsWithAppliedBackup, itemsWithCourseRole, loadSavedDraft, planItemsForCandidate, type HistoryState } from './draft'

describe('draft history', () => {
  it('supports add, swap, undo and redo without losing the course role', () => {
    let state: HistoryState = { past: [], present: emptyDraft(), future: [] }
    state = draftReducer(state, { type: 'ADD', item: { sectionId: 'A-1', role: 'must', locked: true } })
    state = draftReducer(state, { type: 'SWAP', fromId: 'A-1', toId: 'A-2' })
    expect(state.present.items[0]).toMatchObject({ sectionId: 'A-2', role: 'must', locked: true })
    state = draftReducer(state, { type: 'UNDO' })
    expect(state.present.items[0]?.sectionId).toBe('A-1')
    state = draftReducer(state, { type: 'REDO' })
    expect(state.present.items[0]?.sectionId).toBe('A-2')
  })
  it('keeps backup items when applying an optimizer candidate', () => {
    let state: HistoryState = { past: [], present: emptyDraft(), future: [] }
    state = draftReducer(state, { type: 'ADD', item: { sectionId: 'BACKUP', role: 'backup', locked: false } })
    state = draftReducer(state, { type: 'APPLY', items: [{ sectionId: 'A-1', role: 'want', locked: false }, { sectionId: 'B-1', role: 'want', locked: false }] })
    expect(state.present.items.map((item) => item.sectionId)).toEqual(['A-1', 'B-1', 'BACKUP'])
  })
  it('promotes an applied backup and preserves a must role across a section change', () => {
    const make = (id: string, courseCode: string): Section => ({ id, courseCode, sectionCode: id.at(-1)!, name: courseCode, professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] })
    const sections = [make('A-1', 'A'), make('A-2', 'A'), make('B-1', 'B')]
    const items = [
      { sectionId: 'A-1', role: 'must' as const, locked: false },
      { sectionId: 'B-1', role: 'backup' as const, locked: false },
    ]
    expect(planItemsForCandidate(['A-2', 'B-1'], items, new Map(sections.map((section) => [section.id, section])))).toEqual([
      { sectionId: 'A-2', role: 'must', locked: false },
      { sectionId: 'B-1', role: 'want', locked: false },
    ])
  })
  it('can clear a lock when an active item becomes a passive role', () => {
    let state: HistoryState = { past: [], present: emptyDraft(), future: [] }
    state = draftReducer(state, { type: 'ADD', item: { sectionId: 'A-1', role: 'want', locked: true } })
    state = draftReducer(state, { type: 'PATCH_ITEM', sectionId: 'A-1', patch: { role: 'exclude', locked: false } })
    expect(state.present.items[0]).toMatchObject({ role: 'exclude', locked: false })
  })
  it('swaps an applied backup with the current section of the same course', () => {
    const make = (id: string): Section => ({ id, courseCode: 'A', sectionCode: id.at(-1)!, name: 'A', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] })
    const sections = [make('A-1'), make('A-2')]
    const items = [{ sectionId: 'A-1', role: 'must' as const, locked: true }, { sectionId: 'A-2', role: 'backup' as const, locked: false }]
    expect(itemsWithAppliedBackup('A-2', items, new Map(sections.map((section) => [section.id, section])))).toEqual([
      { sectionId: 'A-1', role: 'backup', locked: false },
      { sectionId: 'A-2', role: 'must', locked: true },
    ])
  })
  it('makes a course-level exclusion mutually exclusive with its active and backup sections', () => {
    const make = (id: string): Section => ({ id, courseCode: 'A', sectionCode: id.at(-1)!, name: 'A', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] })
    const sections = [make('A-1'), make('A-2')]
    const items = [{ sectionId: 'A-1', role: 'want' as const, locked: false }, { sectionId: 'A-2', role: 'backup' as const, locked: false }]
    expect(itemsWithCourseRole('A-2', 'exclude', items, new Map(sections.map((section) => [section.id, section])))).toEqual([
      { sectionId: 'A-2', role: 'exclude', locked: false },
    ])
  })
  it('hydrates a catalog against the reducer current state without erasing edit history', () => {
    let state: HistoryState = { past: [], present: emptyDraft(), future: [] }
    state = draftReducer(state, { type: 'PREFERENCES', preferences: { ...state.present.preferences, targetCredits: 12, minCredits: 12 } })
    state = draftReducer(state, { type: 'CATALOG', dataVersion: 'fresh', validIds: new Set() })
    expect(state.present.preferences.targetCredits).toBe(12)
    state = draftReducer(state, { type: 'UNDO' })
    expect(state.present.dataVersion).toBe('fresh')
    expect(state.present.preferences.targetCredits).toBe(18)
  })
  it('ignores malformed local storage instead of crashing the editor', () => {
    localStorage.setItem('pl-timetabler:draft:v1', JSON.stringify({ schemaVersion: 1 }))
    expect(loadSavedDraft().items).toEqual([])
    localStorage.removeItem('pl-timetabler:draft:v1')
  })
  it('ignores an incomplete shared plan instead of crashing the editor', () => {
    const malformed = btoa(JSON.stringify({ schemaVersion: 1 })).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')
    history.replaceState({}, '', `/?plan=${malformed}`)
    expect(loadSavedDraft().items).toEqual([])
    history.replaceState({}, '', '/')
  })
})
