import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'

export async function scanAccessibility(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze()

  const serious = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  )

  if (serious.length > 0) {
    const messages = serious
      .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.html).join(', ')}`)
      .join('\n')
    throw new Error(`Accessibility violations detected:\n${messages}`)
  }
}
