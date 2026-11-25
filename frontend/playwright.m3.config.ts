import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'

if (process.env.UNG_M3_BROWSER_MODE !== '1') {
  throw new Error('STOP: M3 browser suite requires the dedicated guarded runner')
}
if (process.env.UNG_E2E_BASE_URL !== 'http://127.0.0.1:13113') {
  throw new Error('STOP: Unexpected M3 frontend address')
}
if (!process.env.UNG_M3_FIXTURE_JSON) {
  throw new Error('STOP: Browser fixture missing')
}
const reports = process.env.UNG_E2E_ARTIFACTS
if (!reports || !path.isAbsolute(reports)) {
  throw new Error('STOP: Absolute report directory required')
}

export default defineConfig({
  testDir: './tests', testMatch: 'm3-content.spec.ts',
  fullyParallel: false, workers: 1, retries: 0, forbidOnly: true,
  timeout: 120_000, expect: { timeout: 20_000 },
  reporter: [['list'], ['html', {outputFolder: path.join(reports, 'html'), open: 'never'}]],
  outputDir: path.join(reports, 'traces'),
  use: {...devices['Desktop Chrome'], browserName: 'chromium', headless: true,
    baseURL: process.env.UNG_E2E_BASE_URL, trace: 'retain-on-failure', screenshot: 'only-on-failure'},
})
