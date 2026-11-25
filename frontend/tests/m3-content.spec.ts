/** Milestone 3 real-browser tests; ONLY via m3_browser_runner.py. */
import { test, expect, type Page } from '@playwright/test'

type Fixture = {
  adminEmail: string
  participantEmails: string[]
  password: string
  cohortIds: number[]
  cohortLabels: string[]
  enrollmentIds: number[]
  marker: string
}
const fixture: Fixture = (() => {
  if (process.env.UNG_M3_BROWSER_MODE !== '1') throw Error('STOP: guarded M3 run only')
  const raw = process.env.UNG_M3_FIXTURE_JSON
  if (!raw) throw Error('STOP: M3 fixture missing')
  const value = JSON.parse(raw) as Fixture
  if (value.cohortIds.length !== 2 || value.participantEmails.length !== 2) {
    throw Error('STOP: Invalid M3 fixture')
  }
  return value
})()

async function adminLogin(page: Page) {
  await page.goto('/admin/login')
  await page.locator('#email').fill(fixture.adminEmail)
  await page.locator('#password').fill(fixture.password)
  await page.getByRole('button', {name: 'Sign in'}).click()
  await expect(page).toHaveURL(/\/admin\/?$/, {timeout: 30_000})
  const me = await page.request.get('/api/auth/me')
  expect(me.status()).toBe(200)
  const identity = await me.json() as {is_admin?: boolean}
  expect(identity.is_admin).toBe(true)
  await page.goto('/admin/content')
  await expect(page.locator('#content-cohort')).toBeVisible()
  await expect(page.locator(`#content-cohort option[value="${fixture.cohortIds[0]}"]`)).toHaveCount(1)
  await expect(page.locator(`#content-cohort option[value="${fixture.cohortIds[1]}"]`)).toHaveCount(1)
}

async function participantLogin(page: Page, index: number) {
  await page.goto('/login')
  await page.locator('#participant-email').fill(fixture.participantEmails[index])
  await page.locator('#participant-password').fill(fixture.password)
  await page.getByRole('button', {name: 'Sign in'}).click()
  await expect(page).toHaveURL(/\/portal\/?$/, {timeout: 30_000})
  await expect(page.getByRole('heading', {name: /Welcome,/})).toBeVisible({timeout: 30_000})
  await page.getByText('Events & Resources', {exact: true}).click()
  await expect(page.getByText('Upcoming programme events', {exact: true})).toBeVisible()
}

function contentCard(page: Page, title: string) {
  return page.locator('div.rounded-md.border.p-3').filter({has: page.getByText(title, {exact: true})})
}

function formCard(page: Page, heading: string) {
  const title = page.locator('[data-slot="card-title"]').getByText(
    heading, {exact: true}
  )
  return page.locator('[data-slot="card"]').filter({has: title})
}

