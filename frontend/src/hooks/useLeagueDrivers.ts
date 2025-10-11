import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkCreateDrivers as bulkCreateDriversRequest,
  fetchLeagueDrivers,
  updateDriver as updateDriverRequest,
} from '../api/drivers'
import { createTeam, deleteTeam, fetchLeagueTeams, updateTeam as updateTeamRequest } from '../api/teams'
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
  createTeam: (payload: { name: string; driverIds: string[] }) => Promise<TeamSummary>
  updateTeam: (teamId: string, payload: { name: string; driverIds: string[] }) => Promise<TeamSummary>
  deleteTeam: (teamId: string) => Promise<void>
  isBypass: boolean
}

interface MockDataset {
  drivers: DriverSummary[]
  teams: TeamSummary[]
}

function createMockDataset(slug: string): MockDataset {
  const teams: TeamSummary[] = [
    { id: 'aurora-gp', name: 'Aurora GP', driverIds: [], driverCount: 0 },
    { id: 'velocity-racing', name: 'Velocity Racing', driverIds: [], driverCount: 0 },
    { id: 'midnight-apex', name: 'Midnight Apex', driverIds: [], driverCount: 0 },
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

  for (const driver of drivers) {
    if (!driver.teamId) continue
    const team = teams.find((item) => item.id === driver.teamId)
    if (team) {
      team.driverIds.push(driver.id)
      team.driverCount = team.driverIds.length
    }
  }

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
      const previousTeamId = existing.teamId
      const nextTeamId = nextDriver.teamId
      if (previousTeamId !== nextTeamId) {
        setLocalTeams((current) =>
          current.map((team) => {
            if (team.id === previousTeamId) {
              const remaining = team.driverIds.filter((id) => id !== driverId)
              return {
                ...team,
                driverIds: remaining,
                driverCount: remaining.length,
              }
            }
            if (team.id === nextTeamId && nextTeamId) {
              const updatedIds = team.driverIds.includes(driverId)
                ? team.driverIds
                : [...team.driverIds, driverId]
              return {
                ...team,
                driverIds: updatedIds,
                driverCount: updatedIds.length,
              }
            }
            return team
          }),
        )
      }
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
      setLocalTeams((current) =>
        current.map((team) => {
          const additions = generated.filter((driver) => driver.teamId === team.id).map((driver) => driver.id)
          if (additions.length === 0) {
            return team
          }
          const newIds = Array.from(new Set([...team.driverIds, ...additions]))
          return {
            ...team,
            driverIds: newIds,
            driverCount: newIds.length,
          }
        }),
      )
      return generated
    },
    [slug, shouldFetch, accessToken, queryClient, localTeams],
  )

  const createTeamEntry = useCallback(
    async (payload: { name: string; driverIds: string[] }) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const created = await createTeam(token, slug, { name: payload.name, driver_ids: payload.driverIds })
        const teamKey = ['league-teams', slug]
        queryClient.setQueryData(teamKey, (current: TeamSummary[] | undefined) => {
          const existing = current ?? []
          return [...existing, created]
        })

        if (payload.driverIds.length > 0) {
          const driverKey = ['league-drivers', slug]
          queryClient.setQueryData(driverKey, (current: DriverSummary[] | undefined) =>
            (current ?? []).map((driver) =>
              payload.driverIds.includes(driver.id)
                ? { ...driver, teamId: created.id, teamName: created.name }
                : driver,
            ),
          )
        }

        return created
      }

      const newTeam: TeamSummary = {
        id: `${slug || 'demo'}-team-${Date.now().toString(36)}`,
        name: payload.name,
        driverIds: [...payload.driverIds],
        driverCount: payload.driverIds.length,
      }

      setLocalTeams((current) => {
        const sanitized = current.map((team) => {
          if (payload.driverIds.some((driverId) => team.driverIds.includes(driverId))) {
            const remaining = team.driverIds.filter((driverId) => !payload.driverIds.includes(driverId))
            return {
              ...team,
              driverIds: remaining,
              driverCount: remaining.length,
            }
          }
          return team
        })
        return [...sanitized, newTeam]
      })

      if (payload.driverIds.length > 0) {
        setLocalDrivers((current) =>
          current.map((driver) =>
            payload.driverIds.includes(driver.id)
              ? { ...driver, teamId: newTeam.id, teamName: newTeam.name }
              : driver,
          ),
        )
      }

      return newTeam
    },
    [slug, shouldFetch, accessToken, queryClient],
  )

  const updateTeamEntry = useCallback(
    async (teamId: string, payload: { name: string; driverIds: string[] }) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const updated = await updateTeamRequest(token, teamId, { name: payload.name, driver_ids: payload.driverIds })
        const teamKey = ['league-teams', slug]
        const previousTeams = queryClient.getQueryData<TeamSummary[]>(teamKey) ?? []
        const previousTeam = previousTeams.find((team) => team.id === teamId) ?? null

        queryClient.setQueryData(teamKey, previousTeams.map((team) => (team.id === teamId ? updated : team)))

        const previousDriverIds = previousTeam?.driverIds ?? []
        const removed = previousDriverIds.filter((id) => !payload.driverIds.includes(id))

        const driverKey = ['league-drivers', slug]
        queryClient.setQueryData(driverKey, (current: DriverSummary[] | undefined) =>
          (current ?? []).map((driver) => {
            if (payload.driverIds.includes(driver.id)) {
              return { ...driver, teamId: updated.id, teamName: updated.name }
            }
            if (removed.includes(driver.id)) {
              return { ...driver, teamId: null, teamName: null }
            }
            if (driver.teamId === updated.id && !payload.driverIds.includes(driver.id)) {
              return { ...driver, teamId: null, teamName: null }
            }
            return driver
          }),
        )

        return updated
      }

      const driverIdsSet = new Set(payload.driverIds)
      const nextTeam: TeamSummary = {
        id: teamId,
        name: payload.name,
        driverIds: [...driverIdsSet],
        driverCount: driverIdsSet.size,
      }

      const previousTeam = localTeams.find((team) => team.id === teamId) ?? null
      const previousDriverIds = previousTeam?.driverIds ?? []
      const removed = previousDriverIds.filter((id) => !driverIdsSet.has(id))

      setLocalTeams((current) =>
        current.map((team) => {
          if (team.id === teamId) {
            return nextTeam
          }
          if (team.driverIds.some((driverId) => driverIdsSet.has(driverId))) {
            const remaining = team.driverIds.filter((driverId) => !driverIdsSet.has(driverId))
            return { ...team, driverIds: remaining, driverCount: remaining.length }
          }
          return team
        }),
      )

      setLocalDrivers((current) =>
        current.map((driver) => {
          if (driverIdsSet.has(driver.id)) {
            return { ...driver, teamId: nextTeam.id, teamName: nextTeam.name }
          }
          if (removed.includes(driver.id)) {
            return { ...driver, teamId: null, teamName: null }
          }
          if (driver.teamId === nextTeam.id && !driverIdsSet.has(driver.id)) {
            return { ...driver, teamId: null, teamName: null }
          }
          return driver
        }),
      )

      return nextTeam
    },
    [slug, shouldFetch, accessToken, queryClient, localTeams],
  )

  const deleteTeamEntry = useCallback(
    async (teamId: string) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const teamKey = ['league-teams', slug]
        const previousTeams = queryClient.getQueryData<TeamSummary[]>(teamKey) ?? []
        const target = previousTeams.find((team) => team.id === teamId) ?? null

        await deleteTeam(token, teamId)
        queryClient.setQueryData(
          teamKey,
          previousTeams.filter((team) => team.id !== teamId),
        )

        if (target && target.driverIds.length > 0) {
          const driverKey = ['league-drivers', slug]
          queryClient.setQueryData(driverKey, (current: DriverSummary[] | undefined) =>
            (current ?? []).map((driver) =>
              target.driverIds.includes(driver.id) ? { ...driver, teamId: null, teamName: null } : driver,
            ),
          )
        }
        return
      }

      const target = localTeams.find((team) => team.id === teamId) ?? null
      setLocalTeams((current) => current.filter((team) => team.id !== teamId))

      if (target && target.driverIds.length > 0) {
        setLocalDrivers((current) =>
          current.map((driver) =>
            target.driverIds.includes(driver.id) ? { ...driver, teamId: null, teamName: null } : driver,
          ),
        )
      }
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
    createTeam: createTeamEntry,
    updateTeam: updateTeamEntry,
    deleteTeam: deleteTeamEntry,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
