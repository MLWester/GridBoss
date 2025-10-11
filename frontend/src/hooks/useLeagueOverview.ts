import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchLeagueOverview } from '../api/leagueOverview'
import { useAuth } from './useAuth'
import type { LeagueOverviewData, LeagueResultSummary, LeagueEventSummary } from '../types/leagues'
import type { LeagueSummary } from '../types/leagues'

interface UseLeagueOverviewResult {
  overview: LeagueOverviewData | null
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<LeagueOverviewData | null>
  isBypass: boolean
}

function buildFallbackOverview(slug: string, league: LeagueSummary | null): LeagueOverviewData {
  const safeSlug = slug || 'demo-league'
  const leagueSummary: LeagueSummary =
    league ?? {
      id: safeSlug,
      name: safeSlug
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (match) => match.toUpperCase()),
      slug: safeSlug,
      plan: 'FREE',
      driverLimit: 20,
      role: null,
    }

  const now = new Date()
  const nextEventStart = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  const recentEventDate = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000)

  const nextEvent: LeagueEventSummary = {
    id: `${safeSlug}-next-event`,
    name: `${leagueSummary.name} Grand Prix`,
    track: 'TBD Circuit',
    startTime: nextEventStart.toISOString(),
    status: 'SCHEDULED',
  }

  const recentResult: LeagueResultSummary = {
    event: {
      id: `${safeSlug}-recent-event`,
      name: `${leagueSummary.name} Test Event`,
      track: 'GridBoss Arena',
      startTime: recentEventDate.toISOString(),
      status: 'COMPLETED',
    },
    podium: [
      { driverName: 'Jamie Chen', teamName: 'Aurora GP', position: 1, points: 25 },
      { driverName: 'Alex Rivera', teamName: 'Velocity Racing', position: 2, points: 18 },
      { driverName: 'Morgan Patel', teamName: 'Midnight Apex', position: 3, points: 15 },
    ],
  }

  return {
    league: {
      ...leagueSummary,
      description: `This is a preview overview for ${leagueSummary.name}. Upcoming PBIs will hydrate this page with live data.`,
    },
    nextEvent,
    recentResult,
    discordLinked: false,
  }
}

export function useLeagueOverview(slug: string): UseLeagueOverviewResult {
  const { accessToken, isBypassAuth, memberships, billingPlan } = useAuth()

  const leagueFromMembership = useMemo(() => {
    const membership = memberships.find((item) => item.league_slug === slug)
    if (!membership) {
      return null
    }
    return {
      id: membership.league_id,
      name: membership.league_name,
      slug: membership.league_slug,
      plan: billingPlan?.plan ?? 'FREE',
      driverLimit: billingPlan?.plan === 'ELITE' ? 9999 : billingPlan?.plan === 'PRO' ? 100 : 20,
      role: membership.role,
    }
  }, [memberships, slug, billingPlan?.plan])

  const fallback = useMemo(() => buildFallbackOverview(slug, leagueFromMembership), [slug, leagueFromMembership])

  const shouldFetch = Boolean(accessToken)

  const query = useQuery<LeagueOverviewData>({
    queryKey: ['league-overview', slug],
    queryFn: () => fetchLeagueOverview(accessToken ?? '', slug),
    enabled: shouldFetch,
    staleTime: 60_000,
  })

  const overview = shouldFetch ? query.data ?? null : fallback

  const refetch = async () => {
    if (!shouldFetch) {
      return fallback
    }
    const result = await query.refetch()
    return result.data ?? null
  }

  return {
    overview,
    isLoading: shouldFetch ? query.isLoading : false,
    error: shouldFetch ? query.error ?? null : null,
    refetch,
    isBypass: isBypassAuth,
  }
}
