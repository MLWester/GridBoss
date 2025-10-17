import { describe, expect, it } from 'vitest'
import { renderSafeMarkdown } from '../markdown'

describe('renderSafeMarkdown', () => {
  it('returns empty string for blank input', () => {
    expect(renderSafeMarkdown('   ')).toBe('')
    expect(renderSafeMarkdown(null)).toBe('')
  })

  it('converts markdown to sanitized html', () => {
    const result = renderSafeMarkdown('**Bold** _italic_\n\n- item one\n- item two')
    expect(result).toContain('<strong>Bold</strong>')
    expect(result).toContain('<em>italic</em>')
    expect(result).toContain('<ul>')
    expect(result).toContain('<li>item one</li>')
  })

  it('strips disallowed tags and attributes', () => {
    const result = renderSafeMarkdown(
      "<script>alert('xss')</script><a href=\"javascript:alert(1)\" onclick=\"hack()\">click</a>",
    )
    expect(result).not.toContain('script')
    expect(result).not.toContain('onclick')
    expect(result).not.toContain('javascript:')
    expect(result).toContain('<a')
  })
})

