import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadCatalog } from './api/client'
import App from './App'
import type { Candidate, Catalog, DraftSnapshot, Section } from './types'

vi.mock('./api/client', async (importOriginal) => ({
  ...await importOriginal<typeof import('./api/client')>(),
  loadCatalog: vi.fn(),
}))

vi.mock('./components/OptimizerPanel', () => ({
  OptimizerPanel: ({ onPreview, draftFingerprint }: { onPreview: (candidate: Candidate, fingerprint: string) => void; draftFingerprint: string }) => <>
    <button type="button" onClick={() => onPreview({
      id: 'candidate-1', rank: 1, status: 'OPTIMAL', sectionIds: ['A-2', 'B-1'], score: 10,
      reasons: ['분반 교체'], unmetPreferences: [], metrics: { credits: 6, campusDays: 2, totalGapMinutes: 30, earliest: '10:30', latest: '15:00', dailyMinutes: {} },
    }, draftFingerprint)}>테스트 후보 미리보기</button>
    <button type="button" onClick={() => onPreview({
      id: 'candidate-stale', rank: 2, status: 'OPTIMAL', sectionIds: ['A-2'], score: 9,
      reasons: [], unmetPreferences: [], metrics: { credits: 3, campusDays: 1, totalGapMinutes: 0, earliest: '10:30', latest: '12:00', dailyMinutes: {} },
    }, 'stale-generation')}>오래된 테스트 후보 미리보기</button>
    <button type="button" onClick={() => onPreview({
      id: 'candidate-removes-new', rank: 3, status: 'OPTIMAL', sectionIds: ['A-2'], score: 8,
      reasons: [], unmetPreferences: [], metrics: { credits: 3, campusDays: 1, totalGapMinutes: 0, earliest: '10:30', latest: '12:00', dailyMinutes: {} },
    }, draftFingerprint)}>새 필수과목 없는 후보 미리보기</button>
  </>,
}))

const current: Section = { id: 'A-1', courseCode: 'A', sectionCode: '01', name: '알고리즘', professor: '김교수', category: '전공', credits: 3, rawTime: null, sessions: [{ day: '월', start: '09:00', end: '10:30', room: null, building: null }] }
const replacement: Section = { ...current, id: 'A-2', sectionCode: '02', professor: '이교수', sessions: [{ day: '화', start: '10:30', end: '12:00', room: null, building: null }] }
const added: Section = { id: 'B-1', courseCode: 'B', sectionCode: '01', name: '운영체제', professor: '박교수', category: '전공', credits: 3, rawTime: null, sessions: [{ day: '화', start: '11:00', end: '12:30', room: null, building: null }] }
const catalog: Catalog = { schemaVersion: 1, semester: '2026-1', dataVersion: 'test', updatedAt: '2026-07-11', source: { label: 'test', url: 'https://example.test' }, sections: [current, replacement, added] }

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
    await screen.findByRole('button', { name: /알고리즘 월/ })
    fireEvent.click(screen.getByRole('button', { name: /자동완성/ }))
    expect(screen.getByRole('dialog', { name: '자동완성' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '테스트 후보 미리보기' }))

    await waitFor(() => expect(screen.queryByRole('dialog', { name: '자동완성' })).not.toBeInTheDocument())
    expect(screen.getByRole('heading', { name: '후보 1 변경 내용' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('region', { name: '후보 1 변경 내용' })).toHaveFocus())
    expect(screen.getByText('교체: 알고리즘 01분반 → 02분반')).toBeInTheDocument()
    const candidateMetrics = within(screen.getByLabelText('후보 시간표 요약'))
    expect(candidateMetrics.getByText('등교일')).toBeInTheDocument()
    expect(candidateMetrics.getByText('2일')).toBeInTheDocument()
    expect(candidateMetrics.getByText('학점')).toBeInTheDocument()
    expect(candidateMetrics.getByText('6학점')).toBeInTheDocument()
    expect(candidateMetrics.getByText('빈 시간')).toBeInTheDocument()
    expect(candidateMetrics.getByText('30분')).toBeInTheDocument()
    expect(candidateMetrics.getByText('첫 수업')).toBeInTheDocument()
    expect(candidateMetrics.getByText('10:30')).toBeInTheDocument()
    expect(candidateMetrics.getByText('마지막 수업')).toBeInTheDocument()
    expect(candidateMetrics.getByText('15:00')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '내 시간표' }).parentElement).toHaveTextContent('2개 분반')
    expect(screen.getByText(/미리보기에서는 충돌만 확인/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '해결' })).not.toBeInTheDocument()
    expect(screen.getByLabelText(/알고리즘 월.*교체 전 분반/)).toBeInTheDocument()
    expect(screen.getByLabelText(/알고리즘 화.*교체 후 분반/)).toBeInTheDocument()
    expect((JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!) as DraftSnapshot).items[0]?.sectionId).toBe('A-1')

    fireEvent.click(screen.getByRole('button', { name: '후보 적용' }))
    await screen.findByText('자동 생성 후보를 적용했습니다.')
    expect(screen.getByRole('button', { name: '되돌리기' })).toBeInTheDocument()
    await waitFor(() => expect((JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!) as DraftSnapshot).items[0]?.sectionId).toBe('A-2'))
  })

  it('independently rejects a result generated for a different draft', async () => {
    render(<App />)
    await screen.findByRole('button', { name: /알고리즘 월/ })
    fireEvent.click(screen.getByRole('button', { name: /자동완성/ }))
    fireEvent.click(screen.getByRole('button', { name: '오래된 테스트 후보 미리보기' }))

    expect(screen.queryByRole('heading', { name: '후보 2 변경 내용' })).not.toBeInTheDocument()
    expect(await screen.findByText(/조건이 바뀌어 이 후보를 미리 볼 수 없습니다/)).toBeInTheDocument()
    expect((JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!) as DraftSnapshot).items).toEqual([{ sectionId: 'A-1', role: 'want', locked: false, professorLocked: false }])
  })

  it('invalidates an open preview when a current course is added and never applies the old result', async () => {
    render(<App />)
    await screen.findByRole('button', { name: /알고리즘 월/ })
    fireEvent.click(screen.getByRole('button', { name: /자동완성/ }))
    fireEvent.click(screen.getByRole('button', { name: '새 필수과목 없는 후보 미리보기' }))
    await screen.findByRole('heading', { name: '후보 3 변경 내용' })

    fireEvent.click(screen.getAllByRole('button', { name: /과목 추가/ }).at(-1)!)
    fireEvent.click(screen.getByRole('button', { name: /운영체제.*분반 보기/ }))
    fireEvent.click(screen.getByRole('button', { name: /01분반.*추가/ }))
    fireEvent.click(screen.getByRole('button', { name: '과목 검색 닫기' }))
    fireEvent.click(screen.getByRole('button', { name: /운영체제 화/ }))
    fireEvent.click(screen.getByRole('radio', { name: '꼭 포함' }))
    fireEvent.click(screen.getByRole('radio', { name: '현재 수업' }))

    await waitFor(() => expect(screen.queryByRole('button', { name: '후보 적용' })).not.toBeInTheDocument())
    const saved = JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!) as DraftSnapshot
    expect(saved.items).toEqual(expect.arrayContaining([
      { sectionId: 'A-1', role: 'want', locked: false, professorLocked: false },
      { sectionId: 'B-1', role: 'must', locked: true, professorLocked: false },
    ]))
    expect(saved.items.some((item) => item.sectionId === 'A-2')).toBe(false)
  })
})
