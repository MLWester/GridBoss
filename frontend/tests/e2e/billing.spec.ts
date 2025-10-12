import { expect, test } from '@playwright/test'
import { scanAccessibility } from './utils'

test('billing page allows plan upgrade simulation', async ({ page }) => {
  await page.goto('/billing')
  await expect(page.getByRole('heading', { name: /Billing overview/i })).toBeVisible()

  const upgradeButton = page.getByRole('button', { name: /Upgrade to Pro/i })
  await expect(upgradeButton).toBeEnabled()
  await upgradeButton.click()

  await expect(page.getByText(/Pro checkout started/i)).toBeVisible()
  await scanAccessibility(page)
})
