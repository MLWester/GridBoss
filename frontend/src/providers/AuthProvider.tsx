import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchCurrentUser, logoutRequest, UnauthorizedError } from '../api/auth'
import { captureTokenFromUrl, clearAccessToken, readAccessToken, storeAccessToken } from '../lib/token-storage'
import type { AuthContextValue } from './AuthContext'
import { AuthContext } from './AuthContext'

export function AuthProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [profile, setProfile] = useState<AuthContextValue['profile']>(null)
  const [accessToken, setAccessTokenState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const assignAccessToken = useCallback((token: string | null) => {
    setAccessTokenState(token)
    if (token) {
      storeAccessToken(token)
    } else {
      clearAccessToken()
    }
  }, [])

  const loadProfile = useCallback(
    async (token: string) => {
      setIsLoading(true)
      setError(null)
      try {
        const me = await fetchCurrentUser(token, assignAccessToken)
        setProfile(me)
      } catch (err) {
        if (err instanceof UnauthorizedError) {
          assignAccessToken(null)
          setProfile(null)
        } else if (err instanceof Error) {
          setError(err.message)
        } else {
          setError('Unexpected error while loading profile')
        }
      } finally {
        setIsLoading(false)
      }
    },
    [assignAccessToken],
  )

  const initialize = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    const tokenFromUrl = captureTokenFromUrl()
    const token = tokenFromUrl ?? readAccessToken()
    assignAccessToken(token ?? null)

    if (!token) {
      setProfile(null)
      setIsLoading(false)
      return
    }

    await loadProfile(token)
  }, [assignAccessToken, loadProfile])

  useEffect(() => {
    void initialize()
  }, [initialize])

  const refreshProfile = useCallback(async () => {
    const token = accessToken ?? readAccessToken()
    if (!token) {
      setProfile(null)
      assignAccessToken(null)
      return
    }

    await loadProfile(token)
  }, [accessToken, assignAccessToken, loadProfile])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } catch (err) {
      console.error('Failed to logout', err)
    } finally {
      assignAccessToken(null)
      setProfile(null)
    }
  }, [assignAccessToken])

  const value = useMemo<AuthContextValue>(() => ({
    profile,
    isLoading,
    error,
    isAuthenticated: Boolean(profile),
    accessToken,
    refreshProfile,
    logout,
    setAccessToken: assignAccessToken,
  }), [profile, isLoading, error, accessToken, refreshProfile, logout, assignAccessToken])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
