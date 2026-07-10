import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it } from 'vitest'
import { DEFAULT_PREFERENCES } from '../domain/draftSchema'
import type { Preferences } from '../types'
import { PreferencesPanel } from './PreferencesPanel'

afterEach(cleanup)

function Harness({ initial = { ...DEFAULT_PREFERENCES, preferredFreeDays: [] } }: { initial?: Preferences }) {
  const [preferences, setPreferences] = useState<Preferences>(initial)
  return <PreferencesPanel preferences={preferences} onChange={setPreferences} />
}

describe('optimizer credit preferences', () => {
  it('keeps minimum, target and maximum in an API-valid interval', () => {
    render(<Harness />)
    fireEvent.click(screen.getByText('세부 조건 조정'))
    fireEvent.change(screen.getByRole('spinbutton', { name: '최대 학점' }), { target: { value: '12' } })
    expect(screen.getByRole('spinbutton', { name: '최소 학점' })).toHaveValue(12)
    expect(screen.getByRole('spinbutton', { name: '목표 학점' })).toHaveValue(12)
    fireEvent.change(screen.getByRole('spinbutton', { name: '목표 학점' }), { target: { value: '24' } })
    expect(screen.getByRole('spinbutton', { name: '최대 학점' })).toHaveValue(24)
  })
})

describe('student-language preference presets', () => {
  it('keeps target credits and free days visible while low-level controls stay in advanced settings', () => {
    render(<Harness />)

    expect(screen.getByRole('spinbutton', { name: '목표 학점' })).toBeVisible()
    expect(screen.getByRole('group', { name: '공강을 원하는 요일' })).toBeVisible()
    expect(screen.getByText('세부 조건 조정').closest('details')).not.toHaveAttribute('open')

    fireEvent.click(screen.getByText('세부 조건 조정'))
    expect(screen.getByRole('spinbutton', { name: '최소 학점' })).toBeVisible()
    expect(screen.getByRole('slider', { name: /빈 시간 줄이기/ })).toBeVisible()
  })

  it('applies understandable presets without overwriting credits or preferred free days', () => {
    render(<Harness initial={{ ...DEFAULT_PREFERENCES, targetCredits: 20, minCredits: 18, maxCredits: 24, preferredFreeDays: ['금'] }} />)

    fireEvent.click(screen.getByRole('button', { name: '오전 수업 피하기' }))
    expect(screen.getByRole('button', { name: '오전 수업 피하기' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('spinbutton', { name: '목표 학점' })).toHaveValue(20)
    expect(screen.getByRole('checkbox', { name: '금' })).toBeChecked()

    fireEvent.click(screen.getByText('세부 조건 조정'))
    expect(screen.getByLabelText('이 시간 전 피하기')).toHaveValue('10:30')
    expect(screen.getByRole('spinbutton', { name: '최소 학점' })).toHaveValue(18)
    expect(screen.getByRole('spinbutton', { name: '최대 학점' })).toHaveValue(24)
  })

  it('offers compact and free-day priorities as distinct practical choices', () => {
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: '수업 몰아서' }))
    fireEvent.click(screen.getByText('세부 조건 조정'))
    expect(screen.getByRole('slider', { name: /빈 시간 줄이기/ })).toHaveValue('100')
    expect(screen.getByRole('checkbox', { name: /현재 선택을 최대한 유지/ })).not.toBeChecked()

    fireEvent.click(screen.getByRole('button', { name: '공강일 우선' }))
    expect(screen.getByLabelText('하루 최대 수업')).toHaveValue('480')
  })
})
