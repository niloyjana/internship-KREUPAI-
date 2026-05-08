import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E tests of the AI Digital Workforce Platform.
 *
 * Targets the Next.js frontend at http://localhost:3000 with projects for
 * Chromium and Firefox. The webServer block starts the dev server
 * automatically if it is not already running.
 */
export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',

  /* Maximum time one test can run */
  timeout: 30_000,

  /* Expect timeout */
  expect: {
    timeout: 5_000,
  },

  /* Run tests in parallel */
  fullyParallel: true,

  /* Fail the build on CI if test.only is accidentally left in */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Reporter */
  reporter: process.env.CI ? 'html' : 'list',

  /* Shared settings for all projects */
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  /* Browser projects */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],

  /* Web server config -- starts the Next.js dev server if not running */
  webServer: {
    command: 'pnpm --filter web dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    cwd: '../../',
  },
});
