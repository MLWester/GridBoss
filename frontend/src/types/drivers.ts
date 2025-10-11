export interface DriverRead {
  id: string
  display_name: string
  team_id?: string | null
  team_name?: string | null
  user?: {
    id: string
    discord_username: string | null
  } | null
  discord_id?: string | null
}

export interface DriverSummary {
  id: string
  displayName: string
  teamId: string | null
  teamName: string | null
  linkedUser: boolean
  discordId: string | null
  userName: string | null
}

export interface BulkDriverInput {
  display_name: string
  team_id?: string | null
}

export interface UpdateDriverRequest {
  display_name?: string
  team_id?: string | null
}
