import { defineConfig } from '@playwright/test'

// End-to-end tests: real clicks against the built client and the API under
// gunicorn, fresh demo data per run (e2e/support/start-stack.sh). Uses the
// locally installed Google Chrome. npm run test:e2e
const port = Number(process.env.E2E_PORT ?? 5199)
// E2E_REUSE=1 runs against a stack that is already up (faster while writing tests;
// the data is then no longer fresh).
const reuse = process.env.E2E_REUSE === '1'

export default defineConfig({
  testDir: './e2e',
  // One database for the run: the journeys share it, so they run one after another.
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    channel: 'chrome',
    locale: 'de-DE',
    timezoneId: 'Europe/Berlin',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'node e2e/support/smtp-sink.ts',
      url: 'http://127.0.0.1:2526/messages',
      reuseExistingServer: reuse,
    },
    {
      command: 'bash e2e/support/start-stack.sh',
      url: `http://127.0.0.1:${port}/api/health`,
      reuseExistingServer: reuse,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'pipe',
    },
  ],
})
