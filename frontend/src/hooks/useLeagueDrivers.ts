import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkCreateDrivers as bulkCreateDriversRequest,
  fetchLeagueDrivers,
  fetchLeagueTeams,
  updateDriver as updateDriverRequest,
} from '../api/drivers'
import { useAuth } from './useAuth'
import type { BulkDriverInput, DriverSummary, UpdateDriverRequest } from '../types/drivers'
import type { TeamSummary } from '../types/teams'

interface UseLeagueDriversResult {
  drivers: DriverSummary[]
  teams: TeamSummary[]
  isLoading: boolean
  isFetching: boolean
  error: Error | null
  refetch: () => Promise<void>
  updateDriver: (driverId: string, payload: UpdateDriverRequest) => Promise<DriverSummary>
  bulkCreateDrivers: (items: BulkDriverInput[]) => Promise<DriverSummary[]>
  isBypass: boolean
}

interface MockDataset {
  drivers: DriverSummary[]
  teams: TeamSummary[]
}

function createMockDataset(slug: string): MockDataset {
  const teams: TeamSummary[] = [
    { id: 'aurora-gp', name: 'Aurora GP' },
    { id: 'velocity-racing', name: 'Velocity Racing' },
    { id: 'midnight-apex', name: 'Midnight Apex' },
  ]

  const drivers: DriverSummary[] = [
    {
      id: `${slug}-driver-1`,
      displayName: 'Jamie Chen',
      teamId: teams[0]?.id ?? null,
      teamName: teams[0]?.name ?? null,
      linkedUser: true,
      discordId: '1234567890',
      userName: 'jamie#2048',
    },
    {
      id: `${slug}-driver-2`,
      displayName: 'Alex Rivera',
      teamId: teams[1]?.id ?? null,
      teamName: teams[1]?.name ?? null,
      linkedUser: false,
      discordId: null,
      userName: null,
    },
    {
      id: `${slug}-driver-3`,
      displayName: 'Morgan Patel',
      teamId: teams[2]?.id ?? null,
      teamName: teams[2]?.name ?? null,
      linkedUser: true,
      discordId: '1029384756',
      userName: 'morgan#1080',
    },
  ]

  return { drivers, teams }
}

function resolveTeamName(teamId: string | null, teams: TeamSummary[]): string | null {
  if (!teamId) return null
  return teams.find((team) => team.id === teamId)?.name ?? null
}

export function useLeagueDrivers(slug: string): UseLeagueDriversResult {
  const { accessToken, isBypassAuth } = useAuth()
  const shouldFetch = Boolean(accessToken)
  const queryClient = useQueryClient()

  const mockDataset = useMemo(() => createMockDataset(slug || 'demo'), [slug])
  const [localDrivers, setLocalDrivers] = useState<DriverSummary[]>(mockDataset.drivers)
  const [localTeams, setLocalTeams] = useState<TeamSummary[]>(mockDataset.teams)

  useEffect(() => {
    setLocalDrivers(mockDataset.drivers)
    setLocalTeams(mockDataset.teams)
  }, [mockDataset])

  const driversQuery = useQuery<DriverSummary[]>({
    queryKey: ['league-drivers', slug],
    queryFn: () => fetchLeagueDrivers(accessToken ?? '', slug),
    enabled: shouldFetch && Boolean(slug),
    staleTime: 30_000,
  })

  const teamsQuery = useQuery<TeamSummary[]>({
    queryKey: ['league-teams', slug],
    queryFn: () => fetchLeagueTeams(accessToken ?? '', slug),
    enabled: shouldFetch && Boolean(slug),
    staleTime: 60_000,
  })

  const driversData = driversQuery.data
  const teamsData = teamsQuery.data

  const drivers = useMemo(() => {
    const remote = driversData ?? []
    return shouldFetch ? remote : localDrivers
  }, [shouldFetch, driversData, localDrivers])

  const teams = useMemo(() => {
    const remote = teamsData ?? []
    return shouldFetch ? remote : localTeams
  }, [shouldFetch, teamsData, localTeams])

  const refetch = useCallback(async () => {
    if (!shouldFetch) {
      return
    }
    await Promise.allSettled([
      queryClient.refetchQueries({ queryKey: ['league-drivers', slug], exact: true }),
      queryClient.refetchQueries({ queryKey: ['league-teams', slug], exact: true }),
    ])
  }, [shouldFetch, queryClient, slug])

  const updateDriver = useCallback(
    async (driverId: string, payload: UpdateDriverRequest) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const queryKey = ['league-drivers', slug]
        const previous = queryClient.getQueryData<DriverSummary[]>(queryKey) ?? []
        const optimisticTeamName =
          payload.team_id !== undefined ? resolveTeamName(payload.team_id ?? null, teams) : undefined

        const optimistic = previous.map((driver) =>
          driver.id === driverId
            ? {
                ...driver,
                displayName: payload.display_name ?? driver.displayName,
                teamId: payload.team_id ?? driver.teamId,
                teamName: optimisticTeamName ?? driver.teamName,
              }
            : driver,
        )

        queryClient.setQueryData(queryKey, optimistic)

        try {
          const updated = await updateDriverRequest(token, driverId, payload)
          queryClient.setQueryData(queryKey, (current: DriverSummary[] | undefined) =>
            (current ?? []).map((driver) => (driver.id === driverId ? updated : driver)),
          )
          return updated
        } catch (error) {
          queryClient.setQueryData(queryKey, previous)
          throw error
        }
      }

      const existing = localDrivers.find((driver) => driver.id === driverId) ?? null
      if (!existing) {
        throw new Error('Driver not found')
      }
      const nextDriver: DriverSummary = {
        ...existing,
        displayName: payload.display_name ?? existing.displayName,
        teamId: payload.team_id ?? existing.teamId,
        teamName:
          payload.team_id !== undefined
            ? resolveTeamName(payload.team_id ?? null, localTeams)
            : existing.teamName,
      }
      setLocalDrivers((current) =>
        current.map((driver) => (driver.id === driverId ? nextDriver : driver)),
      )
      return nextDriver
    },
    [slug, shouldFetch, accessToken, queryClient, teams, localTeams, localDrivers],
  )

  const bulkCreateDrivers = useCallback(
    async (items: BulkDriverInput[]) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const created = await bulkCreateDriversRequest(token, slug, items)
        const queryKey = ['league-drivers', slug]
        queryClient.setQueryData(queryKey, (current: DriverSummary[] | undefined) => {
          const existing = current ?? []
          return [...existing, ...created]
        })
        return created
      }

      const generated = items.map((item, index) => {
        const teamId = item.team_id ?? null
        return {
          id: `${slug || 'demo'}-local-${Date.now().toString(36)}-${index.toString(36)}`,
          displayName: item.display_name,
          teamId,
          teamName: resolveTeamName(teamId, localTeams),
          linkedUser: false,
          discordId: null,
          userName: null,
        } satisfies DriverSummary
      })
      setLocalDrivers((current) => [...current, ...generated])
      return generated
    },
    [slug, shouldFetch, accessToken, queryClient, localTeams],
  )

  const isLoading = shouldFetch ? driversQuery.isLoading || teamsQuery.isLoading : false
  const isFetching = shouldFetch ? driversQuery.isFetching || teamsQuery.isFetching : false
  const error = shouldFetch ? driversQuery.error ?? teamsQuery.error ?? null : null

  return {
    drivers,
    teams,
    isLoading,
    isFetching,
    error,
    refetch,
    updateDriver,
    bulkCreateDrivers,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
