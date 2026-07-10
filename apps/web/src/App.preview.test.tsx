import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadCatalog } from './api/client'
import App from './App'
import type { Candidate, Catalog, DraftSnapshot, Section } from './types'

vi.mock('./api/client', async (importOriginal) => ({
  ...await importOriginal<typeof import('./api/client')>(),
  loadCatalog: vi.fn(),
}))

vi.mock('./components/OptimizerPanel', () => ({
  OptimizerPanel: ({ onPreview }: { onPreview: (candidate: Candidate) => void }) => <button type="button" onClick={() => onPreview({
    id: 'candidate-1', rank: 1, status: 'OPTIMAL', sectionIds: ['A-2'], score: 10,
    reasons: ['분반 교체'], unmetPreferences: [], metrics: { credits: 3, campusDays: 1, totalGapMinutes: 0, earliest: '10:30', latest: '12:00', dailyMinutes: {} },
  })}>테스트 후보 미리보기</button>,
}))

const current: Section = { id: 'A-1', courseCode: 'A', sectionCode: '01', name: '알고리즘', professor: '김교수', category: '전공', credits: 3, rawTime: null, sessions: [{ day: '월', start: '09:00', end: '10:30', room: null, building: null }] }
const replacement: Section = { ...current, id: 'A-2', sectionCode: '02', professor: '이교수', sessions: [{ day: '화', start: '10:30', end: '12:00', room: null, building: null }] }
const catalog: Catalog = { schemaVersion: 1, semester: '2026-1', dataVersion: 'test', updatedAt: '2026-07-11', source: { label: 'test', url: 'https://example.test' }, sections: [current, replacement] }

describe('candidate preview integration', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('pl-timetabler:onboarding:v1', 'complete')
    const draft: DraftSnapshot = { schemaVersion: 1, semester: '2026-1', dataVersion: 'test', items: [{ sectionId: current.id, role: 'want', locked: false }], preferences: { targetCredits: 18, minCredits: 15, maxCredits: 21, preferredFreeDays: [], avoidBefore: null, avoidAfter: null, minLunchMinutes: 0, maxDailyMinutes: 480, compactness: 50, minimizeChanges: true }, updatedAt: '2026-07-11T00:00:00Z' }
    localStorage.setItem('pl-timetabler:draft:v1', JSON.stringify(draft))
    history.replaceState({}, '', '/')
    vi.mocked(loadCatalog).mockResolvedValue({ catalog, offline: false })
  })
  afterEach(cleanup)

  it('returns from mobile tools to a non-mutating canvas preview, then applies with undo', async () => {
    render(<App />)
    await screen.findByText('최신 데이터 연결됨')
    fireEvent.click(screen.getByRole('button', { name: /자동 생성/ }))
    expect(screen.getByRole('dialog', { name: '자동 생성과 준비' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '테스트 후보 미리보기' }))

    await waitFor(() => expect(screen.queryByRole('dialog', { name: '자동 생성과 준비' })).not.toBeInTheDocument())
    expect(screen.getByRole('heading', { name: '후보 1 변경 내용' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('region', { name: '후보 1 변경 내용' })).toHaveFocus())
    expect(screen.getByText('교체: 알고리즘 01분반 → 02분반')).toBeInTheDocument()
    expect(screen.getByLabelText(/알고리즘 월.*교체 전 분반/)).toBeInTheDocument()
    expect(screen.getByLabelText(/알고리즘 화.*교체 후 분반/)).toBeInTheDocument()
    expect((JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!) as DraftSnapshot).items[0]?.sectionId).toBe('A-1')

    fireEvent.click(screen.getByRole('button', { name: '후보 적용' }))
    await screen.findByText('자동 생성 후보를 적용했습니다.')
    expect(screen.getByRole('button', { name: '되돌리기' })).toBeInTheDocument()
    await waitFor(() => expect((JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!) as DraftSnapshot).items[0]?.sectionId).toBe('A-2'))
  })
})
