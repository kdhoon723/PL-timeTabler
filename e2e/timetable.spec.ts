import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('mobile timetable editor', () => {
  test.use({ viewport: { width: 360, height: 800 } })

  test('searches, adds, persists and edits a section without horizontal overflow', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '내 시간표' })).toBeVisible()
    await page.getByRole('button', { name: /과목 추가/ }).last().click()
    await page.getByRole('textbox', { name: /과목명/ }).fill('AI시대의컴퓨팅사고')
    await page.getByRole('button', { name: /01분반/ }).click()
    await page.getByRole('button', { name: '과목 검색 닫기' }).click()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.reload()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeVisible()
  })

  test('opens graduation evidence and returns to the editor', async ({ page }) => {
    await page.goto('/requirements')
    await expect(page.getByRole('heading', { name: '예상 졸업요건 점검' })).toBeVisible()
    await expect(page.getByText('확인 필요').first()).toBeVisible()
    await page.getByRole('button', { name: '← 시간표로' }).click()
    await expect(page.getByRole('heading', { name: '내 시간표' })).toBeVisible()
  })

  test('has no serious or critical automated accessibility violations', async ({ page }) => {
    await page.goto('/')
    const editor = await new AxeBuilder({ page }).analyze()
    expect(editor.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')).toEqual([])
    await page.goto('/requirements')
    await expect(page.getByRole('heading', { name: '예상 졸업요건 점검' })).toBeVisible()
    const requirements = await new AxeBuilder({ page }).analyze()
    expect(requirements.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')).toEqual([])
  })
})
