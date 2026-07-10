import { describe, expect, it } from 'vitest'
import { emptyDraft } from '../state/draft'
import type { DraftSnapshot, Preferences } from '../types'
import { optimizationDraftFingerprint } from './optimizationDraft'

describe('optimization draft fingerprint', () => {
  const base: DraftSnapshot = {
    ...emptyDraft(),
    dataVersion: 'catalog-v1',
    items: [
      { sectionId: 'B-1', role: 'want', locked: false },
      { sectionId: 'A-1', role: 'must', locked: true },
    ],
    preferences: {
      ...emptyDraft().preferences,
      preferredFreeDays: ['수', '월'],
    },
    updatedAt: '2026-07-11T00:00:00.000Z',
  }

  it('is stable across timestamps and semantically irrelevant collection order', () => {
    expect(optimizationDraftFingerprint({
      ...base,
      items: [...base.items].reverse(),
      preferences: { ...base.preferences, preferredFreeDays: ['월', '수'] },
      updatedAt: '2099-01-01T00:00:00.000Z',
    })).toBe(optimizationDraftFingerprint(base))
  })

  it('changes for semester, catalog version, item section/role/lock, and every preference', () => {
    const fingerprint = optimizationDraftFingerprint(base)
    const changedPreferences: Preferences[] = [
      { ...base.preferences, targetCredits: base.preferences.targetCredits + 1 },
      { ...base.preferences, minCredits: base.preferences.minCredits - 1 },
      { ...base.preferences, maxCredits: base.preferences.maxCredits + 1 },
      { ...base.preferences, preferredFreeDays: ['화'] },
      { ...base.preferences, avoidBefore: '09:00' },
      { ...base.preferences, avoidAfter: '18:00' },
      { ...base.preferences, minLunchMinutes: base.preferences.minLunchMinutes + 30 },
      { ...base.preferences, maxDailyMinutes: base.preferences.maxDailyMinutes - 60 },
      { ...base.preferences, compactness: base.preferences.compactness - 10 },
      { ...base.preferences, minimizeChanges: !base.preferences.minimizeChanges },
    ]
    const changedDrafts: DraftSnapshot[] = [
      { ...base, semester: '2026-2' },
      { ...base, dataVersion: 'catalog-v2' },
      { ...base, items: base.items.map((item, index) => index === 0 ? { ...item, sectionId: 'B-2' } : item) },
      { ...base, items: base.items.map((item, index) => index === 0 ? { ...item, role: 'backup' } : item) },
      { ...base, items: base.items.map((item, index) => index === 0 ? { ...item, locked: true } : item) },
      ...changedPreferences.map((preferences) => ({ ...base, preferences })),
    ]

    for (const draft of changedDrafts) expect(optimizationDraftFingerprint(draft)).not.toBe(fingerprint)
  })
})
