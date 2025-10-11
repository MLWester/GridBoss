export interface TeamRead {
  id: string
  name: string
  driver_count: number
  driver_ids?: string[] | null
}

export interface TeamSummary {
  id: string
  name: string
  driverIds: string[]
  driverCount: number
}
