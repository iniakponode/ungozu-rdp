import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'

if (process.env.UNG_ACCEPTANCE_MODE !== '1') {
  throw new Error('STOP: This suite may be run only through the isolated acceptance runner.')
}
const baseURL = process.env.UNG_E2E_BASE_URL
if (baseURL !== 'http://127.0.0.1:13110') {
  throw new Error('STOP: unexpected acceptance frontend address.')
}
const reports = process.env.UNG_E2E_ARTIFACTS
if (!reports || !path.isAbsolute(reports)) {
  throw new Error('STOP: acceptance reporting directory is not configured.')
}
export default defineConfig({
  testDir: './tests',
  testMatch: 'acceptance.spec.ts',
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [ ['list'], ['html', { outputFolder: path.join(reports, 'html'), open: 'never' }], ['junit', { outputFile: path.join(reports, 'results.xml') }] ],
  outputDir: path.join(reports, 'traces'),
  use: { ...devices['Desktop Chrome'], browserName: 'chromium', baseURL, headless: true, trace: 'retain-on-failure', screenshot: 'only-on-failure', video: 'off' },
})
