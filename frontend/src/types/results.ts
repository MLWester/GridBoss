export type ResultStatus = 'FINISHED' | 'DNF' | 'DNS' | 'DSQ'

export interface ResultEntryRead {
  driver_id: string
  finish_position: number
  status: ResultStatus
  bonus_points?: number | null
  penalty_points?: number | null
}

export interface ResultEntrySummary {
  driverId: string
  finishPosition: number
  status: ResultStatus
  bonusPoints: number
  penaltyPoints: number
}

export interface SubmitResultEntry {
  driverId: string
  finishPosition: number
  status: ResultStatus
  bonusPoints?: number | null
  penaltyPoints?: number | null
}
