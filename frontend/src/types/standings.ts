export interface SeasonRead {
  id: string
  name: string
  is_active: boolean
}

export interface SeasonSummary {
  id: string
  name: string
  isActive: boolean
}

export interface StandingEntryRead {
  driver_id: string
  driver_name: string
  team_name?: string | null
  points: number
  wins: number
  best_finish: number | null
  podiums?: number | null
}

export interface StandingEntrySummary {
  driverId: string
  driverName: string
  teamName: string | null
  points: number
  wins: number
  bestFinish: number | null
  podiums: number | null
}
