import DOMPurify from 'dompurify'
import { marked } from 'marked'

const ALLOWED_TAGS = ['a', 'strong', 'em', 'ul', 'ol', 'li', 'p', 'br']
const ALLOWED_ATTR = ['href', 'title']

marked.setOptions({ gfm: true, breaks: true })

export function renderSafeMarkdown(markdown: string | null | undefined): string {
  if (!markdown) {
    return ''
  }

  const trimmed = markdown.trim()
  if (!trimmed) {
    return ''
  }

  const rawHtml = marked.parse(trimmed)
  const sanitized = DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS: ['img', 'script', 'style'],
    FORBID_ATTR: ['style', 'onerror', 'onclick'],
  })

  return sanitized
}

