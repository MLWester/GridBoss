const ACCESS_TOKEN_KEY = 'gridboss.access_token'

export function storeAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function readAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function captureTokenFromUrl(): string | null {
  const currentUrl = new URL(window.location.href)
  const accessToken = currentUrl.searchParams.get('access_token')

  if (!accessToken) {
    return readAccessToken()
  }

  storeAccessToken(accessToken)
  currentUrl.searchParams.delete('access_token')
  const nextSearch = currentUrl.searchParams.toString()
  const cleanedUrl = `${currentUrl.pathname}${nextSearch ? `?${nextSearch}` : ''}${currentUrl.hash}`
  window.history.replaceState({}, '', cleanedUrl)

  return accessToken
}
