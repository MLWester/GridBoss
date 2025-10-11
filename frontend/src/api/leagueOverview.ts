import { apiFetch } from './client'
import { ApiError } from './auth'
import type {
  LeagueOverviewData,
  LeagueEventSummary,
  LeagueResultSummary,
  LeagueResultPodiumEntry,
  LeagueSummary,
  LeagueRead,
} from '../types/leagues'

interface LeagueOverviewResponse {
  league: LeagueRead
  description?: string | null
  discord_linked: boolean | null
  next_event?: LeagueEventSummary | null
  recent_result?: {
    event: LeagueEventSummary
    podium?: LeagueResultPodiumEntry[] | null
  } | null
}

function toSummary(league: LeagueRead): LeagueSummary {
  return {
    id: league.id,
    name: league.name,
    slug: league.slug,
    plan: league.plan ?? null,
    driverLimit: typeof league.driver_limit === 'number' ? league.driver_limit : null,
    role: null,
  }
}

function mapOverview(payload: LeagueOverviewResponse): LeagueOverviewData {
  const podiumRaw = payload.recent_result?.podium
  const podiumEntries = Array.isArray(podiumRaw) ? podiumRaw : []
  const recentResult: LeagueResultSummary | null = payload.recent_result
    ? {
        event: payload.recent_result.event,
        podium: podiumEntries,
      }
    : null

  return {
    league: {
      ...toSummary(payload.league),
      description: payload.description ?? null,
    },
    nextEvent: payload.next_event ?? null,
    recentResult,
    discordLinked: Boolean(payload.discord_linked),
  }
}

export async function fetchLeagueOverview(token: string, slug: string): Promise<LeagueOverviewData> {
  const response = await apiFetch(`/leagues/${slug}/overview`, {
    token,
  })

  if (response.status === 404) {
    throw new ApiError('League not found', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to load league overview', response.status)
  }

  const payload = (await response.json()) as LeagueOverviewResponse
  return mapOverview(payload)
}
