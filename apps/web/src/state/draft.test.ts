import { describe, expect, it } from 'vitest'
import { draftReducer, emptyDraft, type HistoryState } from './draft'

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
    state = draftReducer(state, { type: 'APPLY', sectionIds: ['A-1', 'B-1'] })
    expect(state.present.items.map((item) => item.sectionId)).toEqual(['A-1', 'B-1', 'BACKUP'])
  })
})
