import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CourseEntryPanel } from './CourseEntryPanel'

const profile = { schemaVersion: 2 as const, department: '컴퓨터공학전공', currentGrade: 3 as const, academicBasis: null, updatedAt: '2026-07-11T00:00:00Z' }

afterEach(cleanup)

describe('course entry panel', () => {
  it('keeps one primary course search action and separates required-course guidance', async () => {
    const onRequired = vi.fn()
    const onSearch = vi.fn()
    render(<CourseEntryPanel profile={profile} onRequired={onRequired} onEditProfile={() => undefined} onSearch={onSearch} />)

    await userEvent.click(screen.getByRole('button', { name: '필수과목 확인' }))
    await userEvent.click(screen.getByRole('button', { name: '과목 찾기' }))

    expect(onRequired).toHaveBeenCalledOnce()
    expect(onSearch).toHaveBeenCalledOnce()
    expect(screen.queryByRole('button', { name: '내 전공' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '교양선택' })).not.toBeInTheDocument()
  })

  it('offers a quiet department setup prompt instead of an unavailable recommendation', async () => {
    const onEditProfile = vi.fn()
    render(<CourseEntryPanel profile={null} onRequired={() => undefined} onEditProfile={onEditProfile} onSearch={() => undefined} />)
    await userEvent.click(screen.getByRole('button', { name: '학과를 설정하면 필수과목을 안내해요' }))
    expect(onEditProfile).toHaveBeenCalledOnce()
    expect(screen.queryByRole('button', { name: '필수과목 확인' })).not.toBeInTheDocument()
  })
})
