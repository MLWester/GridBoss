import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { LeagueOverviewData } from '../../types/leagues'
import { LeagueOverviewPage } from '../LeagueOverviewPage'

const mockUseOutletContext = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  )
  return {
    ...actual,
    useOutletContext: () => mockUseOutletContext(),
  }
})

vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}))

describe('LeagueOverviewPage', () => {
  beforeEach(() => {
    mockUseOutletContext.mockReset()
  })

  it('renders sanitized league description', () => {
    const overview: LeagueOverviewData = {
      league: {
        id: '1',
        name: 'Night Rally',
        slug: 'night-rally',
        plan: 'FREE',
        driverLimit: 20,
        role: 'OWNER',
        description:
          "Welcome **racers**! <script>alert('xss')</script> [Rules](https://example.com)",
      },
      nextEvent: null,
      recentResult: null,
      discordLinked: false,
    }

    mockUseOutletContext.mockReturnValue({
      overview,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      isBypass: false,
    })

    render(<LeagueOverviewPage />)

    const matches = screen.getAllByText((_, element) =>
      element?.textContent?.includes('Welcome racers!') ?? false,
    )
    expect(matches.length).toBeGreaterThan(0)
    const link = screen.getByRole('link', { name: 'Rules' })
    expect(link).toHaveAttribute('href', 'https://example.com')
    expect(document.querySelector('script')).toBeNull()
  })
})

