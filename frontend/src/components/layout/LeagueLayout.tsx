import { useMemo } from 'react'
import type { ReactElement } from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { useLeagueOverview } from '../../hooks/useLeagueOverview'
import { useLeagues } from '../../hooks/useLeagues'
import { useAuth } from '../../hooks/useAuth'
import type { LeagueOverviewData } from '../../types/leagues'

export interface LeagueOutletContext {
  overview: LeagueOverviewData | null
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<LeagueOverviewData | null>
  isBypass: boolean
}

const tabs = [
  { label: 'Overview', path: '.' },
  { label: 'Drivers', path: 'drivers' },
  { label: 'Teams', path: 'teams' },
  { label: 'Events', path: 'events' },
  { label: 'Standings', path: 'standings' },
  { label: 'Settings', path: 'settings' },
]

function formatPlan(plan: string | null): string {
  if (!plan) return 'FREE'
  return plan.toUpperCase()
}

function formatDriverLimit(limit: number | null): string {
  if (limit == null) return 'n/a'
  return limit.toString()
}

export function LeagueLayout(): ReactElement {
  const { slug } = useParams<{ slug: string }>()
  const { leagues } = useLeagues()
  const { billingPlan } = useAuth()

  const { overview, isLoading, error, refetch, isBypass } = useLeagueOverview(slug ?? '')

  const leagueSummary = useMemo(() => {
    if (!slug) return overview?.league ?? null
    return leagues.find((league) => league.slug === slug) ?? overview?.league ?? null
  }, [leagues, overview?.league, slug])

  const contextValue: LeagueOutletContext = {
    overview,
    isLoading,
    error,
    refetch,
    isBypass,
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/40">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">League</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-100">
              {leagueSummary?.name ?? (slug ? slug.replace(/-/g, ' ') : 'League')}
            </h1>
            <p className="text-sm text-slate-400">Slug: {leagueSummary?.slug ?? slug ?? 'n/a'}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-4 text-right">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Plan</p>
              <p className="mt-2 text-lg font-semibold text-slate-100">{formatPlan(leagueSummary?.plan ?? billingPlan?.plan ?? 'FREE')}</p>
            </div>
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-4 text-right">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Driver limit</p>
              <p className="mt-2 text-lg font-semibold text-slate-100">{formatDriverLimit(leagueSummary?.driverLimit ?? null)}</p>
            </div>
          </div>
        </div>

        <nav className="mt-6 flex flex-wrap gap-2 text-sm">
          {tabs.map((tab) => (
            <NavLink
              key={tab.label}
              to={tab.path}
              end={tab.path === '.'}
              className={({ isActive }) =>
                [
                  'inline-flex items-center rounded-full border border-slate-800/70 bg-slate-900/60 px-4 py-2 transition hover:border-sky-500/60 hover:text-sky-100',
                  isActive ? 'border-sky-500/60 bg-sky-500/10 text-sky-100' : '',
                ]
                  .filter(Boolean)
                  .join(' ')
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="min-h-[320px] rounded-3xl border border-slate-800/70 bg-slate-900/50 p-6 shadow shadow-slate-950/30">
        <Outlet context={contextValue} />
      </div>
    </div>
  )
}
