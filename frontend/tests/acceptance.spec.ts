/** Isolated, browser-driven A/B/C acceptance. Never run against production. */
import { test, expect } from '@playwright/test'

type Fixture = {
  adminEmail: string; participantEmail: string; outsiderEmail: string; password: string;
  programmeTitle: string; versionTitle: string; cohortSlug: string; cohortId: number; versionId: number;
  curriculumTitle: string; criterionTitle: string; enrollmentId: number; outsiderEnrollmentId: number
}
const fixture = (() => {
  if (process.env.UNG_ACCEPTANCE_MODE !== '1') throw Error('STOP: isolated acceptance mode required')
  const raw = process.env.UNG_E2E_FIXTURE_JSON
  if (!raw) throw Error('STOP: runner fixture not supplied')
  return JSON.parse(raw) as Fixture
})()

async function adminLogin(page: import('@playwright/test').Page) {
  await page.goto('/admin/login')
  await page.locator('#email').fill(fixture.adminEmail)
  await page.locator('#password').fill(fixture.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/admin(?:\/)?$/, { timeout: 30_000 })
  // A successful redirect is not proof of a persisted admin session.
  // Verify the authenticated API before looking for dashboard controls.
  const session = await page.request.get('/api/auth/me')
  if (!session.ok()) {
    throw new Error(`Administrator session check failed: /api/auth/me returned HTTP ${session.status()}; current page: ${page.url()}`)
  }
  const identity = (await session.json()) as { is_admin?: boolean }
  if (!identity.is_admin) {
    throw new Error('Administrator session check failed: /api/auth/me did not confirm administrator privileges')
  }
  await expect(page.locator('#admin-cohort'), 'Admin dashboard should render after verified login')
    .toBeVisible({ timeout: 40_000 })
}
async function participantLogin(page: import('@playwright/test').Page, email = fixture.participantEmail) {
  await page.goto('/login')
  await page.locator('#participant-email').fill(email)
  await page.locator('#participant-password').fill(fixture.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/portal(?:\/)?$/)
}