test('M3 cohort-scoped event/resource creation, editing, publication and participant visibility', async ({browser}) => {
  const adminContext = await browser.newContext()
  const admin = await adminContext.newPage()
  const participantAContext = await browser.newContext()
  const participantA = await participantAContext.newPage()
  const participantBContext = await browser.newContext()
  const participantB = await participantBContext.newPage()
  const originalEvent = `M3 Browser Event ${fixture.marker}`
  const revisedEvent = `M3 Browser Event Revised ${fixture.marker}`
  const originalResource = `M3 Browser Resource ${fixture.marker}`
  const revisedResource = `M3 Browser Resource Revised ${fixture.marker}`

  try {
    await test.step('Admin login and explicit cohort A selection', async () => {
      await adminLogin(admin)
      await expect(admin.getByText('Choose or create a cohort before managing content.')).toBeVisible()
      await admin.locator('#content-cohort').selectOption(String(fixture.cohortIds[0]))
      await expect(formCard(admin, 'Create event')).toBeVisible()
    })

    await test.step('Create draft WAT event and verify displayed record', async () => {
      const card = formCard(admin, 'Create event')
      await card.locator('input').nth(0).fill(originalEvent)
      await card.locator('input[type="datetime-local"]').first().fill('2030-02-15T10:00')
      await card.locator('input[type="datetime-local"]').nth(1).fill('2030-02-15T11:30')
      await expect(card.locator('input[type="checkbox"]')).not.toBeChecked()
      await card.getByRole('button', {name: 'Create event'}).click()
      await expect(contentCard(admin, originalEvent)).toBeVisible()
      await expect(contentCard(admin, originalEvent).getByText('hidden', {exact:true})).toBeVisible()
    })

    await test.step('Event Cancel leaves title unchanged; Save edits title', async () => {
      await contentCard(admin, originalEvent).getByRole('button', {name: 'Edit'}).click()
      const editor = formCard(admin, 'Edit event')
      await expect(editor).toBeVisible()
      await editor.locator('input').first().fill(revisedEvent)
      await editor.getByRole('button', {name: 'Cancel'}).click()
      await expect(contentCard(admin, originalEvent)).toBeVisible()
      await expect(contentCard(admin, revisedEvent)).toHaveCount(0)
      await contentCard(admin, originalEvent).getByRole('button', {name: 'Edit'}).click()
      const updatedEditor = formCard(admin, 'Edit event')
      await updatedEditor.locator('input').first().fill(revisedEvent)
      await updatedEditor.getByRole('button', {name: 'Save changes'}).click()
      await expect(contentCard(admin, revisedEvent)).toBeVisible()
    })

    await test.step('Draft event remains hidden from participant A', async () => {
      await participantLogin(participantA, 0)
      await expect(participantA.getByText(revisedEvent, {exact:true})).toHaveCount(0)
    })

    await test.step('Publish event and verify participant A, not cohort B', async () => {
      await contentCard(admin, revisedEvent).getByRole('button', {name: 'Publish'}).click()
      await expect(contentCard(admin, revisedEvent).getByText('published', {exact:true})).toBeVisible()
      await participantA.reload()
      await participantA.getByText('Events & Resources', {exact:true}).click()
      await expect(participantA.getByText(revisedEvent, {exact:true})).toBeVisible()
      await participantLogin(participantB, 1)
      await expect(participantB.getByText(revisedEvent, {exact:true})).toHaveCount(0)
    })

    await test.step('Switch to cohort B without displaying cohort A records', async () => {
      await admin.locator('#content-cohort').selectOption(String(fixture.cohortIds[1]))
      await expect(formCard(admin, 'Create resource')).toBeVisible()
      await expect(contentCard(admin, revisedEvent)).toHaveCount(0)
    })

    await test.step('Create resource draft, edit, Cancel and Save', async () => {
      const card = formCard(admin, 'Create resource')
      await card.locator('input').first().fill(originalResource)
      await card.getByRole('button', {name:'Create resource'}).click()
      await expect(contentCard(admin, originalResource)).toBeVisible()
      await expect(contentCard(admin, originalResource).getByText('hidden', {exact:true})).toBeVisible()
      await contentCard(admin, originalResource).getByRole('button', {name:'Edit'}).click()
      let editor = formCard(admin, 'Edit resource')
      await editor.locator('input').first().fill(revisedResource)
      await editor.getByRole('button', {name:'Cancel'}).click()
      await expect(contentCard(admin, originalResource)).toBeVisible()
      await contentCard(admin, originalResource).getByRole('button', {name:'Edit'}).click()
      editor = formCard(admin, 'Edit resource')
      await editor.locator('input').first().fill(revisedResource)
      await editor.getByRole('button', {name:'Save changes'}).click()
      await expect(contentCard(admin, revisedResource)).toBeVisible()
    })

    await test.step('Publish resource to cohort B only', async () => {
      await participantB.reload()
      await participantB.getByText('Events & Resources', {exact:true}).click()
      await expect(participantB.getByText(revisedResource, {exact:true})).toHaveCount(0)
      await contentCard(admin, revisedResource).getByRole('button', {name:'Publish'}).click()
      await expect(contentCard(admin, revisedResource).getByText('published', {exact:true})).toBeVisible()
      await participantB.reload()
      await participantB.getByText('Events & Resources', {exact:true}).click()
      await expect(participantB.getByText(revisedResource, {exact:true})).toBeVisible()
      await participantA.reload()
      await participantA.getByText('Events & Resources', {exact:true}).click()
      await expect(participantA.getByText(revisedResource, {exact:true})).toHaveCount(0)
    })

    await test.step('Unpublish resources and event; participant visibility ends', async () => {
      await contentCard(admin, revisedResource).getByRole('button', {name:'Unpublish'}).click()
      await expect(contentCard(admin, revisedResource).getByText('hidden', {exact:true})).toBeVisible()
      await admin.locator('#content-cohort').selectOption(String(fixture.cohortIds[0]))
      await expect(contentCard(admin, revisedEvent)).toBeVisible()
      await contentCard(admin, revisedEvent).getByRole('button', {name:'Unpublish'}).click()
      await expect(contentCard(admin, revisedEvent).getByText('hidden', {exact:true})).toBeVisible()
      await participantA.reload()
      await participantA.getByText('Events & Resources', {exact:true}).click()
      await expect(participantA.getByText(revisedEvent, {exact:true})).toHaveCount(0)
      await participantB.reload()
      await participantB.getByText('Events & Resources', {exact:true}).click()
      await expect(participantB.getByText(revisedResource, {exact:true})).toHaveCount(0)
    })
    await test.step('Simulated failed deletion keeps records visible', async () => {
      let interceptedDeletes = 0

      await admin.route('**/api/rdp-admin/**', async route => {
        if (route.request().method() === 'DELETE') {
          interceptedDeletes += 1
          await route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({
              detail: 'M3 simulated deletion failure',
            }),
          })
        } else {
          await route.continue()
        }
      })

      try {
        // The earlier test leaves cohort A selected.
        await expect(contentCard(admin, revisedEvent)).toBeVisible()

        admin.once('dialog', dialog => {
          void dialog.accept()
        })

        await contentCard(admin, revisedEvent)
          .getByRole('button', {name: 'Delete'})
          .click()

        await expect(
          admin.getByText(
            'A server problem prevented this action. Please try again or contact support.',
            {exact: true}
          ).first()
        ).toBeVisible()

        await expect(contentCard(admin, revisedEvent)).toBeVisible()
        await expect(
          contentCard(admin, revisedEvent)
            .getByRole('button', {name: 'Delete'})
        ).toBeEnabled()

        await admin.locator('#content-cohort')
          .selectOption(String(fixture.cohortIds[1]))

        await expect(contentCard(admin, revisedResource)).toBeVisible()

        admin.once('dialog', dialog => {
          void dialog.accept()
        })

        await contentCard(admin, revisedResource)
          .getByRole('button', {name: 'Delete'})
          .click()

        await expect(
          admin.getByText(
            'A server problem prevented this action. Please try again or contact support.',
            {exact: true}
          ).first()
        ).toBeVisible()

        await expect(contentCard(admin, revisedResource)).toBeVisible()
        await expect(
          contentCard(admin, revisedResource)
            .getByRole('button', {name: 'Delete'})
        ).toBeEnabled()

        expect(interceptedDeletes).toBe(2)
      } finally {
        await admin.unrouteAll({behavior: 'wait'})
      }
    })

    await test.step('Delayed cohort A responses cannot overwrite cohort B', async () => {
      const cohortA = fixture.cohortIds[0]
      const cohortB = fixture.cohortIds[1]
      let delayedRequests = 0
      let releaseRequests!: () => void

      const gate = new Promise<void>(resolve => {
        releaseRequests = resolve
      })

      // The preceding failed-delete test leaves cohort B selected.
      await expect(contentCard(admin, revisedResource)).toBeVisible()

      await admin.route('**/api/rdp-admin/**', async route => {
        const request = route.request()
        const url = new URL(request.url())

        const isCohortARead =
          request.method() === 'GET' &&
          /^\/api\/rdp-admin\/(events|resources)$/.test(url.pathname) &&
          url.searchParams.get('cohort_id') === String(cohortA)

        if (isCohortARead) {
          delayedRequests += 1
          await gate
        }

        await route.continue()
      })

      try {
        await admin.locator('#content-cohort')
          .selectOption(String(cohortA))

        // Confirm both cohort A requests are held before switching.
        await expect.poll(() => delayedRequests, {
          timeout: 15_000,
        }).toBe(2)

        const eventResponse = admin.waitForResponse(response => {
          const url = new URL(response.url())
          return response.request().method() === 'GET' &&
            url.pathname === '/api/rdp-admin/events' &&
            url.searchParams.get('cohort_id') === String(cohortA)
        })

        const resourceResponse = admin.waitForResponse(response => {
          const url = new URL(response.url())
          return response.request().method() === 'GET' &&
            url.pathname === '/api/rdp-admin/resources' &&
            url.searchParams.get('cohort_id') === String(cohortA)
        })

        await admin.locator('#content-cohort')
          .selectOption(String(cohortB))

        await expect(contentCard(admin, revisedResource)).toBeVisible()
        await expect(contentCard(admin, revisedEvent)).toHaveCount(0)

        // Deliver the stale cohort A responses after cohort B is loaded.
        releaseRequests()

        const [eventResult, resourceResult] = await Promise.all([
          eventResponse,
          resourceResponse,
        ])

        expect(eventResult.ok()).toBe(true)
        expect(resourceResult.ok()).toBe(true)

        await expect(
          admin.locator('#content-cohort')
        ).toHaveValue(String(cohortB))

        await expect(contentCard(admin, revisedResource)).toBeVisible()
        await expect(contentCard(admin, revisedEvent)).toHaveCount(0)

        expect(delayedRequests).toBe(2)
      } finally {
        releaseRequests()
        await admin.unrouteAll({behavior: 'wait'})
      }
    })

  } finally {
    await participantBContext.close()
    await participantAContext.close()
    await adminContext.close()
  }
})
