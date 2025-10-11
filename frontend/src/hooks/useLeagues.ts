import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchLeagues } from '../api/leagues'
import type { LeagueSummary } from '../types/leagues'
import type { LeagueRole } from '../types/auth'
import { useAuth } from './useAuth'

interface UseLeaguesResult {
  leagues: LeagueSummary[]
  isLoading: boolean
  isFetching: boolean
  error: Error | null
  refetch: () => Promise<LeagueSummary[] | undefined>
  isBypass: boolean
  addLocalLeague: (league: LeagueSummary) => void
}

export function useLeagues(): UseLeaguesResult {
  const { accessToken, profile, isBypassAuth } = useAuth()

  const rolesMap = useMemo(() => {
    const map = new Map<string, LeagueRole>()
    for (const membership of profile?.memberships ?? []) {
      map.set(membership.league_id, membership.role)
    }
    return map
  }, [profile?.memberships])

  const shouldFetch = Boolean(accessToken)

  const query = useQuery<LeagueSummary[]>({
    queryKey: ['leagues'],
    queryFn: () => fetchLeagues(accessToken ?? ''),
    enabled: shouldFetch,
    staleTime: 60_000,
  })

  const leaguesFromApi = useMemo(() => {
    if (!query.data) {
      return [] as LeagueSummary[]
    }
    return query.data.map((league) => ({
      ...league,
      role: league.role ?? rolesMap.get(league.id) ?? null,
    }))
  }, [query.data, rolesMap])

  const fallbackLeagues = useMemo<LeagueSummary[]>(() => {
    if (!profile) {
      return []
    }

    return profile.memberships.map((membership) => ({
      id: membership.league_id,
      name: membership.league_name,
      slug: membership.league_slug,
      plan: profile.billingPlan?.plan ?? 'FREE',
      driverLimit: profile.billingPlan?.plan === 'ELITE' ? 9999 : profile.billingPlan?.plan === 'PRO' ? 100 : 20,
      role: membership.role,
    }))
  }, [profile])

  const [mockLeagues, setMockLeagues] = useState<LeagueSummary[]>(fallbackLeagues)

  useEffect(() => {
    if (!shouldFetch) {
      setMockLeagues(fallbackLeagues)
    }
  }, [fallbackLeagues, shouldFetch])

  const leagues = shouldFetch ? leaguesFromApi : mockLeagues

  const refetch = async () => {
    if (!shouldFetch) {
      return leagues
    }
    const result = await query.refetch()
    return result.data
  }

  return {
    leagues,
    isLoading: shouldFetch ? query.isLoading : false,
    isFetching: shouldFetch ? query.isFetching : false,
    error: shouldFetch ? query.error ?? null : null,
    refetch,
    isBypass: isBypassAuth,
    addLocalLeague: (league: LeagueSummary) => {
      setMockLeagues((current) => [...current, league])
    },
  }
}
