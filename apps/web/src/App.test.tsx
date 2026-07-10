import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { loadCatalog } from './api/client'
import App from './App'
import type { Catalog } from './types'

vi.mock('./api/client', async (importOriginal) => ({
  ...await importOriginal<typeof import('./api/client')>(),
  loadCatalog: vi.fn(),
}))

describe('catalog hydration', () => {
  beforeEach(() => {
    localStorage.clear()
    history.replaceState({}, '', '/')
  })

  it('does not roll back preferences edited while the initial catalog is loading', async () => {
    let resolveCatalog!: (value: { catalog: Catalog; offline: boolean }) => void
    vi.mocked(loadCatalog).mockReturnValue(new Promise((resolve) => { resolveCatalog = resolve }))
    render(<App />)
    fireEvent.change(screen.getByRole('spinbutton', { name: '목표 학점' }), { target: { value: '12' } })

    await act(async () => resolveCatalog({
      catalog: { schemaVersion: 1, semester: '2026-1', dataVersion: 'fresh-version', updatedAt: '2026-07-10', source: { label: 'test', url: 'https://example.test' }, sections: [] },
      offline: false,
    }))

    expect(screen.getByRole('spinbutton', { name: '목표 학점' })).toHaveValue(12)
    expect(screen.getByText('최신 데이터 연결됨')).toBeInTheDocument()
  })
})
