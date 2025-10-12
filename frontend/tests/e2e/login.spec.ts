import { expect, test } from '@playwright/test'
import { scanAccessibility } from './utils'

test('login page renders with Discord CTA', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: /Sign in with Discord/i })).toBeVisible()
  await expect(page.getByRole('button', { name: /Continue with Discord/i })).toBeVisible()
  await scanAccessibility(page)
})
