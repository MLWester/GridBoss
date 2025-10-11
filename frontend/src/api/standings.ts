import { apiFetch } from './client'
import { ApiError } from './auth'
import type { SeasonRead, SeasonSummary, StandingEntryRead, StandingEntrySummary } from '../types/standings'

function mapSeason(season: SeasonRead): SeasonSummary {
  return {
    id: season.id,
    name: season.name,
    isActive: season.is_active,
  }
}

function mapStanding(entry: StandingEntryRead): StandingEntrySummary {
  return {
    driverId: entry.driver_id,
    driverName: entry.driver_name,
    teamName: entry.team_name ?? null,
    points: entry.points,
    wins: entry.wins,
    bestFinish: entry.best_finish,
    podiums: entry.podiums ?? null,
  }
}

export async function fetchLeagueSeasons(token: string, slug: string): Promise<SeasonSummary[]> {
  const response = await apiFetch(`/leagues/${slug}/seasons`, {
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to load seasons', response.status)
  }

  const payload = (await response.json()) as SeasonRead[]
  return payload.map(mapSeason)
}

export async function fetchLeagueStandings(
  token: string,
  slug: string,
  seasonId: string,
): Promise<StandingEntrySummary[]> {
  const response = await apiFetch(`/leagues/${slug}/standings?seasonId=${encodeURIComponent(seasonId)}`, {
    token,
  })

  if (response.status === 404) {
    return []
  }

  if (!response.ok) {
    throw new ApiError('Unable to load standings', response.status)
  }

  const payload = (await response.json()) as StandingEntryRead[]
  return payload.map(mapStanding)
}
