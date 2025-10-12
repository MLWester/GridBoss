import { expect, test } from '@playwright/test'
import { scanAccessibility } from './utils'

test('dashboard allows creating a league in bypass mode', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Your leagues/i })).toBeVisible()

  await page.getByRole('button', { name: /Create league/i }).click()
  await page.getByRole('textbox', { name: /League name/i }).fill('E2E League')
  await page.getByRole('textbox', { name: /Slug/i }).fill('e2e-league')
  await page.getByRole('button', { name: /Simulate League/i }).click()

  await expect(page.getByText(/E2E League/)).toBeVisible()
  await scanAccessibility(page)
})
