import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Section } from '../types'
import { SectionDetailSheet } from './SectionDetailSheet'

const section: Section = {
  id: '922601-01',
  courseCode: '922601',
  sectionCode: '01',
  name: 'AI시대의컴퓨팅사고',
  professor: '김선경',
  category: '교양필수',
  credits: 2,
  rawTime: null,
  sessions: [{ day: '화', start: '11:30', end: '13:20', room: null, building: null }],
}

const sameProfessor = { ...section, id: '922601-05', sectionCode: '05', sessions: [{ ...section.sessions[0]!, day: '목' as const }] }
const otherProfessor = { ...section, id: '922601-02', sectionCode: '02', professor: '박효진' }

afterEach(cleanup)

describe('section detail planning controls', () => {
  it('separates course inclusion from compact professor and section preservation choices', async () => {
    const onRole = vi.fn()
    const onAdjustmentMode = vi.fn()
    const { rerender } = render(<SectionDetailSheet section={section} role="must" locked={false} professorLocked={false} professorLockAvailable alternatives={[sameProfessor, otherProfessor]} onClose={() => undefined} onRole={onRole} onAdjustmentMode={onAdjustmentMode} onRemove={() => undefined} onSwap={() => undefined} />)

    const dialog = screen.getByRole('dialog', { name: section.name })
    expect(within(dialog).getByRole('radio', { name: '꼭 포함' })).toBeChecked()
    expect(within(dialog).queryByText('반드시')).not.toBeInTheDocument()
    expect(within(dialog).queryByText('분반 잠금')).not.toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('radio', { name: '교수 유지' }))
    expect(onAdjustmentMode).toHaveBeenCalledWith('PROFESSOR')

    rerender(<SectionDetailSheet section={section} role="must" locked={false} professorLocked professorLockAvailable alternatives={[sameProfessor, otherProfessor]} onClose={() => undefined} onRole={onRole} onAdjustmentMode={onAdjustmentMode} onRemove={() => undefined} onSwap={() => undefined} />)
    expect(within(dialog).getByText('같은 교수님의 다른 분반')).toBeVisible()
    expect(within(dialog).getByText(/김선경 교수님의 분반 안에서/)).toBeVisible()
    expect(within(dialog).getByText(/05분반/)).toBeVisible()
    expect(within(dialog).queryByText(/02분반/)).not.toBeInTheDocument()
  })

  it('hides professor preservation when the professor has no other section', () => {
    render(<SectionDetailSheet section={section} role="want" locked={false} professorLocked={false} professorLockAvailable={false} alternatives={[]} onClose={() => undefined} onRole={() => undefined} onAdjustmentMode={() => undefined} onRemove={() => undefined} onSwap={() => undefined} />)

    expect(screen.queryByRole('radio', { name: '교수 유지' })).not.toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '현재 수업' })).toBeVisible()
  })
})
