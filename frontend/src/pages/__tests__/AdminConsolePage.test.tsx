import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AdminConsolePage } from '../AdminConsolePage'
import { useAdminConsole } from '../../hooks/useAdminConsole'
import type { AdminSearchResponse } from '../../types/admin'
import type { BillingPlanTier } from '../../types/billing'

type AdminConsoleState = ReturnType<typeof useAdminConsole>

const createMockData = (): AdminSearchResponse => {
  const proPlan: BillingPlanTier = 'PRO'
  return {
    users: [
      {
        id: 'user-1',
        discordUsername: 'AdminUser',
        email: 'admin@example.com',
        createdAt: new Date('2025-10-10T12:00:00Z').toISOString(),
        leaguesOwned: 3,
        billingPlan: proPlan,
        subscriptionStatus: 'active',
        stripeCustomerId: 'cus_test',
      },
    ],
    leagues: [
      {
        id: 'league-1',
        name: 'Test League',
        slug: 'test-league',
        plan: proPlan,
        driverLimit: 100,
        driverCount: 42,
        ownerId: 'user-1',
        ownerDiscordUsername: 'AdminUser',
        ownerEmail: 'admin@example.com',
        billingPlan: proPlan,
        discordActive: true,
      },
    ],
  }
}

const createState = (): AdminConsoleState => {
  const data = createMockData()
  return {
    adminEnabled: true,
    isFounder: true,
    isProduction: false,
    query: '',
    setQuery: vi.fn<AdminConsoleState['setQuery']>(),
    data,
    isLoading: false,
    error: null,
    refresh: vi.fn<AdminConsoleState['refresh']>(() => Promise.resolve(data)),
    toggleDiscord: vi.fn<AdminConsoleState['toggleDiscord']>(() =>
      Promise.resolve(),
    ),
    overridePlan: vi.fn<AdminConsoleState['overridePlan']>(() =>
      Promise.resolve(),
    ),
    togglingLeagueId: null,
    planUpdatingLeagueId: null,
    isMutating: false,
    shouldFetch: false,
  }
}

let baseState: AdminConsoleState = createState()

vi.mock('../../hooks/useAdminConsole')
const mockedUseAdminConsole = vi.mocked(useAdminConsole)

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

function renderPage() {
  return render(<AdminConsolePage />)
}

describe('AdminConsolePage', () => {
  beforeEach(() => {
    Object.assign(import.meta.env, { VITE_ADMIN_MODE: 'true' })
    baseState = createState()
    mockedUseAdminConsole.mockReset()
    mockedUseAdminConsole.mockReturnValue(baseState)
  })

  it('renders search form and user table', () => {
    renderPage()

    expect(screen.getByLabelText(/Search users/i)).toBeInTheDocument()
    expect(screen.getAllByText('AdminUser')).not.toHaveLength(0)
    expect(screen.getByText(/Test League/)).toBeInTheDocument()
  })

  it('calls refresh when search form submitted', () => {
    const refresh = vi.fn()
    mockedUseAdminConsole.mockReturnValue({
      ...baseState,
      refresh,
    })
    renderPage()

    const refreshButton = screen.getAllByRole('button', { name: /Refresh/i })[0]
    fireEvent.click(refreshButton)

    expect(refresh).toHaveBeenCalled()
  })

  it('handles admin disabled state', () => {
    mockedUseAdminConsole.mockReturnValue({
      ...baseState,
      adminEnabled: false,
    })
    renderPage()

    expect(screen.getByText(/Admin console disabled/)).toBeInTheDocument()
  })
})
