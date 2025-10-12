
import { useMemo } from 'react'
import type { ReactElement, FormEvent } from 'react'
import { useAdminConsole } from '../hooks/useAdminConsole'
import { useToast } from '../hooks/useToast'
import type { BillingPlanTier } from '../types/billing'

const PLAN_OPTIONS: BillingPlanTier[] = ['FREE', 'PRO', 'ELITE']

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date)
}

export function AdminConsolePage(): ReactElement {
  const {
    adminEnabled,
    isFounder,
    isProduction,
    query,
    setQuery,
    data,
    isLoading,
    error,
    refresh,
    toggleDiscord,
    overridePlan,
    togglingLeagueId,
    planUpdatingLeagueId,
  } = useAdminConsole()
  const { showToast } = useToast()

  const disablePlanOverride = isProduction
  const planOverrideHelp = disablePlanOverride
    ? 'Plan override is disabled in production environments.'
    : 'Use with caution: this bypasses normal billing workflows.'

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void refresh()
  }

  const users = data.users
  const leagues = data.leagues

  const hasNoAccess = adminEnabled && !isFounder

  const summaryEmpty = useMemo(() => users.length === 0 && leagues.length === 0, [users, leagues])

  if (!adminEnabled) {
    return (
      <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-300">
        <h2 className="text-xl font-semibold text-slate-100">Admin console disabled</h2>
        <p className="mt-2 text-slate-400">
          Enable the console by setting <code className="font-mono text-slate-200">ADMIN_MODE=true</code>{' '}
          on the API and <code className="font-mono text-slate-200">VITE_ADMIN_MODE=true</code> for the frontend build.
        </p>
      </div>
    )
  }

  if (hasNoAccess) {
    return (
      <div className="rounded-3xl border border-amber-500/40 bg-amber-500/10 p-6 text-sm text-amber-100">
        <h2 className="text-xl font-semibold text-amber-200">Founder access required</h2>
        <p className="mt-2">
          Only founder accounts can view the admin console. Add <code className="font-mono text-amber-100">is_founder</code>{' '}
          to your user record to continue.
        </p>
      </div>
    )
  }

  const handleToggleDiscord = async (leagueId: string, isActive: boolean) => {
    try {
      await toggleDiscord(leagueId, isActive)
      showToast({
        title: 'Discord integration updated',
        description: isActive
          ? 'Integration activated for this league.'
          : 'Integration disabled for this league.',
        variant: 'success',
      })
    } catch (err) {
      showToast({
        title: 'Discord update failed',
        description: err instanceof Error ? err.message : 'Unable to update Discord integration.',
        variant: 'error',
      })
    }
  }

  const handlePlanOverride = async (leagueId: string, plan: BillingPlanTier) => {
    if (disablePlanOverride) {
      showToast({
        title: 'Plan override disabled',
        description: planOverrideHelp,
        variant: 'error',
      })
      return
    }
    try {
      await overridePlan(leagueId, plan)
      showToast({
        title: 'Plan updated',
        description: `League plan set to ${plan}.`,
        variant: 'success',
      })
    } catch (err) {
      showToast({
        title: 'Override failed',
        description: err instanceof Error ? err.message : 'Unable to override league plan.',
        variant: 'error',
      })
    }
  }

  return (
    <div className="space-y-6">
      {isProduction ? (
        <div className="rounded-3xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
          Running in production mode. Dangerous actions are read-only unless explicitly enabled.
        </div>
      ) : (
        <div className="rounded-3xl border border-sky-500/40 bg-sky-500/10 p-4 text-sm text-sky-100">
          Admin mode active. Use this console to inspect data and perform guarded overrides for debugging.
        </div>
      )}

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-4">
          <div className="flex-1" style={{ minWidth: '200px' }}>
            <label htmlFor="admin-search" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Search users & leagues
            </label>
            <input
              id="admin-search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
              }}
              placeholder="Search by email, Discord username, league name, or slug"
              className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-5 py-2 text-sm font-semibold uppercase tracking-wide text-slate-200 transition hover:border-slate-500 hover:text-slate-100"
          >
            Refresh
          </button>
        </form>
        {error ? (
          <p className="mt-3 text-sm text-rose-300">
            {error.message}
          </p>
        ) : null}
      </section>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">User overview</h2>
            <p className="text-sm text-slate-400">Inspect founders, owners, and subscription health.</p>
          </div>
        </header>

        {isLoading ? (
          <div className="mt-5 space-y-3">
            {Array.from({ length: 2 }).map((_, index) => (
              <div key={index} className="animate-pulse rounded-2xl border border-slate-800/70 bg-slate-900/50 p-4">
                <div className="h-4 w-48 rounded bg-slate-800" />
                <div className="mt-3 h-3 w-32 rounded bg-slate-800" />
                <div className="mt-3 h-3 w-64 rounded bg-slate-800" />
              </div>
            ))}
          </div>
        ) : users.length === 0 ? (
          <p className="mt-4 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-4 text-sm text-slate-300">
            No users matched this query.
          </p>
        ) : (
          <div className="mt-5 space-y-4">
            {users.map((user) => (
              <div key={user.id} className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-slate-100">
                      {user.discordUsername || 'Unknown Discord user'}
                    </p>
                    <p className="text-xs text-slate-500">{user.email || 'No email provided'}</p>
                  </div>
                  <div className="text-xs text-slate-400">
                    <p>
                      Created: <span className="text-slate-200">{formatDateTime(user.createdAt)}</span>
                    </p>
                    <p>
                      Leagues owned: <span className="text-slate-200">{user.leaguesOwned}</span>
                    </p>
                  </div>
                </div>
                <div className="mt-3 grid gap-3 text-xs text-slate-400 sm:grid-cols-3">
                  <div className="rounded-2xl border border-slate-800/70 bg-slate-900/40 p-3">
                    <p className="font-semibold text-slate-300">Billing plan</p>
                    <p className="mt-1 text-slate-200">{user.billingPlan}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800/70 bg-slate-900/40 p-3">
                    <p className="font-semibold text-slate-300">Subscription status</p>
                    <p className="mt-1 text-slate-200">{user.subscriptionStatus ?? 'n/a'}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800/70 bg-slate-900/40 p-3">
                    <p className="font-semibold text-slate-300">Stripe customer</p>
                    <p className="mt-1 text-slate-200">{user.stripeCustomerId ?? 'n/a'}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">League overview</h2>
            <p className="text-sm text-slate-400">
              Check driver utilisation, billing state, and Discord connectivity.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              void refresh()
            }}
            className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:border-slate-500 hover:text-slate-100"
          >
            Refresh
          </button>
        </header>

        {isLoading ? (
          <div className="mt-5 space-y-3">
            {Array.from({ length: 2 }).map((_, index) => (
              <div key={index} className="animate-pulse rounded-2xl border border-slate-800/70 bg-slate-900/50 p-4">
                <div className="h-4 w-40 rounded bg-slate-800" />
                <div className="mt-2 h-3 w-60 rounded bg-slate-800" />
                <div className="mt-4 h-3 w-32 rounded bg-slate-800" />
              </div>
            ))}
          </div>
        ) : leagues.length === 0 ? (
          <p className="mt-4 rounded-2xl border border-slate-800/70 bg-slate-900/50 p-4 text-sm text-slate-300">
            No leagues matched this query.
          </p>
        ) : (
          <div className="mt-5 space-y-4">
            {leagues.map((league) => {
              const isToggling = togglingLeagueId === league.id
              const isUpdatingPlan = planUpdatingLeagueId === league.id
              return (
                <div key={league.id} className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/20">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-slate-100">{league.name}</p>
                      <p className="text-xs text-slate-500">slug: {league.slug}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        Owner: <span className="text-slate-200">{league.ownerDiscordUsername ?? 'Unknown'}</span> ·{' '}
                        <span className="text-slate-200">{league.ownerEmail ?? 'n/a'}</span>
                      </p>
                    </div>
                    <div className="text-xs text-slate-400">
                      <p>
                        League plan:{' '}
                        <span className="text-slate-200">{league.plan}</span>
                      </p>
                      <p>
                        Billing plan:{' '}
                        <span className="text-slate-200">{league.billingPlan}</span>
                      </p>
                      <p>
                        Drivers: <span className={`text-slate-200 ${league.driverCount >= league.driverLimit ? 'text-amber-300' : ''}`}>
                          {league.driverCount} / {league.driverLimit}
                        </span>
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        void handleToggleDiscord(league.id, !league.discordActive)
                      }}
                      disabled={isToggling}
                      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide transition ${
                        league.discordActive
                          ? 'bg-emerald-500 text-emerald-950 hover:bg-emerald-400'
                          : 'bg-slate-800 text-slate-200 hover:bg-slate-700'
                      } disabled:cursor-not-allowed disabled:opacity-70`}
                    >
                      {isToggling ? (
                        <span className="inline-flex h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                      ) : null}
                      {league.discordActive ? 'Disable Discord' : 'Enable Discord'}
                    </button>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <label htmlFor={`plan-${league.id}`} className="font-semibold text-slate-300">
                        Override plan
                      </label>
                      <select
                        id={`plan-${league.id}`}
                        value={league.plan}
                        onChange={(event) => {
                          const nextPlan = event.target.value as BillingPlanTier
                          void handlePlanOverride(league.id, nextPlan)
                        }}
                        disabled={disablePlanOverride || isUpdatingPlan}
                        title={planOverrideHelp}
                        className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs text-slate-100 transition hover:border-slate-500 focus:border-sky-500 focus:outline-none disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500"
                      >
                        {PLAN_OPTIONS.map((plan) => (
                          <option key={plan} value={plan}>
                            {plan}
                          </option>
                        ))}
                      </select>
                      {isUpdatingPlan ? (
                        <span className="inline-flex h-3 w-3 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                      ) : null}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {summaryEmpty && !isLoading ? (
        <p className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-4 text-sm text-slate-400">
          No results yet. Try adjusting your search or create sample records.
        </p>
      ) : null}
    </div>
  )
}