test('Isolated browser acceptance: published programme → application → delivery → assessment → certificate → revocation', async ({ browser }) => {
  let publicApplicantEmail = ''
  const guest = await browser.newContext()
  const applicant = await guest.newPage()
  await test.step('Public catalogue and fee pages display a real published fixture', async () => {
    await applicant.goto(`/programme?cohort=${fixture.cohortSlug}`)
    await expect(applicant.getByText(fixture.versionTitle).first()).toBeVisible()
    await applicant.goto(`/fees?cohort=${fixture.cohortSlug}`)
    await expect(applicant.getByText('E2E Testing Only Fee Plan').first()).toBeVisible()
  })
  await test.step('Anonymous applicant selects cohort and submits an application', async () => {
    await applicant.goto(`/apply?cohort=${fixture.cohortSlug}`)
    await expect(applicant.locator('#selected-cohort')).toHaveValue(fixture.cohortSlug)
    const stamp = Date.now().toString(36)
    publicApplicantEmail = `e2e-applicant-${stamp}@example.com`
    const fields: Record<string, string> = {
      full_name: 'E2E Public Applicant', email: publicApplicantEmail,
      country: 'Nigeria', institution: 'Acceptance Test Institution', career_stage: 'Early career researcher',
      discipline: 'Computer science',
      research_interests: 'Testing the browser application submission with an isolated programme cohort',
      goals: 'Demonstrate that applications are bound to the correct published cohort in the test database',
      challenges: 'Ensuring that multiple programme journeys remain separate and are validated correctly',
      commitment: 'I will review and complete all development activities in this controlled testing environment',
    }
    for (const [key, value] of Object.entries(fields)) await applicant.locator(`#${key}`).fill(value)
    await applicant.locator('input[type=checkbox][required]').check()
    await applicant.getByRole('button', { name: 'Submit application' }).click()
    await expect(applicant.getByText('Application received')).toBeVisible()
    await expect(applicant.getByText('Application reference')).toBeVisible()
  })

  const adminContext = await browser.newContext()
  const admin = await adminContext.newPage()
  await test.step('Administrator login, builder and assessment pages', async () => {
    await adminLogin(admin)
    // Wait for the cohort data (loaded asynchronously) before selecting it.
    await expect(admin.locator(`#admin-cohort option[value="${fixture.cohortId}"]`),
      'The published fixture cohort should be available in admin selection')
      .toHaveCount(1, { timeout: 30_000 })
    await admin.locator('#admin-cohort').selectOption(String(fixture.cohortId))
    await admin.getByPlaceholder('Search applicant, email or reference').fill(publicApplicantEmail)
    await expect(admin.getByText(publicApplicantEmail)).toBeVisible()
    await admin.getByRole('link', { name: 'Review' }).last().click()
    await expect(admin.getByRole('heading', { name: 'E2E Public Applicant' })).toBeVisible()
    await expect(admin.locator('option').filter({ hasText: 'E2E Testing Only Fee Plan' })).toHaveCount(1)
    await admin.goto('/admin/builder')
    // The programme is initially rendered inside an unselected HTML <select>.
    // Playwright does not consider a closed dropdown <option> visible.
    // Select the published programme, then verify that its version is available.
    const programmePicker = admin.getByRole('combobox').first()
    const matchingProgramme = programmePicker.locator('option').filter({ hasText: fixture.programmeTitle })
    await expect(matchingProgramme, 'Fixture programme should be present in the Builder selector')
      .toHaveCount(1, { timeout: 20_000 })
    const programmeValue = await matchingProgramme.getAttribute('value')
    if (!programmeValue) throw new Error('Fixture programme has no selectable value in the Builder')
    await programmePicker.selectOption(programmeValue)
    await expect(admin.getByText('2. Version', { exact: true })).toBeVisible()
    const versionPicker = admin.getByRole('combobox').nth(1)
    await expect(versionPicker.locator(`option[value="${fixture.versionId}"]`),
      'Fixture version should belong to the selected programme')
      .toHaveCount(1, { timeout: 20_000 })
    await versionPicker.selectOption(String(fixture.versionId))
    await expect(admin.getByText('3. Curriculum modules and items', { exact: true })).toBeVisible()
    await admin.goto('/admin/assessments')
    const rubricPicker = admin.locator('#rubric-version')
    // Wait for the requested version to load before selecting it.
    await expect(rubricPicker.locator(`option[value="${fixture.versionId}"]`),
      'Assessment selector should contain the current fixture version')
      .toHaveCount(1, { timeout: 30_000 })
    await rubricPicker.selectOption(String(fixture.versionId))
    // Guard against asynchronous initialisation resetting the chosen version.
    await expect(rubricPicker).toHaveValue(String(fixture.versionId))
    // CardTitle renders a styled div, not a semantic HTML heading.
    // The selected programme version and criterion must still be visible.
    await expect(admin.getByText(`Criteria for ${fixture.versionTitle}`, { exact: true }),
      'Assessment card title must reflect the selected programme version')
      .toBeVisible({ timeout: 20_000 })
    await expect(admin.getByText(`${fixture.criterionTitle} (required)`, { exact: true }),
      'Rubric criteria must belong to this programme version')
      .toBeVisible({ timeout: 20_000 })
  })

  const participantContext = await browser.newContext()
  const participant = await participantContext.newPage()
  await test.step('Participant login and evidence submission', async () => {
    await participantLogin(participant)
    await expect(participant.getByText(fixture.curriculumTitle).first()).toBeVisible()
    await participant.getByPlaceholder('Describe your submitted output, evidence or research artefact').fill('E2E submitted methods chapter with source evidence, reviewed entirely within the isolated browser test schema.')
    await participant.getByRole('button', { name: 'Submit evidence' }).click()
    await expect(participant.getByText('Status: submitted').first()).toBeVisible()
  })
  await test.step('A different participant cannot read this enrolment', async () => {
    const otherContext = await browser.newContext()
    const other = await otherContext.newPage()
    try {
      await participantLogin(other, fixture.outsiderEmail)
      const result = await other.request.get(`/api/rdp-portal/completion?enrollment_id=${fixture.enrollmentId}`)
      expect(result.status()).toBe(403)
    } finally {
      await otherContext.close()
    }
  })

  await test.step('Administrator reviews the plan, check-in and submitted curriculum', async () => {
    await admin.goto(`/admin/enrollments/${fixture.enrollmentId}`)
    await expect(admin.getByText('E2E Test Researcher').first()).toBeVisible()
    await expect(admin.getByRole('button', { name: 'Approve completion' })).toBeDisabled()
    await admin.getByRole('button', { name: 'Save IRDP feedback' }).click()
    await admin.getByRole('button', { name: 'Mark reviewed & save feedback' }).click()
    const reviewed = admin.getByText('Curriculum review feedback', { exact: true }).locator('..')
    await reviewed.getByRole('textbox').fill('Acceptable documented research output for this test')
    await admin.getByRole('button', { name: 'Approve evidence' }).click()
    await expect(admin.getByText('Curriculum item reviewed')).toBeVisible()
  })
  await test.step('Assessment and reasoned completion decision', async () => {
    const rubric = admin.locator('div.rounded-lg.border.p-4.space-y-3').filter({ hasText: fixture.criterionTitle })
    await expect(rubric).toHaveCount(1)
    await rubric.getByRole('spinbutton').fill('87')
    await rubric.getByRole('textbox').nth(0).fill('E2E assessed methodology chapter, evidence and citations')
    await rubric.getByRole('textbox').nth(1).fill('Methods meet the required published criterion')
    await rubric.getByRole('button', { name: 'Record assessment' }).click()
    const decision = admin.getByText('Reasoned completion decision (minimum 10 characters)').locator('..')
    await decision.getByRole('textbox').fill('All required work, progression evidence and rubric evaluations reviewed satisfactorily.')
    await expect(admin.getByRole('button', { name: 'Approve completion' })).toBeEnabled()
    await admin.getByRole('button', { name: 'Approve completion' }).click()
    await expect(admin.getByRole('button', { name: 'Issue certificate' })).toBeEnabled()
  })

  let token = ''
  await test.step('Certificate issue, verification and printable page', async () => {
    await admin.getByRole('button', { name: 'Issue certificate' }).click()
    const link = admin.getByRole('link', { name: 'Public verification' })
    await expect(link).toBeVisible()
    token = (await link.getAttribute('href'))?.split('/').pop() ?? ''
    expect(token).toMatch(/^[A-Za-z0-9_-]{43}$/)
    await applicant.goto(`/verify/${token}`)
    await expect(applicant.getByText('Verified certificate')).toBeVisible()
    await expect(applicant.getByText('E2E Test Researcher')).toBeVisible()
    await applicant.goto(`/certificate/${token}`)
    await expect(applicant.getByRole('heading', { name: 'Certificate of Completion' })).toBeVisible()
    await applicant.goto(`/verify/${'0'.repeat(43)}`)
    await expect(applicant.getByText('Certificate could not be verified.')).toBeVisible()
  })
  await test.step('Revoked certificate immediately becomes invalid in public verification', async () => {
    await admin.getByText('Revocation reason').locator('..').getByRole('textbox').fill('Revoked for isolated acceptance test verification only.')
    admin.once('dialog', dialog => dialog.accept())
    await admin.getByRole('button', { name: 'Revoke certificate' }).click()
    await expect(admin.getByText('Revoked', { exact: true }).first()).toBeVisible()
    await applicant.goto(`/verify/${token}`)
    await expect(applicant.getByText('Certificate revoked — not valid')).toBeVisible()
  })
  await guest.close()
  await participantContext.close()
  await adminContext.close()
})
