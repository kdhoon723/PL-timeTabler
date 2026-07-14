import { afterEach, describe, expect, it, vi } from 'vitest'
import { emptyDraft } from '../state/draft'
import type { Section } from '../types'
import { createOptimizationJob, startEmailOtp } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('optimizer API request mapping', () => {
  it('sends effective scoring preferences and never locks passive items', async () => {
    const sections: Section[] = [
      { id: 'A-1', courseCode: 'A', sectionCode: '1', name: 'A', professor: '김교수', category: '전공', credits: 3, rawTime: null, sessions: [] },
      { id: 'B-1', courseCode: 'B', sectionCode: '1', name: 'B', professor: null, category: '전공', credits: 3, rawTime: null, sessions: [] },
    ]
    const draft = {
      ...emptyDraft(),
      dataVersion: 'version',
      items: [
        { sectionId: 'A-1', role: 'want' as const, locked: false, professorLocked: true },
        { sectionId: 'B-1', role: 'backup' as const, locked: true },
      ],
      preferences: {
        ...emptyDraft().preferences,
        minCredits: 3,
        maxCredits: 6,
        targetCredits: 6,
        excludedDays: ['금' as const],
        hardStart: '09:00',
        hardEnd: '18:00',
        maxGapMinutes: 60,
        compactness: 90,
        minimizeChanges: false,
      },
    }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'job', status: 'QUEUED' }), { status: 202, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await createOptimizationJob(draft, sections)

    const body = JSON.parse(String((fetchMock.mock.calls[0]?.[1] as RequestInit).body)) as Record<string, unknown>
    expect(body).toMatchObject({ targetCredits: 6, lockedSectionIds: [], professorConstraints: [{ courseCode: 'A', professor: '김교수' }] })
    expect(body.preferences).toMatchObject({
      excludedDays: ['금'],
      hardStartMinute: 540,
      hardEndMinute: 1080,
      maxGapMinutes: 60,
      gapWeightPercent: 90,
      minimizeChanges: false,
    })
  })
})

describe('school email auth request mapping', () => {
  it('sends only the numeric student number and keeps the session cookie same-origin', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: 'accepted' }), { status: 202, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await startEmailOtp('20260001')

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/otp/start', expect.objectContaining({
      method: 'POST',
      credentials: 'same-origin',
      body: JSON.stringify({ studentNumber: '20260001' }),
    }))
  })
})
