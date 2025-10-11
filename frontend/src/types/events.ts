export type EventStatus = 'SCHEDULED' | 'COMPLETED' | 'CANCELLED'

export interface EventRead {
  id: string
  name: string
  track: string | null
  start_time: string
  status: EventStatus
  laps?: number | null
  distance_km?: number | null
}

export interface EventSummary {
  id: string
  name: string
  track: string | null
  startTime: string
  status: EventStatus
  laps: number | null
  distanceKm: number | null
}
