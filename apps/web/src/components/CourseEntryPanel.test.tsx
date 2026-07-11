import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CourseEntryPanel } from './CourseEntryPanel'

afterEach(cleanup)

describe('course entry panel', () => {
  it('routes each course job to one predictable entry point', async () => {
    const onRequired = vi.fn()
    const onMajor = vi.fn()
    const onLiberal = vi.fn()
    const onAll = vi.fn()
    render(<CourseEntryPanel hasProfile onRequired={onRequired} onMajor={onMajor} onLiberal={onLiberal} onAll={onAll} />)

    await userEvent.click(screen.getByRole('button', { name: '필수 추천' }))
    await userEvent.click(screen.getByRole('button', { name: '내 전공' }))
    await userEvent.click(screen.getByRole('button', { name: '교양' }))
    await userEvent.click(screen.getByRole('button', { name: '전체 과목 추가' }))

    expect(onRequired).toHaveBeenCalledOnce()
    expect(onMajor).toHaveBeenCalledOnce()
    expect(onLiberal).toHaveBeenCalledOnce()
    expect(onAll).toHaveBeenCalledOnce()
  })

  it('turns the major shortcut into an actionable department setup when needed', async () => {
    const onMajor = vi.fn()
    render(<CourseEntryPanel hasProfile={false} onRequired={() => undefined} onMajor={onMajor} onLiberal={() => undefined} onAll={() => undefined} />)
    await userEvent.click(screen.getByRole('button', { name: '학과 설정' }))
    expect(onMajor).toHaveBeenCalledOnce()
  })
})
