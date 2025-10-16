import { useMemo } from 'react'
import type { ReactElement } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { ThemeToggle } from '../common/ThemeToggle'

export function AppLayout(): ReactElement {
  const { user, memberships, billingPlan, logout, isFounder } = useAuth()
  const membershipCount = memberships.length
  const membershipLabel =
    membershipCount > 0
      ? `${membershipCount.toString()} league${membershipCount > 1 ? 's' : ''}`
      : 'No leagues yet'

  const adminModeEnabled = import.meta.env.VITE_ADMIN_MODE === 'true'

  const tabs = useMemo(() => {
    const base = [
      { label: 'Dashboard', path: '.' },
      { label: 'Billing', path: 'billing' },
    ]
    if (adminModeEnabled && isFounder) {
      base.push({ label: 'Admin', path: 'admin' })
    }
    return base
  }, [adminModeEnabled, isFounder])

  return (
    <div className="min-h-screen bg-app text-text transition-colors duration-300">
      <header className="border-border/70 bg-surface/80 border-b backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-accent">
              GridBoss
            </span>
            <span className="text-sm text-muted">League Control Center</span>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">{user?.discord_username ?? 'Driver'}</p>
              <p className="text-xs text-muted">{membershipLabel}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                void logout()
              }}
              className="border-border/70 rounded-full border px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-text transition hover:border-accent hover:text-accent"
            >
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
        <section className="border-border/70 bg-surface/80 rounded-3xl border p-6 shadow-soft">
          <h1 className="text-3xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-2 text-sm text-muted">
            {billingPlan?.plan
              ? `You are on the ${billingPlan.plan} plan. Manage your leagues, events, and drivers from this hub as upcoming PBIs bring the full experience to life.`
              : 'Connect a Discord account, create a league, and keep an eye out for new modules as the build progresses.'}
          </p>
        </section>
        <nav className="flex flex-wrap gap-2 text-sm">
          {tabs.map((tab) => (
            <NavLink
              key={tab.label}
              to={tab.path}
              end={tab.path === '.'}
              className={({ isActive }) =>
                [
                  'inline-flex items-center rounded-full border border-border/70 px-4 py-2 bg-surface-muted/80 transition',
                  isActive
                    ? 'border-accent bg-accent-soft text-accent'
                    : 'hover:border-accent/70 hover:text-text',
                ]
                  .filter(Boolean)
                  .join(' ')
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
        <Outlet />
      </main>
    </div>
  )
}
