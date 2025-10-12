import { useCallback, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchDiscordIntegration,
  startDiscordLink,
  unlinkDiscord,
  testDiscordIntegration,
} from '../api/discord'
import { useAuth } from './useAuth'
import type { DiscordIntegrationStatus } from '../types/discord'

const MOCK_CONNECTED: DiscordIntegrationStatus = {
  linked: true,
  guildName: 'GridBoss Demo Guild',
  channelName: '#race-control',
  requiresReconnect: false,
  lastTestedAt: new Date().toISOString(),
}

const MOCK_DISCONNECTED: DiscordIntegrationStatus = {
  linked: false,
  guildName: null,
  channelName: null,
  requiresReconnect: false,
  lastTestedAt: null,
}

export function useDiscordIntegration(slug: string | null) {
  const { accessToken, isBypassAuth } = useAuth()
  const shouldFetch = Boolean(accessToken) && Boolean(slug)
  const queryClient = useQueryClient()

  const [localStatus, setLocalStatus] =
    useState<DiscordIntegrationStatus>(MOCK_DISCONNECTED)

  useEffect(() => {
    setLocalStatus(MOCK_DISCONNECTED)
  }, [slug])

  const statusQuery = useQuery({
    queryKey: ['discord-integration', slug],
    queryFn: () => fetchDiscordIntegration(accessToken ?? '', slug ?? ''),
    enabled: shouldFetch,
    staleTime: 60_000,
  })

  const status = shouldFetch
    ? (statusQuery.data ?? MOCK_DISCONNECTED)
    : localStatus

  const refresh = useCallback(async () => {
    if (!slug) {
      return
    }
    if (!shouldFetch) {
      setLocalStatus((current) => current)
      return
    }
    await queryClient.invalidateQueries({
      queryKey: ['discord-integration', slug],
      exact: true,
    })
  }, [slug, shouldFetch, queryClient])

  const beginLink = useCallback(async () => {
    if (!slug) {
      throw new Error('Missing league identifier')
    }

    if (shouldFetch) {
      if (!accessToken) {
        throw new Error('Not authenticated')
      }
      const url = await startDiscordLink(accessToken, slug)
      return url
    }

    setLocalStatus(MOCK_CONNECTED)
    return 'https://discord.com/oauth2/authorize?client_id=demo'
  }, [slug, shouldFetch, accessToken])

  const disconnect = useCallback(async () => {
    if (!slug) {
      throw new Error('Missing league identifier')
    }

    if (shouldFetch) {
      if (!accessToken) {
        throw new Error('Not authenticated')
      }
      await unlinkDiscord(accessToken, slug)
      await refresh()
      return
    }

    setLocalStatus(MOCK_DISCONNECTED)
  }, [slug, shouldFetch, accessToken, refresh])

  const sendTest = useCallback(async () => {
    if (!slug) {
      throw new Error('Missing league identifier')
    }

    if (shouldFetch) {
      if (!accessToken) {
        throw new Error('Not authenticated')
      }
      return testDiscordIntegration(accessToken, slug)
    }

    setLocalStatus((current) => ({
      ...current,
      lastTestedAt: new Date().toISOString(),
    }))
    return 'Demo test message sent'
  }, [slug, shouldFetch, accessToken])

  return {
    status,
    isLoading: shouldFetch ? statusQuery.isLoading : false,
    error: shouldFetch ? (statusQuery.error ?? null) : null,
    refresh,
    beginLink,
    disconnect,
    sendTest,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
