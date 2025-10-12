import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAdminSearch, overrideLeaguePlan, toggleLeagueDiscord } from '../api/admin'
import { useAuth } from './useAuth'
import type { AdminLeagueSummary, AdminSearchResponse } from '../types/admin'
import type { BillingPlanTier } from '../types/billing'

const MOCK_ADMIN_RESPONSE: AdminSearchResponse = {
  users: [
    {
      id: 'mock-user-1',
      discordUsername: 'FounderOne',
      email: 'founder@gridboss.app',
      createdAt: new Date().toISOString(),
      leaguesOwned: 2,
      billingPlan: 'ELITE',
      subscriptionStatus: 'active',
      stripeCustomerId: 'cus_mock',
    },
  ],
  leagues: [
    {
      id: 'mock-league-1',
      name: 'GridBoss Premier',
      slug: 'gridboss-premier',
      plan: 'ELITE',
      driverLimit: 9999,
      driverCount: 240,
      ownerId: 'mock-user-1',
      ownerDiscordUsername: 'FounderOne',
      ownerEmail: 'founder@gridboss.app',
      billingPlan: 'ELITE',
      discordActive: true,
    },
    {
      id: 'mock-league-2',
      name: 'Rookie Cup',
      slug: 'rookie-cup',
      plan: 'FREE',
      driverLimit: 20,
      driverCount: 19,
      ownerId: 'mock-user-1',
      ownerDiscordUsername: 'FounderOne',
      ownerEmail: 'founder@gridboss.app',
      billingPlan: 'FREE',
      discordActive: false,
    },
  ],
}

interface ToggleArgs {
  leagueId: string
  isActive: boolean
}

interface PlanOverrideArgs {
  leagueId: string
  plan: BillingPlanTier
}

export function useAdminConsole() {
  const { accessToken, isBypassAuth, isFounder } = useAuth()
  const queryClient = useQueryClient()

  const adminModeEnabled = import.meta.env.VITE_ADMIN_MODE === 'true'
  const isProduction = import.meta.env.MODE === 'production'

  const [query, setQuery] = useState('')
  const [mockData, setMockData] = useState<AdminSearchResponse>(MOCK_ADMIN_RESPONSE)

  const shouldFetch = adminModeEnabled && isFounder && Boolean(accessToken) && !isBypassAuth

  const searchQuery = useQuery({
    queryKey: ['admin-search', query],
    queryFn: () => fetchAdminSearch(accessToken ?? '', query),
    enabled: shouldFetch,
    staleTime: 30_000,
  })

  const data = useMemo<AdminSearchResponse>(() => {
    if (shouldFetch) {
      return searchQuery.data ?? { users: [], leagues: [] }
    }
    return mockData
  }, [searchQuery.data, shouldFetch, mockData])

  const refresh = async () => {
    if (shouldFetch) {
      const result = await searchQuery.refetch()
      return result.data ?? { users: [], leagues: [] }
    }
    return mockData
  }

  const resolvedError = useMemo(() => {
    if (!shouldFetch) {
      return null
    }
    if (!searchQuery.error) {
      return null
    }
    if (searchQuery.error instanceof Error) {
      return searchQuery.error
    }
    return new Error('Unable to load admin data')
  }, [shouldFetch, searchQuery.error])

  const [togglingLeagueId, setTogglingLeagueId] = useState<string | null>(null)
  const toggleMutation = useMutation({
    mutationFn: async ({ leagueId, isActive }: ToggleArgs) => {
      if (!shouldFetch) {
        let updatedResult: AdminLeagueSummary | undefined
        setMockData((current) => {
          const existing = current.leagues.find((league) => league.id === leagueId)
          if (!existing) {
            updatedResult = undefined
            return current
          }
          const nextLeague = { ...existing, discordActive: isActive }
          updatedResult = nextLeague
          return {
            ...current,
            leagues: current.leagues.map((league) =>
              league.id === leagueId ? nextLeague : league,
            ),
          }
        })
        if (!updatedResult) {
          throw new Error('League not found in mock data')
        }
        return updatedResult
      }

      if (!accessToken) {
        throw new Error('Not authenticated')
      }
      return toggleLeagueDiscord(accessToken, leagueId, isActive)
    },
    onMutate: ({ leagueId }) => {
      setTogglingLeagueId(leagueId)
    },
    onSuccess: (updated) => {
      if (shouldFetch) {
        queryClient.setQueryData<AdminSearchResponse>(['admin-search', query], (current) => {
          if (!current) {
            return current
          }
          return {
            ...current,
            leagues: current.leagues.map((league) =>
              league.id === updated.id ? updated : league,
            ),
          }
        })
      }
    },
    onSettled: () => {
      setTogglingLeagueId(null)
    },
  })

  const [planUpdatingLeagueId, setPlanUpdatingLeagueId] = useState<string | null>(null)
  const planMutation = useMutation({
    mutationFn: async ({ leagueId, plan }: PlanOverrideArgs) => {
      if (!shouldFetch) {
        let updatedResult: AdminLeagueSummary | undefined
        setMockData((current) => {
          const existing = current.leagues.find((league) => league.id === leagueId)
          if (!existing) {
            updatedResult = undefined
            return current
          }
          const nextLeague = { ...existing, plan, billingPlan: plan }
          updatedResult = nextLeague
          return {
            ...current,
            leagues: current.leagues.map((league) =>
              league.id === leagueId ? nextLeague : league,
            ),
          }
        })
        if (!updatedResult) {
          throw new Error('League not found in mock data')
        }
        return updatedResult
      }

      if (!accessToken) {
        throw new Error('Not authenticated')
      }
      return overrideLeaguePlan(accessToken, leagueId, plan)
    },
    onMutate: ({ leagueId }) => {
      setPlanUpdatingLeagueId(leagueId)
    },
    onSuccess: (updated) => {
      if (shouldFetch) {
        queryClient.setQueryData<AdminSearchResponse>(['admin-search', query], (current) => {
          if (!current) {
            return current
          }
          return {
            ...current,
            leagues: current.leagues.map((league) =>
              league.id === updated.id ? updated : league,
            ),
          }
        })
      }
    },
    onSettled: () => {
      setPlanUpdatingLeagueId(null)
    },
  })

  const toggleDiscord = async (leagueId: string, isActive: boolean) => {
    await toggleMutation.mutateAsync({ leagueId, isActive })
  }

  const overridePlan = async (leagueId: string, plan: BillingPlanTier) => {
    await planMutation.mutateAsync({ leagueId, plan })
  }

  return {
    adminEnabled: adminModeEnabled,
    isFounder,
    isProduction,
    query,
    setQuery,
    data,
    isLoading: shouldFetch ? searchQuery.isLoading : false,
    error: resolvedError,
    refresh,
    toggleDiscord,
    overridePlan,
    togglingLeagueId,
    planUpdatingLeagueId,
    isMutating: toggleMutation.isPending || planMutation.isPending,
    shouldFetch,
  }
}
