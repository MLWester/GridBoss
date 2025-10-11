import { apiFetch } from './client'
import { clearAccessToken, storeAccessToken } from '../lib/token-storage'
import type { MeResponse, TokenResponse } from '../types/auth'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export class UnauthorizedError extends Error {
  constructor(message = 'Session expired') {
    super(message)
  }
}

async function parseJson<T>(response: Response): Promise<Partial<T>> {
  const text = await response.text()
  if (!text) {
    return {}
  }
  return JSON.parse(text) as Partial<T>
}

export async function refreshAccessToken(): Promise<string> {
  const response = await apiFetch('/auth/refresh', {
    method: 'POST',
    token: null,
  })

  if (response.status === 401) {
    clearAccessToken()
    throw new UnauthorizedError()
  }

  if (!response.ok) {
    throw new ApiError('Unable to refresh session', response.status)
  }

  const payload = await parseJson<TokenResponse>(response)
  if (!('access_token' in payload) || !payload.access_token) {
    throw new ApiError('Refresh response missing access token', response.status)
  }

  storeAccessToken(payload.access_token)
  return payload.access_token
}

export async function fetchCurrentUser(
  accessToken: string,
  onTokenRefreshed: (token: string) => void,
): Promise<MeResponse> {
  let response: Response

  try {
    response = await apiFetch('/auth/me', { token: accessToken })
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : 'Failed to load profile',
      0,
    )
  }

  if (response.status === 401) {
    const newToken = await refreshAccessToken()
    onTokenRefreshed(newToken)
    response = await apiFetch('/auth/me', { token: newToken })
    if (response.status === 401) {
      clearAccessToken()
      throw new UnauthorizedError()
    }
  }

  if (!response.ok) {
    throw new ApiError('Unable to load account', response.status)
  }

  const me = await parseJson<MeResponse>(response)
  return me as MeResponse
}

export async function logoutRequest(): Promise<void> {
  const response = await apiFetch('/auth/logout', { method: 'POST' })
  if (!response.ok && response.status !== 204) {
    throw new ApiError('Failed to logout', response.status)
  }
}
