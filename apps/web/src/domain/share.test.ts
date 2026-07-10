import { describe, expect, it } from 'vitest'
import { emptyDraft } from '../state/draft'
import { decodeDraft, encodeDraft } from './share'

describe('privacy-safe share payload', () => {
  it('round-trips a Unicode draft', () => {
    const draft = { ...emptyDraft(), items: [{ sectionId: '한글-01', role: 'want' as const, locked: false }] }
    expect(decodeDraft(encodeDraft(draft))).toMatchObject({ items: draft.items })
  })
  it('rejects corrupt values', () => expect(decodeDraft('not-json')).toBeNull())
  it('rejects a schema marker without the required draft fields', () => {
    const encoded = btoa(JSON.stringify({ schemaVersion: 1 })).replaceAll('=', '')
    expect(decodeDraft(encoded)).toBeNull()
  })
  it('fills newly added preference fields for an older valid draft', () => {
    const old = { ...emptyDraft(), preferences: { minCredits: 12, maxCredits: 18 } }
    const encoded = btoa(JSON.stringify(old)).replaceAll('=', '')
    expect(decodeDraft(encoded)?.preferences).toMatchObject({ minCredits: 12, maxCredits: 18, targetCredits: 18, compactness: 70, minimizeChanges: true })
  })
  it('normalizes a legacy target into the accepted credit interval', () => {
    const legacy = { ...emptyDraft(), preferences: { ...emptyDraft().preferences, minCredits: 9, maxCredits: 12, targetCredits: 18 } }
    expect(decodeDraft(encodeDraft(legacy))?.preferences.targetCredits).toBe(12)
  })
  it('clears an impossible lock from a legacy passive item', () => {
    const legacy = { ...emptyDraft(), items: [{ sectionId: 'backup-01', role: 'backup' as const, locked: true }] }
    expect(decodeDraft(encodeDraft(legacy))?.items[0]?.locked).toBe(false)
  })
  it('rejects fractional credits that the optimizer API cannot honor exactly', () => {
    const invalid = { ...emptyDraft(), preferences: { ...emptyDraft().preferences, targetCredits: 12.5 } }
    expect(decodeDraft(encodeDraft(invalid))).toBeNull()
  })
})
