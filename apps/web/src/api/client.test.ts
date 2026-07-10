import { afterEach, describe, expect, it, vi } from 'vitest'
import { emptyDraft } from '../state/draft'
import type { Section } from '../types'
import { createOptimizationJob } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('optimizer API request mapping', () => {
  it('sends effective scoring preferences and never locks passive items', async () => {
    const sections: Section[] = [
      { id: 'A-1', courseCode: 'A', sectionCode: '1', name: 'A', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] },
      { id: 'B-1', courseCode: 'B', sectionCode: '1', name: 'B', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] },
    ]
    const draft = {
      ...emptyDraft(),
      dataVersion: 'version',
      items: [
        { sectionId: 'A-1', role: 'want' as const, locked: true },
        { sectionId: 'B-1', role: 'backup' as const, locked: true },
      ],
      preferences: { ...emptyDraft().preferences, minCredits: 3, maxCredits: 6, targetCredits: 6, compactness: 90, minimizeChanges: false },
    }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'job', status: 'QUEUED' }), { status: 202, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await createOptimizationJob(draft, sections)

    const body = JSON.parse(String((fetchMock.mock.calls[0]?.[1] as RequestInit).body)) as Record<string, unknown>
    expect(body).toMatchObject({ targetCredits: 6, lockedSectionIds: ['A-1'] })
    expect(body.preferences).toMatchObject({ gapWeightPercent: 90, minimizeChanges: false })
  })
})
