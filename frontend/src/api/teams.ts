import { apiFetch } from './client'
import { ApiError } from './auth'
import type { TeamRead, TeamSummary } from '../types/teams'

function mapTeam(team: TeamRead): TeamSummary {
  return {
    id: team.id,
    name: team.name,
    driverIds: Array.isArray(team.driver_ids) ? [...team.driver_ids] : [],
    driverCount: typeof team.driver_count === 'number' ? team.driver_count : 0,
  }
}

export async function fetchLeagueTeams(token: string, slug: string): Promise<TeamSummary[]> {
  const response = await apiFetch(`/leagues/${slug}/teams`, {
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to load teams', response.status)
  }

  const payload = (await response.json()) as TeamRead[]
  return payload.map(mapTeam)
}

export async function createTeam(
  token: string,
  slug: string,
  body: { name: string; driver_ids: string[] },
): Promise<TeamSummary> {
  const response = await apiFetch(`/leagues/${slug}/teams`, {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 409) {
    throw new ApiError('A team with that name already exists', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to create team', response.status)
  }

  const payload = (await response.json()) as TeamRead
  return mapTeam(payload)
}

export async function updateTeam(
  token: string,
  teamId: string,
  body: { name?: string; driver_ids?: string[] },
): Promise<TeamSummary> {
  const response = await apiFetch(`/teams/${teamId}`, {
    method: 'PATCH',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 404) {
    throw new ApiError('Team not found', response.status)
  }

  if (response.status === 409) {
    throw new ApiError('A team with that name already exists', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to update team', response.status)
  }

  const payload = (await response.json()) as TeamRead
  return mapTeam(payload)
}

export async function deleteTeam(token: string, teamId: string): Promise<void> {
  const response = await apiFetch(`/teams/${teamId}`, {
    method: 'DELETE',
    token,
  })

  if (response.status === 404) {
    throw new ApiError('Team not found', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to delete team', response.status)
  }
}
