import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AcademicProfile, DepartmentSource } from '../types'
import { Onboarding } from './Onboarding'

afterEach(cleanup)

const department = { academicUnit: '컴퓨터공학전공', college: 'AI융합대학' } as DepartmentSource
const profile: AcademicProfile = {
  schemaVersion: 2,
  department: department.academicUnit,
  currentGrade: 3,
  academicBasis: { admissionYear: 2026, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN' },
  updatedAt: '2026-07-11T00:00:00.000Z',
}

describe('progressive academic profile setup', () => {
  it('saves only department and grade for a regular first-run student', async () => {
    const onComplete = vi.fn()
    render(<Onboarding departments={[department]} initialProfile={null} mode="FIRST_RUN" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)
    await userEvent.click(screen.getByRole('button', { name: '학과 선택하고 시작' }))
    await userEvent.click(screen.getByRole('option', { name: /컴퓨터공학전공/ }))
    await userEvent.click(screen.getByRole('button', { name: '3학년' }))

    expect(screen.queryByText('신입학')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: /입학연도/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '3학년 시간표 만들기' }))
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ currentGrade: 3, academicBasis: null }))
  })

  it('reveals transfer-only guidance and year after the small transfer choice', async () => {
    render(<Onboarding departments={[department]} initialProfile={null} mode="FIRST_RUN" authAvailable={false} onComplete={() => undefined} onSkip={() => undefined} onLogin={() => undefined} />)
    await userEvent.click(screen.getByRole('button', { name: '학과 선택하고 시작' }))
    await userEvent.click(screen.getByRole('option', { name: /컴퓨터공학전공/ }))
    const transfer = screen.getByRole('checkbox', { name: /혹시 편입생인가요/ })
    expect(screen.queryByText('편입 기준으로 안내할게요')).not.toBeInTheDocument()
    await userEvent.click(transfer)
    expect(transfer).toBeChecked()
    expect(screen.getByText('편입 기준으로 안내할게요')).toBeVisible()
    expect(screen.getByRole('combobox', { name: /대진대 편입학년도/ })).toBeVisible()
  })

  it('opens an existing basic profile directly at optional academic-basis settings', async () => {
    render(<Onboarding departments={[department]} initialProfile={{ ...profile, academicBasis: null }} mode="EDIT" authAvailable={false} onComplete={() => undefined} onSkip={() => undefined} onLogin={() => undefined} />)
    expect(screen.getByRole('heading', { name: /몇 학년 시간표를 준비할까요/ })).toBeVisible()
    expect(screen.queryByRole('option', { name: /컴퓨터공학전공/ })).not.toBeInTheDocument()
    const precision = screen.getByRole('checkbox', { name: /필수과목 추천을 더 정확히/ })
    expect(precision).not.toBeChecked()
    await userEvent.click(precision)
    expect(screen.getByRole('combobox', { name: /입학연도/ })).toBeVisible()
    expect(screen.getByRole('checkbox', { name: /혹시 편입생인가요/ })).toBeVisible()
  })

  it('keeps accelerated academic-basis data for manual review without authorizing it', async () => {
    const onComplete = vi.fn()
    render(<Onboarding departments={[department]} initialProfile={profile} mode="EDIT" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)
    expect(screen.getByRole('alert')).toHaveTextContent('보통 1학년')
    expect(screen.queryByRole('checkbox', { name: /현재 3학년이 맞습니다/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '설정 저장' }))
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ academicBasis: expect.objectContaining({ admissionYear: 2026, gradeMismatchAcknowledged: undefined }) }))
  })

  it('requires acknowledgement for delayed progression and records it inside the basis', async () => {
    const onComplete = vi.fn()
    render(<Onboarding departments={[department]} initialProfile={{ ...profile, currentGrade: 1, academicBasis: { ...profile.academicBasis!, admissionYear: 2024 } }} mode="EDIT" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)
    expect(screen.getByRole('button', { name: '설정 저장' })).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox', { name: /현재 1학년이 맞습니다/ }))
    await userEvent.click(screen.getByRole('button', { name: '설정 저장' }))
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ academicBasis: expect.objectContaining({ gradeMismatchAcknowledged: true }) }))
  })

  it('does not require a progression acknowledgement for transfer entry', async () => {
    const onComplete = vi.fn()
    const transfer = { ...profile, academicBasis: { ...profile.academicBasis!, entryType: 'TRANSFER' as const } }
    render(<Onboarding departments={[department]} initialProfile={transfer} mode="EDIT" authAvailable={false} onComplete={onComplete} onSkip={() => undefined} onLogin={() => undefined} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /혹시 편입생인가요/ })).toBeChecked()
    await userEvent.click(screen.getByRole('button', { name: '설정 저장' }))
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ academicBasis: expect.objectContaining({ entryType: 'TRANSFER' }) }))
  })
})
