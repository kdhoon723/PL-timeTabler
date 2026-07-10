import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadCatalog } from './api/client'
import App from './App'
import type { Catalog, Section } from './types'

vi.mock('./api/client', async (importOriginal) => ({
  ...await importOriginal<typeof import('./api/client')>(),
  loadCatalog: vi.fn(),
}))

afterEach(cleanup)

describe('catalog hydration', () => {
  beforeEach(() => {
    localStorage.clear()
    history.replaceState({}, '', '/')
  })

  it('does not roll back preferences edited while the initial catalog is loading', async () => {
    let resolveCatalog!: (value: { catalog: Catalog; offline: boolean }) => void
    vi.mocked(loadCatalog).mockReturnValue(new Promise((resolve) => { resolveCatalog = resolve }))
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /자동 생성/ }))
    fireEvent.change(screen.getByRole('spinbutton', { name: '목표 학점' }), { target: { value: '12' } })

    await act(async () => resolveCatalog({
      catalog: { schemaVersion: 1, semester: '2026-1', dataVersion: 'fresh-version', updatedAt: '2026-07-10', source: { label: 'test', url: 'https://example.test' }, sections: [] },
      offline: false,
    }))

    expect(screen.getByRole('spinbutton', { name: '목표 학점' })).toHaveValue(12)
    expect(screen.getByText('최신 데이터 연결됨')).toBeInTheDocument()
  })
})

describe('editor command recovery', () => {
  const section: Section = { id: '922601-01', courseCode: '922601', sectionCode: '01', name: 'AI시대의컴퓨팅사고', professor: '김선경', category: '교양필수', credits: 2, rawTime: null, sessions: [{ day: '화', start: '11:30', end: '13:30', room: null, building: null }] }

  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('pl-timetabler:onboarding:v1', 'complete')
    history.replaceState({}, '', '/')
    vi.mocked(loadCatalog).mockResolvedValue({ catalog: { schemaVersion: 1, semester: '2026-1', dataVersion: 'test', updatedAt: '2026-07-11', source: { label: 'test', url: 'https://example.test' }, sections: [section] }, offline: false })
  })

  async function addSection() {
    render(<App />)
    await screen.findByText('최신 데이터 연결됨')
    fireEvent.click(screen.getAllByRole('button', { name: /과목 추가/ }).at(-1)!)
    fireEvent.click(screen.getByRole('button', { name: /AI시대의컴퓨팅사고.*분반 보기/ }))
    fireEvent.click(screen.getByRole('button', { name: /01분반.*추가/ }))
    expect(screen.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeInTheDocument()
  }

  it('supports Ctrl/Cmd+Z and Shift+Ctrl/Cmd+Z outside editable controls', async () => {
    await addSection()
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true })
    await waitFor(() => expect(screen.queryByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).not.toBeInTheDocument())
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true, shiftKey: true })
    await waitFor(() => expect(screen.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeInTheDocument())
  })

  it('does not attach Undo to unrelated toast messages merely because history exists', async () => {
    await addSection()
    fireEvent.click(screen.getByRole('button', { name: '시간표 공유' }))
    await screen.findByText('공유 링크를 만들지 못했습니다.')
    expect(screen.queryByRole('button', { name: '되돌리기' })).not.toBeInTheDocument()
  })
})
