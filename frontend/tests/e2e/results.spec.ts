import { expect, test } from '@playwright/test'
import { scanAccessibility } from './utils'

test('results page allows submitting results with bypass data', async ({ page }) => {
  await page.goto('/leagues/demo-gp/results')
  await expect(page.getByRole('button', { name: /Submit results/i })).toBeVisible()

  await page.getByRole('button', { name: /Submit results/i }).click()
  await expect(page.getByText(/Results submitted/i)).toBeVisible()
  await scanAccessibility(page)
})
