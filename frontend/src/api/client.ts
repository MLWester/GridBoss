import { API_URL } from '../lib/env'

interface ApiFetchOptions extends RequestInit {
  token?: string | null
}

export async function apiFetch(
  path: string,
  { token, headers, credentials, ...init }: ApiFetchOptions = {},
): Promise<Response> {
  const resolvedHeaders = new Headers(headers)

  if (token) {
    resolvedHeaders.set('Authorization', `Bearer ${token}`)
  }

  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      headers: resolvedHeaders,
      credentials: credentials ?? 'include',
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Network request failed'
    throw new Error(message)
  }
}
