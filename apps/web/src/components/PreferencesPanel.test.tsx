import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { DEFAULT_PREFERENCES } from '../domain/draftSchema'
import type { Preferences } from '../types'
import { PreferencesPanel } from './PreferencesPanel'

function Harness() {
  const [preferences, setPreferences] = useState<Preferences>({ ...DEFAULT_PREFERENCES, preferredFreeDays: [] })
  return <PreferencesPanel preferences={preferences} onChange={setPreferences} />
}

describe('optimizer credit preferences', () => {
  it('keeps minimum, target and maximum in an API-valid interval', () => {
    render(<Harness />)
    fireEvent.change(screen.getByRole('spinbutton', { name: '최대 학점' }), { target: { value: '12' } })
    expect(screen.getByRole('spinbutton', { name: '최소 학점' })).toHaveValue(12)
    expect(screen.getByRole('spinbutton', { name: '목표 학점' })).toHaveValue(12)
    fireEvent.change(screen.getByRole('spinbutton', { name: '목표 학점' }), { target: { value: '24' } })
    expect(screen.getByRole('spinbutton', { name: '최대 학점' })).toHaveValue(24)
  })
})
