import type { ReactElement } from 'react'
import { Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function AppLayout(): ReactElement {
  const { user, memberships, billingPlan, logout } = useAuth()
  const membershipCount = memberships.length
  const membershipLabel =
    membershipCount > 0
      ? `${membershipCount.toString()} league${membershipCount > 1 ? 's' : ''}`
      : 'No leagues yet'

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-sky-400">
              GridBoss
            </span>
            <span className="text-sm text-slate-400">League Control Center</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium">
                {user?.discord_username ?? 'Driver'}
              </p>
              <p className="text-xs text-slate-400">
                {membershipLabel}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                void logout()
              }}
              className="rounded-full border border-slate-700 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
            >
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
        <section className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 shadow-lg shadow-slate-950/40">
          <h1 className="text-3xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-2 text-sm text-slate-400">
            {billingPlan?.plan
              ? `You are on the ${billingPlan.plan} plan. Manage your leagues, events, and drivers from this hub as upcoming PBIs bring the full experience to life.`
              : 'Connect a Discord account, create a league, and keep an eye out for new modules as the build progresses.'}
          </p>
        </section>
        <Outlet />
      </main>
    </div>
  )
}
