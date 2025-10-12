import { defineConfig } from '@playwright/test'

const PORT = process.env.PORT ? Number.parseInt(process.env.PORT, 10) : 4173
const PORT_STRING = String(PORT)

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${PORT_STRING}`,
    trace: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${PORT_STRING}`,
    url: `http://127.0.0.1:${PORT_STRING}`,
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    env: {
      VITE_BYPASS_AUTH: 'true',
      VITE_ADMIN_MODE: 'true',
    },
  },
  reporter: [['list'], ['html', { open: 'never' }]],
})
