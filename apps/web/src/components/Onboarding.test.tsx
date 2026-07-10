import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AcademicProfile, DepartmentSource } from '../types'
import { Onboarding } from './Onboarding'

afterEach(cleanup)

const department = { academicUnit: '컴퓨터공학전공', college: 'AI융합대학' } as DepartmentSource
const profile: AcademicProfile = {
  schemaVersion: 1,
  department: department.academicUnit,
  admissionYear: 2026,
  currentGrade: 3,
  entryType: 'FRESHMAN',
  studentType: 'DOMESTIC',
  sectionGroup: 'UNKNOWN',
  updatedAt: '2026-07-11T00:00:00.000Z',
}

describe('academic profile consistency safeguard', () => {
  it('allows saving accelerated progression but requires department confirmation for automatic requirements', async () => {
    const onComplete = vi.fn()
    render(<Onboarding departments={[department]} initialProfile={profile} mode="EDIT" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)

    await userEvent.click(screen.getByRole('option', { name: /컴퓨터공학전공/ }))
    expect(screen.getByRole('alert')).toHaveTextContent('2026학년도 1학기 기준')
    expect(screen.getByRole('alert')).toHaveTextContent('보통 1학년')
    expect(screen.getByRole('alert')).toHaveTextContent('학과 확인 전에는 필수과목을 자동 판정하지 않습니다')
    expect(screen.queryByRole('checkbox', { name: /현재 3학년이 맞습니다/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '시간표 만들기' })).toBeEnabled()
    await userEvent.click(screen.getByRole('button', { name: '시간표 만들기' }))

    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ currentGrade: 3, gradeMismatchAcknowledged: undefined }))
  })

  it('requires acknowledgement for delayed progression and records it', async () => {
    const onComplete = vi.fn()
    render(<Onboarding departments={[department]} initialProfile={{ ...profile, admissionYear: 2024, currentGrade: 1 }} mode="EDIT" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)

    await userEvent.click(screen.getByRole('option', { name: /컴퓨터공학전공/ }))
    expect(screen.getByRole('button', { name: '시간표 만들기' })).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox', { name: /현재 1학년이 맞습니다/ }))
    await userEvent.click(screen.getByRole('button', { name: '시간표 만들기' }))

    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ currentGrade: 1, gradeMismatchAcknowledged: true }))
  })

  it('does not require an acknowledgement for transfer entry', async () => {
    const onComplete = vi.fn()
    render(<Onboarding departments={[department]} initialProfile={{ ...profile, entryType: 'TRANSFER' }} mode="EDIT" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)

    await userEvent.click(screen.getByRole('option', { name: /컴퓨터공학전공/ }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '시간표 만들기' }))

    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ entryType: 'TRANSFER' }))
  })
})
