import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAdminConsole } from '../useAdminConsole'

vi.mock('../../api/admin', () => ({
  fetchAdminSearch: vi.fn().mockResolvedValue({
    users: [],
    leagues: [],
  }),
  toggleLeagueDiscord: vi.fn().mockResolvedValue({
    id: 'league',
    name: 'League',
    slug: 'league',
    plan: 'PRO',
    driverLimit: 100,
    driverCount: 10,
    ownerId: 'owner',
    ownerDiscordUsername: 'Owner',
    ownerEmail: 'owner@example.com',
    billingPlan: 'PRO',
    discordActive: true,
  }),
  overrideLeaguePlan: vi.fn().mockResolvedValue({
    id: 'league',
    name: 'League',
    slug: 'league',
    plan: 'ELITE',
    driverLimit: 9999,
    driverCount: 10,
    ownerId: 'owner',
    ownerDiscordUsername: 'Owner',
    ownerEmail: 'owner@example.com',
    billingPlan: 'ELITE',
    discordActive: true,
  }),
}))

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    accessToken: null,
    isBypassAuth: true,
    isFounder: true,
  }),
}))

describe('useAdminConsole', () => {
  beforeEach(() => {
    Object.assign(import.meta.env, { VITE_ADMIN_MODE: 'true' })
  })

  it('returns mock data in bypass mode', () => {
    const queryClient = new QueryClient();
    const { result } = renderHook(() => useAdminConsole(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    expect(result.current.adminEnabled).toBe(true)
    expect(result.current.data.users).not.toHaveLength(0)
    expect(result.current.shouldFetch).toBe(false)
  })

  it('updates mock data when toggling discord', async () => {
    const queryClient = new QueryClient();
    const { result } = renderHook(() => useAdminConsole(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    const league = result.current.data.leagues[0]
    expect(league.discordActive).toBe(true)

    await act(async () => {
      await result.current.toggleDiscord(league.id, false)
    })

    const updated = result.current.data.leagues.find((item) => item.id === league.id)
    expect(updated?.discordActive).toBe(false)
  })
})

