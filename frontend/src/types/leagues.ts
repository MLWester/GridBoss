import type { LeagueRole } from './auth'

export interface LeagueRead {
  id: string
  name: string
  slug: string
  plan?: string | null
  driver_limit?: number | null
  owner_id?: string | null
  is_deleted?: boolean
  deleted_at?: string | null
}

export interface LeagueSummary {
  id: string
  name: string
  slug: string
  plan: string | null
  driverLimit: number | null
  role: LeagueRole | null
}

export interface CreateLeagueRequest {
  name: string
  slug: string
}

export interface LeagueEventSummary {
  id: string
  name: string
  track: string
  startTime: string
  status: string
}

export interface LeagueResultPodiumEntry {
  driverName: string
  teamName?: string | null
  position: number
  points?: number | null
}

export interface LeagueResultSummary {
  event: LeagueEventSummary
  podium: LeagueResultPodiumEntry[]
}

export interface LeagueOverviewData {
  league: LeagueSummary & {
    description?: string | null
  }
  nextEvent?: LeagueEventSummary | null
  recentResult?: LeagueResultSummary | null
  discordLinked: boolean
}
