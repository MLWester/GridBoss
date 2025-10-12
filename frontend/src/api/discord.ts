import { apiFetch } from './client'
import { ApiError } from './auth'
import type {
  DiscordIntegrationStatus,
  DiscordIntegrationStatusRead,
  DiscordLinkResponse,
  DiscordTestResponse,
} from '../types/discord'

function mapStatus(payload: DiscordIntegrationStatusRead): DiscordIntegrationStatus {
  return {
    linked: payload.linked ?? false,
    guildName: payload.guild_name ?? null,
    channelName: payload.channel_name ?? null,
    requiresReconnect: payload.requires_reconnect ?? false,
    lastTestedAt: payload.last_tested_at ?? null,
  }
}

export async function fetchDiscordIntegration(token: string, slug: string): Promise<DiscordIntegrationStatus> {
  const response = await apiFetch(`/leagues/${slug}/discord`, {
    token,
  })

  if (response.status === 404) {
    return {
      linked: false,
      guildName: null,
      channelName: null,
      requiresReconnect: false,
      lastTestedAt: null,
    }
  }

  if (!response.ok) {
    throw new ApiError('Unable to load Discord integration', response.status)
  }

  const payload = (await response.json()) as DiscordIntegrationStatusRead
  return mapStatus(payload)
}

export async function startDiscordLink(token: string, slug: string): Promise<string> {
  const response = await apiFetch(`/leagues/${slug}/discord/link`, {
    method: 'POST',
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to start Discord linking', response.status)
  }

  const payload = (await response.json()) as DiscordLinkResponse
  return payload.url
}

export async function unlinkDiscord(token: string, slug: string): Promise<void> {
  const response = await apiFetch(`/leagues/${slug}/discord/unlink`, {
    method: 'POST',
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to unlink Discord integration', response.status)
  }
}

export async function testDiscordIntegration(token: string, slug: string): Promise<string> {
  const response = await apiFetch(`/leagues/${slug}/discord/test`, {
    method: 'POST',
    token,
  })

  if (response.status === 402) {
    throw new ApiError('Upgrade to Pro to send Discord announcements.', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to send test announcement', response.status)
  }

  const payload = (await response.json()) as DiscordTestResponse
  return payload.message
}
