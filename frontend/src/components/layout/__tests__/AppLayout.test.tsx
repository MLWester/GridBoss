import { describe, expect, it, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { AuthContextValue } from '../../../providers/AuthContext'
import { AuthContext } from '../../../providers/AuthContext'
import { AppLayout } from '../AppLayout'

const baseAuthValue = (
  overrides: Partial<AuthContextValue> = {},
): AuthContextValue => ({
  profile: null,
  isLoading: false,
  error: null,
  isAuthenticated: true,
  isBypassAuth: false,
  accessToken: 'token',
  refreshProfile: async () => {},
  logout: async () => {},
  setAccessToken: () => {},
  ...overrides,
})

const founderProfile = {
  user: {
    id: 'founder',
    discord_id: null,
    discord_username: 'Founder One',
    avatar_url: null,
    email: 'founder@example.com',
    is_founder: true,
  },
  memberships: [],
  billingPlan: { plan: 'ELITE', current_period_end: null },
}

describe('AppLayout', () => {
  beforeEach(() => {
    Object.assign(import.meta.env, { VITE_ADMIN_MODE: 'true' })
  })

  it('renders billing summary by default', () => {
    const value = baseAuthValue({
      profile: founderProfile,
    })

    render(
      <AuthContext.Provider value={value}>
        <MemoryRouter>
          <AppLayout />
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    expect(screen.getByText(/You are on the ELITE plan/i)).toBeInTheDocument()
  })

  it('shows admin tab when founder and admin mode enabled', () => {
    const value = baseAuthValue({
      profile: founderProfile,
    })

    render(
      <AuthContext.Provider value={value}>
        <MemoryRouter>
          <AppLayout />
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('hides admin tab for non-founders', () => {
    const value = baseAuthValue({
      profile: {
        ...founderProfile,
        user: { ...founderProfile.user, is_founder: false },
      },
    })

    render(
      <AuthContext.Provider value={value}>
        <MemoryRouter>
          <AppLayout />
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    expect(screen.queryByText('Admin')).not.toBeInTheDocument()
  })
})
