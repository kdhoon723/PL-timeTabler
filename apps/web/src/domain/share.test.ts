import { describe, expect, it } from 'vitest'
import { emptyDraft } from '../state/draft'
import { decodeDraft, encodeDraft } from './share'

describe('privacy-safe share payload', () => {
  it('round-trips a Unicode draft', () => {
    const draft = { ...emptyDraft(), items: [{ sectionId: '한글-01', role: 'want' as const, locked: false }] }
    expect(decodeDraft(encodeDraft(draft))).toMatchObject({ items: draft.items })
  })
  it('rejects corrupt values', () => expect(decodeDraft('not-json')).toBeNull())
})
