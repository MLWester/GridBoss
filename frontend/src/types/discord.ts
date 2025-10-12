export interface DiscordIntegrationStatusRead {
  linked?: boolean | null
  guild_name?: string | null
  channel_name?: string | null
  requires_reconnect?: boolean | null
  last_tested_at?: string | null
}

export interface DiscordIntegrationStatus {
  linked: boolean
  guildName: string | null
  channelName: string | null
  requiresReconnect: boolean
  lastTestedAt: string | null
}

export interface DiscordLinkResponse {
  url: string
}

export interface DiscordTestResponse {
  message: string
}
