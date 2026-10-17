/** Mocked browser-only quotation UI. Starts localhost Next.js; no database writes. */
import { defineConfig, devices } from '@playwright/test'

if (process.env.UNG_QUOTATION_UI_MOCK !== '1') {
  throw new Error('STOP: Set UNG_QUOTATION_UI_MOCK=1 to run this isolated mocked UI test.')
}

const baseURL = 'http://127.0.0.1:13220'
export default defineConfig({
  testDir: './tests',
  testMatch: 'quotation-ui.spec.ts',
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: 'list',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: { ...devices['Desktop Chrome'], baseURL, browserName: 'chromium', headless: true },
  webServer: {
    command: 'npm run dev -- --hostname 127.0.0.1 --port 13220',
    url: `${baseURL}/status`,
    reuseExistingServer: false,
    timeout: 180_000,
    env: { ...process.env, NEXT_TELEMETRY_DISABLED: '1' },
  },
})
