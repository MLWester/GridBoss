import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchLeagueSeasons, fetchLeagueStandings } from '../api/standings'
import { useAuth } from './useAuth'
import type { SeasonSummary, StandingEntrySummary } from '../types/standings'

interface UseLeagueStandingsResult {
  seasons: SeasonSummary[]
  selectedSeasonId: string | null
  setSelectedSeasonId: (seasonId: string) => void
  standings: StandingEntrySummary[]
  isLoading: boolean
  isFetching: boolean
  error: Error | null
  refresh: () => Promise<void>
  isBypass: boolean
}

function createMockSeasons(slug: string): SeasonSummary[] {
  return [
    { id: `${slug}-season-2025`, name: '2025 Championship', isActive: true },
    { id: `${slug}-season-2024`, name: '2024 Championship', isActive: false },
  ]
}

function createMockStandings(slug: string, seasonId: string): StandingEntrySummary[] {
  const base = slug || 'demo'
  const entries: StandingEntrySummary[] = [
    {
      driverId: `${base}-driver-1`,
      driverName: 'Jamie Chen',
      teamName: 'Aurora GP',
      points: seasonId.endsWith('2025') ? 112 : 198,
      wins: seasonId.endsWith('2025') ? 3 : 6,
      bestFinish: 1,
      podiums: seasonId.endsWith('2025') ? 5 : 10,
    },
    {
      driverId: `${base}-driver-2`,
      driverName: 'Alex Rivera',
      teamName: 'Velocity Racing',
      points: seasonId.endsWith('2025') ? 110 : 176,
      wins: seasonId.endsWith('2025') ? 2 : 4,
      bestFinish: 1,
      podiums: seasonId.endsWith('2025') ? 6 : 9,
    },
    {
      driverId: `${base}-driver-3`,
      driverName: 'Morgan Patel',
      teamName: 'Midnight Apex',
      points: seasonId.endsWith('2025') ? 98 : 160,
      wins: seasonId.endsWith('2025') ? 1 : 3,
      bestFinish: 1,
      podiums: seasonId.endsWith('2025') ? 4 : 8,
    },
    {
      driverId: `${base}-driver-4`,
      driverName: 'Riley Torres',
      teamName: 'Aurora GP',
      points: seasonId.endsWith('2025') ? 76 : 140,
      wins: 0,
      bestFinish: 2,
      podiums: seasonId.endsWith('2025') ? 2 : 5,
    },
  ]

  return entries
}

export function useLeagueStandings(slug: string): UseLeagueStandingsResult {
  const { accessToken, isBypassAuth } = useAuth()
  const shouldFetch = Boolean(accessToken)
  const queryClient = useQueryClient()

  const fallbackSeasons = useMemo(() => createMockSeasons(slug || 'demo'), [slug])
  const [localSeasons, setLocalSeasons] = useState<SeasonSummary[]>(fallbackSeasons)
  const [localStandings, setLocalStandings] = useState<Record<string, StandingEntrySummary[]>>(() => {
    const initial: Record<string, StandingEntrySummary[]> = {}
    for (const season of fallbackSeasons) {
      initial[season.id] = createMockStandings(slug, season.id)
    }
    return initial
  })

  useEffect(() => {
    const seasons = createMockSeasons(slug || 'demo')
    setLocalSeasons(seasons)
    setLocalStandings(() => {
      const map: Record<string, StandingEntrySummary[]> = {}
      for (const season of seasons) {
        map[season.id] = createMockStandings(slug, season.id)
      }
      return map
    })
  }, [slug])

  const seasonsQuery = useQuery<SeasonSummary[]>({
    queryKey: ['league-seasons', slug],
    queryFn: () => fetchLeagueSeasons(accessToken ?? '', slug),
    enabled: shouldFetch && Boolean(slug),
    staleTime: 60_000,
  })

  const [selectedSeasonId, setSelectedSeasonIdState] = useState<string | null>(null)

  useEffect(() => {
    const availableSeasons = shouldFetch ? seasonsQuery.data ?? [] : localSeasons
    if (availableSeasons.length === 0) {
      setSelectedSeasonIdState(null)
      return
    }
    const activeSeason = availableSeasons.find((season) => season.isActive)
    const preferred = activeSeason ?? availableSeasons[0]
    setSelectedSeasonIdState((current) => {
      if (current && availableSeasons.some((season) => season.id === current)) {
        return current
      }
      return preferred.id
    })
  }, [shouldFetch, seasonsQuery.data, localSeasons])

  const standingsQuery = useQuery<StandingEntrySummary[]>({
    queryKey: ['league-standings', slug, selectedSeasonId],
    queryFn: () => fetchLeagueStandings(accessToken ?? '', slug, selectedSeasonId ?? ''),
    enabled: shouldFetch && Boolean(slug) && Boolean(selectedSeasonId),
    staleTime: 30_000,
  })

  const seasons = shouldFetch ? seasonsQuery.data ?? [] : localSeasons
  const standings = shouldFetch
    ? standingsQuery.data ?? []
    : selectedSeasonId
      ? localStandings[selectedSeasonId] ?? []
      : []

  const setSelectedSeasonId = useCallback(
    (seasonId: string) => {
      setSelectedSeasonIdState(seasonId)
    },
    [],
  )

  const refresh = useCallback(async () => {
    if (!selectedSeasonId) {
      return
    }
    if (!shouldFetch) {
      setLocalStandings((current) => ({
        ...current,
        [selectedSeasonId]: createMockStandings(slug, selectedSeasonId),
      }))
      return
    }
    await queryClient.invalidateQueries({ queryKey: ['league-standings', slug, selectedSeasonId], exact: true })
  }, [selectedSeasonId, shouldFetch, queryClient, slug])

  return {
    seasons,
    selectedSeasonId,
    setSelectedSeasonId,
    standings,
    isLoading: shouldFetch ? seasonsQuery.isLoading || standingsQuery.isLoading : false,
    isFetching: shouldFetch ? standingsQuery.isFetching : false,
    error: shouldFetch ? seasonsQuery.error ?? standingsQuery.error ?? null : null,
    refresh,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
