import type { LeagueRole } from './auth'

export interface LeagueRead {
  id: string
  name: string
  slug: string
  plan: string
  driver_limit: number
  owner_id: string | null
  is_deleted: boolean
  deleted_at: string | null
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
