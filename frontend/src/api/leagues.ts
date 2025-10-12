import { apiFetch } from './client'
import { ApiError } from './auth'
import type {
  CreateLeagueRequest,
  LeagueRead,
  LeagueSummary,
  UpdateLeagueGeneralRequest,
} from '../types/leagues'
import type { LeagueRole } from '../types/auth'

function toSummary(
  league: LeagueRead,
  role: LeagueRole | null = null,
): LeagueSummary {
  return {
    id: league.id,
    name: league.name,
    slug: league.slug,
    plan: league.plan ?? null,
    driverLimit:
      typeof league.driver_limit === 'number' ? league.driver_limit : null,
    role,
  }
}

export async function fetchLeagues(token: string): Promise<LeagueSummary[]> {
  const response = await apiFetch('/leagues', { token })

  if (!response.ok) {
    throw new ApiError('Unable to load leagues', response.status)
  }

  const payload = (await response.json()) as LeagueRead[]
  return payload.map((league) => toSummary(league))
}

export async function createLeague(
  token: string,
  body: CreateLeagueRequest,
): Promise<LeagueSummary> {
  const response = await apiFetch('/leagues', {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 409) {
    throw new ApiError('Slug already in use', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to create league', response.status)
  }

  const payload = (await response.json()) as LeagueRead
  return toSummary(payload)
}

export async function updateLeagueGeneral(
  token: string,
  slug: string,
  body: UpdateLeagueGeneralRequest,
): Promise<LeagueSummary> {
  const response = await apiFetch(`/leagues/${slug}`, {
    method: 'PATCH',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 409) {
    throw new ApiError('Slug already in use', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to update league', response.status)
  }

  const payload = (await response.json()) as LeagueRead
  return toSummary(payload)
}
