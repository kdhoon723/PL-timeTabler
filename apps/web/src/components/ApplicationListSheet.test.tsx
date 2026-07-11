import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PlanItem, Section } from '../types'
import { ApplicationListSheet } from './ApplicationListSheet'

afterEach(cleanup)

const sections: Section[] = [
  { id: '561041-01', courseCode: '561041', sectionCode: '01', name: '운영체제론', professor: '김교수', category: '전공', credits: 3, rawTime: null, sessions: [] },
  { id: '561042-02', courseCode: '561042', sectionCode: '02', name: '데이터베이스', professor: '박교수', category: '전공', credits: 3, rawTime: null, sessions: [] },
]
const items: PlanItem[] = [
  { sectionId: '561041-01', role: 'want', locked: false },
  { sectionId: '561042-02', role: 'backup', locked: false },
]

describe('application list sheet', () => {
  it('keeps final codes, backups, and export actions together outside automatic generation', async () => {
    const onClose = vi.fn()
    render(<ApplicationListSheet open items={items} sectionById={new Map(sections.map((section) => [section.id, section]))} onApplyBackup={() => undefined} onMessage={() => undefined} onExportPng={() => undefined} onExportPdf={() => undefined} onClose={onClose} />)

    expect(screen.getByRole('dialog', { name: '신청 목록' })).toBeVisible()
    expect(screen.getByText('561041-01')).toBeInTheDocument()
    expect(screen.getByText('예비 과목')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '과목코드·분반 복사' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'PNG 저장' })).toBeVisible()
    expect(screen.getByRole('button', { name: '인쇄·PDF' })).toBeVisible()

    await userEvent.click(screen.getByRole('button', { name: '신청 목록 닫기' }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
