import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'

async function openEditor(page: Page) {
  await page.goto('/')
  const skip = page.getByRole('button', { name: '건너뛰고 바로 만들기' })
  if (await skip.isVisible()) await skip.click()
  await expect(page.getByRole('heading', { name: '내 시간표' })).toBeVisible()
}

test.describe('mobile timetable editor', () => {
  test.use({ viewport: { width: 360, height: 800 } })

  test('keeps first-run focus inside the accessible setup dialog', async ({ page }) => {
    await page.goto('/')
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect.poll(() => page.evaluate(() => {
      const modal = document.querySelector('dialog.onboarding')
      return !!modal && modal.contains(document.activeElement)
    })).toBe(true)
    for (let index = 0; index < 6; index += 1) {
      await page.keyboard.press('Tab')
      expect(await page.evaluate(() => {
        const modal = document.querySelector('dialog.onboarding')
        return !!modal && modal.contains(document.activeElement)
      })).toBe(true)
    }
    const result = await new AxeBuilder({ page }).analyze()
    expect(result.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')).toEqual([])
  })

  test('searches, adds, persists and edits a section without horizontal overflow', async ({ page }) => {
    await openEditor(page)
    await page.getByRole('button', { name: /과목 추가/ }).last().click()
    await page.getByRole('textbox', { name: /과목명/ }).fill('AI시대의컴퓨팅사고')
    await page.getByRole('button', { name: /01분반/ }).click()
    await page.getByRole('button', { name: '과목 검색 닫기' }).click()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.reload()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeVisible()
  })

  test('guides department selection, then places a current-grade required course in the live timetable', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /원하는 시간표/ })).toBeVisible()
    await page.getByRole('button', { name: '학과 선택하고 시작' }).click()
    await page.getByRole('textbox', { name: '학과 검색' }).fill('컴퓨터공학')
    await page.getByRole('option', { name: /컴퓨터공학전공/ }).click()
    await page.getByRole('button', { name: '3학년' }).click()
    await page.getByRole('button', { name: '국내학생' }).click()
    await page.getByRole('button', { name: '시간표 만들기' }).click()

    await expect(page.getByText('컴퓨터공학전공 · 3학년')).toBeVisible()
    const required = page.locator('.required-option').filter({ hasText: '운영체제론' })
    await expect(required).toBeVisible()
    await required.getByRole('combobox', { name: '운영체제론 분반' }).selectOption({ index: 1 })
    await required.getByRole('button', { name: '시간표에 배치' }).click()
    await expect(page.getByRole('button', { name: /운영체제론 월 13:30/ })).toBeVisible()
    await page.reload()
    await expect(page.getByRole('heading', { name: /원하는 시간표/ })).toHaveCount(0)
    await expect(page.getByText('컴퓨터공학전공 · 3학년')).toBeVisible()
  })

  test('opens graduation evidence and returns to the editor', async ({ page }) => {
    await page.goto('/requirements')
    await expect(page.getByRole('heading', { name: '예상 졸업요건 점검' })).toBeVisible()
    await expect(page.getByText('확인 필요').first()).toBeVisible()
    await page.getByRole('combobox', { name: /^학과/ }).selectOption({ label: '컴퓨터공학전공' })
    await expect(page.getByRole('heading', { name: '컴퓨터공학전공 공식 확인 자료' })).toBeVisible()
    await expect(page.getByRole('link', { name: '학과 교육과정 원문' })).toHaveAttribute('href', /^https:\/\//)
    await page.getByRole('button', { name: '← 시간표로' }).click()
    await expect(page.getByRole('heading', { name: '내 시간표' })).toBeVisible()
  })

  test('has no serious or critical automated accessibility violations', async ({ page }) => {
    await openEditor(page)
    const editor = await new AxeBuilder({ page }).analyze()
    expect(editor.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')).toEqual([])
    await page.goto('/requirements')
    await expect(page.getByRole('heading', { name: '예상 졸업요건 점검' })).toBeVisible()
    const requirements = await new AxeBuilder({ page }).analyze()
    expect(requirements.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')).toEqual([])
  })
})

test.describe('production optimizer integration', () => {
  test.skip(!process.env.E2E_LIVE, 'requires the Docker API and optimizer worker')

  test('keeps live API responses out of the service worker cache', async ({ page }) => {
    await openEditor(page)
    await page.evaluate(async () => { await navigator.serviceWorker.ready })
    if (!await page.evaluate(() => !!navigator.serviceWorker.controller)) await page.reload()
    await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true)
    await expect(page.getByRole('heading', { name: '내 시간표' })).toBeVisible()
    await expect.poll(() => page.evaluate(async () => {
      const cacheName = (await caches.keys()).find((name) => name.startsWith('pl-timetabler-'))
      if (!cacheName) return false
      const keys = (await (await caches.open(cacheName)).keys()).map((request) => new URL(request.url).pathname)
      return keys.includes('/') && keys.some((path) => path.startsWith('/assets/') && path.endsWith('.js'))
    })).toBe(true)
    expect(await page.evaluate(async () => {
      const response = await fetch('/api/v1/health/ready')
      if (!response.ok) return `HTTP ${response.status}`
      return !!await caches.match('/api/v1/health/ready')
    })).toBe(false)

    expect(await page.evaluate(async () => {
      const cacheName = (await caches.keys()).find((name) => name.startsWith('pl-timetabler-'))
      if (!cacheName) return false
      const cache = await caches.open(cacheName)
      await cache.put('/data/department-sources-2026.json', new Response('{"stale":true}', { headers: { 'Content-Type': 'application/json' } }))
      const fresh = await fetch('/data/department-sources-2026.json').then((response) => response.json()) as { departments?: unknown[] }
      return Array.isArray(fresh.departments) && fresh.departments.length > 0
    })).toBe(true)
    await expect.poll(() => page.evaluate(async () => {
      const cached = await caches.match('/data/department-sources-2026.json')
      if (!cached) return false
      const value = await cached.json() as { departments?: unknown[] }
      return Array.isArray(value.departments) && value.departments.length > 0
    })).toBe(true)

    await page.context().setOffline(true)
    await page.goto(new URL('/requirements', page.url()).href, { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: '예상 졸업요건 점검' })).toBeVisible()
    await page.context().setOffline(false)
  })

  test('creates and applies three real OR-Tools candidates', async ({ page }) => {
    await openEditor(page)
    await expect(page.getByText('최신 데이터 연결됨')).toBeVisible()
    await page.getByRole('button', { name: /과목 추가/ }).last().click()
    const search = page.getByRole('textbox', { name: /과목명/ })
    for (const courseCode of ['005111', '927283', '927430', '922601', '005005']) {
      await search.fill(courseCode)
      const course = page.locator('.course-group').filter({ hasText: courseCode })
      await expect(course).toHaveCount(1)
      await course.getByRole('button', { name: /01분반/ }).click()
    }
    await page.getByRole('button', { name: '과목 검색 닫기' }).click()
    const mobileTools = page.getByRole('button', { name: /자동 생성/ }).first()
    if (await mobileTools.isVisible()) await mobileTools.click()
    await page.getByRole('spinbutton', { name: '최소 학점' }).fill('9')
    await page.getByRole('spinbutton', { name: '최대 학점' }).fill('12')
    await page.getByRole('spinbutton', { name: '목표 학점' }).fill('12')
    await page.getByRole('button', { name: '시간표 3개 만들기' }).click()

    await expect(page.getByRole('article').filter({ hasText: '후보 1' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('article').filter({ hasText: '후보 2' })).toBeVisible()
    await expect(page.getByRole('article').filter({ hasText: '후보 3' })).toBeVisible()
    await page.getByRole('article').filter({ hasText: '후보 1' }).getByRole('button', { name: '이 후보 적용' }).click()
    await expect(page.getByText('자동 생성 후보를 적용했습니다.')).toBeVisible()
  })
})
