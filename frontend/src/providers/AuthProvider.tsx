import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { fetchCurrentUser, logoutRequest, UnauthorizedError } from '../api/auth'
import {
  captureTokenFromUrl,
  clearAccessToken,
  readAccessToken,
  storeAccessToken,
} from '../lib/token-storage'
import type { MeResponse } from '../types/auth'
import type { AuthContextValue } from './AuthContext'
import { AuthContext } from './AuthContext'

const MOCK_PROFILE: MeResponse = {
  user: {
    id: 'demo-user',
    discord_id: null,
    discord_username: 'Demo Driver',
    avatar_url: null,
    email: 'demo@gridboss.app',
    is_founder: true,
  },
  memberships: [
    {
      league_id: 'demo-league',
      league_slug: 'demo-gp',
      league_name: 'Demo GP',
      role: 'OWNER',
    },
  ],
  billingPlan: { plan: 'PRO', current_period_end: null },
}

const createMockProfile = (): MeResponse => ({
  user: { ...MOCK_PROFILE.user },
  memberships: MOCK_PROFILE.memberships.map((membership) => ({
    ...membership,
  })),
  billingPlan: MOCK_PROFILE.billingPlan
    ? { ...MOCK_PROFILE.billingPlan }
    : null,
})

export function AuthProvider({
  children,
}: {
  children: React.ReactNode
}): ReactElement {
  const [profile, setProfile] = useState<AuthContextValue['profile']>(null)
  const [accessToken, setAccessTokenState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const bypassAuth = import.meta.env.VITE_BYPASS_AUTH === 'true'

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

    if (bypassAuth) {
      assignAccessToken(null)
      setProfile(createMockProfile())
      setIsLoading(false)
      return
    }

    const tokenFromUrl = captureTokenFromUrl()
    const token = tokenFromUrl ?? readAccessToken()
    assignAccessToken(token ?? null)

    if (!token) {
      setProfile(null)
      setIsLoading(false)
      return
    }

    await loadProfile(token)
  }, [assignAccessToken, bypassAuth, loadProfile])

  useEffect(() => {
    void initialize()
  }, [initialize])

  const refreshProfile = useCallback(async () => {
    if (bypassAuth) {
      setProfile(createMockProfile())
      assignAccessToken(null)
      return
    }

    const token = accessToken ?? readAccessToken()
    if (!token) {
      setProfile(null)
      assignAccessToken(null)
      return
    }

    await loadProfile(token)
  }, [accessToken, assignAccessToken, loadProfile, bypassAuth])

  const logout = useCallback(async () => {
    if (bypassAuth) {
      setProfile(createMockProfile())
      assignAccessToken(null)
      return
    }

    try {
      await logoutRequest()
    } catch (err) {
      console.error('Failed to logout', err)
    } finally {
      assignAccessToken(null)
      setProfile(null)
    }
  }, [assignAccessToken, bypassAuth])

  const value = useMemo<AuthContextValue>(
    () => ({
      profile,
      isLoading,
      error,
      isAuthenticated: Boolean(profile) || bypassAuth,
      isBypassAuth: bypassAuth,
      accessToken,
      refreshProfile,
      logout,
      setAccessToken: assignAccessToken,
    }),
    [
      profile,
      isLoading,
      error,
      accessToken,
      refreshProfile,
      logout,
      assignAccessToken,
      bypassAuth,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
