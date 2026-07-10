import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'

async function openEditor(page: Page) {
  await page.goto('/')
  const skip = page.getByRole('button', { name: '건너뛰고 바로 만들기' })
  if (await skip.isVisible()) await skip.click()
  await expect(page.getByRole('heading', { name: '내 시간표' })).toBeVisible()
}

async function addCourse(page: Page, query: string, courseName: RegExp, sectionName = /01분반.*추가/) {
  await page.getByRole('button', { name: /과목 추가/ }).last().click()
  await page.getByRole('textbox', { name: /과목명/ }).fill(query)
  await page.getByRole('button', { name: courseName }).click()
  await page.getByRole('button', { name: sectionName }).click()
  await page.getByRole('button', { name: '과목 검색 닫기' }).click()
}

async function seedDraft(page: Page, sectionId = '922601-01') {
  await page.addInitScript(({ seededSectionId }) => {
    localStorage.setItem('pl-timetabler:onboarding:v1', 'complete')
    localStorage.setItem('pl-timetabler:draft:v1', JSON.stringify({
      schemaVersion: 1,
      semester: '2026-1',
      dataVersion: 'e2e-seed',
      items: [{ sectionId: seededSectionId, role: 'want', locked: false }],
      preferences: { targetCredits: 2, minCredits: 2, maxCredits: 21, preferredFreeDays: [], avoidBefore: null, avoidAfter: null, minLunchMinutes: 60, maxDailyMinutes: 360, compactness: 70, minimizeChanges: true },
      updatedAt: '2026-07-11T00:00:00.000Z',
    }))
  }, { seededSectionId: sectionId })
}

test.describe('responsive timetable editor', () => {

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
    await page.getByRole('button', { name: /AI시대의컴퓨팅사고.*분반 보기/ }).click()
    await page.getByRole('button', { name: /01분반.*추가/ }).click()
    await page.getByRole('button', { name: '과목 검색 닫기' }).click()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.reload()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })).toBeVisible()
  })

  test('saves accelerated progression for manual review without authorizing automatic requirements', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /원하는 시간표/ })).toBeVisible()
    await page.getByRole('button', { name: '학과 선택하고 시작' }).click()
    await page.getByRole('textbox', { name: '학과 검색' }).fill('컴퓨터공학')
    await page.getByRole('option', { name: /컴퓨터공학전공/ }).click()
    await page.getByRole('button', { name: '3학년' }).click()
    await page.getByRole('button', { name: '국내학생' }).click()
    await expect(page.getByRole('alert')).toContainText('보통 1학년')
    await expect(page.getByRole('alert')).toContainText('학과 확인 전에는 필수과목을 자동 판정하지 않습니다')
    await expect(page.getByRole('checkbox', { name: /현재 3학년이 맞습니다/ })).toHaveCount(0)
    await page.getByRole('button', { name: '시간표 만들기' }).click()

    await expect(page.getByText('컴퓨터공학전공 · 3학년')).toBeVisible()
    await page.getByRole('button', { name: /필수 과목 먼저/ }).click()
    await expect(page.getByText(/현재 학년이 일반 예상보다 높아 학과 확인 전에는 전공필수를 자동 판정하지 않습니다/)).toBeVisible()
    await expect(page.getByRole('button', { name: '시간표에 배치' })).toHaveCount(0)
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

  test('uses a real mobile tools dialog with close, Escape, Back, and exact trigger focus return', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-390', 'mobile dialog contract')
    await openEditor(page)
    const trigger = page.getByRole('button', { name: /자동 생성/ })
    await expect(page.getByRole('dialog', { name: '자동 생성과 준비' })).toHaveCount(0)

    await trigger.click()
    const dialog = page.getByRole('dialog', { name: '자동 생성과 준비' })
    await expect(dialog).toBeVisible()
    await expect(page.getByRole('button', { name: '닫기' })).toBeFocused()
    const dialogA11y = await new AxeBuilder({ page }).include('.tools-dialog').analyze()
    expect(dialogA11y.violations.filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')).toEqual([])
    await page.getByRole('button', { name: '닫기' }).click()
    await expect(dialog).toHaveCount(0)
    await expect(trigger).toBeFocused()

    await trigger.click()
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(trigger).toBeFocused()

    await trigger.click()
    await page.evaluate(() => history.back())
    await expect(dialog).toHaveCount(0)
    await expect(trigger).toBeFocused()
  })

  test('keeps the tools as a static reachable aside on tablet and desktop', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile-390', 'desktop/tablet aside contract')
    await openEditor(page)
    await expect(page.getByRole('complementary', { name: '자동 생성과 준비' })).toBeVisible()
    await expect(page.getByRole('dialog', { name: '자동 생성과 준비' })).toHaveCount(0)
  })

  test('exposes mobile recovery commands through the compact overflow', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-390', 'mobile command contract')
    await openEditor(page)
    await page.getByRole('button', { name: '더보기' }).click()
    const menu = page.getByRole('menu', { name: '시간표 명령' })
    for (const name of ['실행 취소', '다시 실행', '시간표 공유', '졸업요건', 'PNG 저장', 'PDF 저장']) {
      await expect(menu.getByRole('menuitem', { name })).toBeVisible()
    }
  })

  test('supports undo and redo keyboard shortcuts outside editable controls', async ({ page }) => {
    await openEditor(page)
    await addCourse(page, 'AI시대의컴퓨팅사고', /AI시대의컴퓨팅사고.*분반 보기/)
    const block = page.getByRole('button', { name: /AI시대의컴퓨팅사고 화/ })
    await expect(block).toBeVisible()
    await page.keyboard.press('Control+z')
    await expect(block).toHaveCount(0)
    await page.keyboard.press('Control+Shift+z')
    await expect(block).toBeVisible()
  })

  test('starts the timetable grid within the initial 390px mobile viewport budget', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-390', '390px layout contract')
    await page.addInitScript(() => {
      localStorage.setItem('pl-timetabler:onboarding:v1', 'complete')
      localStorage.setItem('pl-timetabler:profile:v1', JSON.stringify({ schemaVersion: 1, department: '컴퓨터공학전공', admissionYear: 2026, currentGrade: 1, entryType: 'FRESHMAN', studentType: 'DOMESTIC', sectionGroup: 'UNKNOWN', updatedAt: '2026-07-11T00:00:00Z' }))
    })
    await page.goto('/')
    await expect(page.getByRole('button', { name: /필수 과목 먼저/ })).toHaveAttribute('aria-expanded', 'false')
    const box = await page.locator('.timetable-grid').boundingBox()
    expect(box?.y).toBeLessThanOrEqual(360)
  })
})

test.describe('desktop preview and guided section drag', () => {
  test('keeps decision metrics in mobile and desktop preview, then applies with undo', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'mobile and desktop preview contract')
    await seedDraft(page)
    await page.route('**/api/v1/optimizations', async (route) => {
      if (new URL(route.request().url()).pathname !== '/api/v1/optimizations') return route.continue()
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'e2e-preview',
          status: 'OPTIMAL',
          result: {
            candidates: [{
              rank: 1,
              sectionIds: ['922601-03'],
              metrics: { totalCredits: 2, campusDays: 1, gapMinutes: 0, firstClassMinute: 570, lastClassMinute: 690 },
              scoreComponents: { weighted: 100 },
              explanation: ['금요일 오전 분반으로 교체'],
              unmetPreferences: [],
            }],
            reasons: [],
          },
        }),
      })
    })
    await openEditor(page)
    if (testInfo.project.name === 'mobile-390') await page.getByRole('button', { name: /자동 생성/ }).click()

    await page.getByRole('button', { name: '시간표 3개 만들기' }).click()
    await page.getByRole('button', { name: '후보 1 미리보기' }).click()

    const preview = page.getByRole('region', { name: '후보 1 변경 내용' })
    await expect(preview).toBeFocused()
    await expect(preview.getByText('교체: AI시대의컴퓨팅사고 01분반 → 03분반')).toBeVisible()
    const metrics = preview.getByLabel('후보 시간표 요약')
    await expect(metrics).toContainText('등교일1일')
    await expect(metrics).toContainText('학점2학점')
    await expect(metrics).toContainText('빈 시간0분')
    await expect(metrics).toContainText('첫 수업09:30')
    await expect(metrics).toContainText('마지막 수업11:30')
    await expect(page.getByRole('heading', { name: '내 시간표' }).locator('..')).toContainText('1개 분반')
    await expect(page.getByLabel(/AI시대의컴퓨팅사고 화.*교체 전 분반/)).toBeVisible()
    await expect(page.getByLabel(/AI시대의컴퓨팅사고 금.*교체 후 분반/)).toBeVisible()
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!).items[0].sectionId)).toBe('922601-01')

    await page.getByRole('button', { name: '후보 적용' }).click()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 금 09:30/ })).toBeVisible()
    await page.getByRole('button', { name: '되돌리기' }).click()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화 11:30/ })).toBeVisible()
  })

  test('drops only on an official alternative and keeps replacement undoable', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'desktop-1440', 'desktop drag contract')
    await seedDraft(page)
    await openEditor(page)

    const source = page.getByRole('button', { name: /AI시대의컴퓨팅사고 화 11:30.*드래그/ })
    await expect(source).toHaveAttribute('draggable', 'true')
    const dataTransfer = await page.evaluateHandle(() => new DataTransfer())
    await source.dispatchEvent('dragstart', { dataTransfer })
    const officialSlot = page.locator('[data-drop-slot-key="금-09:30-11:30"]')
    await expect(officialSlot).toBeVisible()
    await expect(officialSlot).toContainText('3개 분반 중 선택')
    await officialSlot.dispatchEvent('dragenter', { dataTransfer })
    await expect(officialSlot).toHaveClass(/active/)
    await officialSlot.dispatchEvent('dragover', { dataTransfer })
    await officialSlot.dispatchEvent('drop', { dataTransfer })
    await dataTransfer.dispose()

    const chooser = page.getByRole('dialog', { name: '같은 시간 분반 선택' })
    await expect(chooser.getByRole('button', { name: '03분반 선택' })).toBeFocused()
    await expect(chooser.getByRole('button', { name: '04분반 선택' })).toBeVisible()
    await expect(chooser.getByRole('button', { name: '05분반 선택' })).toBeVisible()
    await chooser.getByRole('button', { name: '04분반 선택' }).click()

    await expect(page.getByRole('heading', { name: '내 시간표' })).toBeFocused()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 금 09:30/ })).toBeVisible()
    await expect(page.locator('.timetable-section [role="status"]')).toContainText('04분반으로 교체했습니다')
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('pl-timetabler:draft:v1')!).items[0].sectionId)).toBe('922601-04')
    await page.getByRole('button', { name: '되돌리기' }).click()
    await expect(page.getByRole('button', { name: /AI시대의컴퓨팅사고 화 11:30/ })).toBeVisible()
    await expect(page.getByRole('dialog', { name: 'AI시대의컴퓨팅사고' })).toHaveCount(0)
  })

  test('keeps click and keyboard alternatives complete at every viewport', async ({ page }, testInfo) => {
    await seedDraft(page)
    await openEditor(page)
    const block = page.getByRole('button', { name: /AI시대의컴퓨팅사고 화 11:30/ })
    await expect(block).toHaveAttribute('draggable', testInfo.project.name === 'desktop-1440' ? 'true' : 'false')
    await block.focus()
    await page.keyboard.press('Enter')
    const dialog = page.getByRole('dialog', { name: 'AI시대의컴퓨팅사고' })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('button', { name: /03분반.*교체/ })).toBeVisible()
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
      await course.getByRole('button', { name: /분반 보기/ }).click()
      await course.getByRole('button', { name: /01분반.*추가/ }).click()
    }
    await page.getByRole('button', { name: '과목 검색 닫기' }).click()
    const mobileTools = page.getByRole('button', { name: /자동 생성/ }).first()
    if (await mobileTools.isVisible()) await mobileTools.click()
    await page.getByText('세부 조건 조정').click()
    await page.getByRole('spinbutton', { name: '최소 학점' }).fill('9')
    await page.getByRole('spinbutton', { name: '최대 학점' }).fill('12')
    await page.getByRole('spinbutton', { name: '목표 학점' }).fill('12')
    await page.getByRole('button', { name: '시간표 3개 만들기' }).click()

    await expect(page.getByRole('article').filter({ hasText: '후보 1' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('article').filter({ hasText: '후보 2' })).toBeVisible()
    await expect(page.getByRole('article').filter({ hasText: '후보 3' })).toBeVisible()
    await page.getByRole('article').filter({ hasText: '후보 1' }).getByRole('button', { name: '후보 1 미리보기' }).click()
    await page.getByRole('button', { name: '후보 적용' }).click()
    await expect(page.getByText('자동 생성 후보를 적용했습니다.')).toBeVisible()
  })
})
