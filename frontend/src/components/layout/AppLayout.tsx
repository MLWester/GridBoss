import { useMemo } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

interface NavigationItem {
  label: string
  to?: string
  description: string
  comingSoon?: boolean
}

const navigation: NavigationItem[] = [
  {
    label: 'Dashboard',
    to: '/',
    description: 'Central overview and quick actions',
  },
  {
    label: 'Leagues',
    description: 'League configuration and roster management',
    comingSoon: true,
  },
  {
    label: 'Results',
    description: 'Race control, results entry, and standings',
    comingSoon: true,
  },
]

function formatPlan(plan: string | null | undefined): string {
  if (!plan) return 'Free'
  return plan.replace(/_/g, ' ').toUpperCase()
}

function formatRenewal(dateIso: string | null | undefined): string {
  if (!dateIso) return 'Renewal date not yet scheduled'
  const date = new Date(dateIso)
  if (Number.isNaN(date.getTime())) return 'Renewal date not yet scheduled'
  return `Renews ${new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)}`
}

export function AppLayout(): JSX.Element {
  const { user, memberships, billingPlan, logout } = useAuth()

  const membershipLabel = useMemo(() => {
    if (memberships.length === 0) return 'No leagues yet'
    if (memberships.length === 1) {
      return `${memberships[0]?.league_name ?? 'Untitled league'} - ${memberships[0]?.role ?? 'Member'}`
    }
    return `${memberships.length.toString()} leagues`
  }, [memberships])

  const planName = formatPlan(billingPlan?.plan)
  const renewal = formatRenewal(billingPlan?.current_period_end)

  const avatarInitial = (user?.discord_username ?? user?.email ?? '?').slice(0, 1).toUpperCase()

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.18),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(59,130,246,0.12),transparent_65%)]" />
      </div>

      <div className="relative flex min-h-screen flex-col">
        <header className="border-b border-slate-800/70 bg-slate-900/70 backdrop-blur">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6">
            <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-900/80 px-4 py-1 text-xs font-semibold uppercase tracking-[0.4em] text-sky-300">
                  GridBoss
                </div>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-100 md:text-3xl">
                  League Control Center
                </h1>
                <p className="max-w-2xl text-sm text-slate-400">
                  A polished shell for the upcoming console experience. Authentication, routing, and layout scaffolding are in
                  place so the next PBIs can plug in live data, dashboards, and management workflows.
                </p>
              </div>
              <div className="flex items-center gap-4 self-start rounded-2xl border border-slate-800/70 bg-slate-900/70 p-4 shadow-lg shadow-slate-950/40">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-800/70 text-lg font-semibold text-sky-300">
                  {avatarInitial}
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-slate-100">
                    {user?.discord_username ?? user?.email ?? 'Driver'}
                  </div>
                  <div className="text-xs text-slate-400">{membershipLabel}</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    void logout()
                  }}
                  className="rounded-full border border-slate-700/80 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
                >
                  Logout
                </button>
              </div>
            </div>

            <nav className="flex flex-wrap gap-2 text-sm">
              {navigation.map((item) =>
                item.to ? (
                  <NavLink
                    key={item.label}
                    to={item.to}
                    className={({ isActive }) => {
                      const base = 'group inline-flex items-center rounded-full border border-slate-800/70 bg-slate-900/60 px-4 py-2 transition hover:border-sky-500/60 hover:text-sky-100'
                      const active = isActive ? 'border-sky-500/60 bg-sky-500/10 text-sky-100' : ''
                      return [base, active].filter(Boolean).join(' ')
                    }}
                  >
                    <span className="font-semibold">{item.label}</span>
                    <span className="ml-2 hidden text-xs text-slate-400 sm:inline">{item.description}</span>
                  </NavLink>
                ) : (
                  <span
                    key={item.label}
                    className="inline-flex cursor-not-allowed items-center rounded-full border border-slate-800/60 bg-slate-900/40 px-4 py-2 text-slate-500"
                  >
                    <span className="font-semibold">{item.label}</span>
                    <span className="ml-2 hidden text-xs text-slate-500 sm:inline">{item.description}</span>
                    <span className="ml-3 rounded-full border border-slate-700/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      Soon
                    </span>
                  </span>
                ),
              )}
            </nav>
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-8 px-6 py-10">
          <section className="grid gap-6 rounded-3xl border border-slate-800/70 bg-slate-900/50 p-6 shadow-xl shadow-slate-950/40 md:grid-cols-3">
            <div className="md:col-span-2">
              <h2 className="text-lg font-semibold text-slate-100">Plan summary</h2>
              <p className="mt-2 text-sm text-slate-400">
                {planName} plan - {renewal}
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 text-center">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Teams & leagues</dt>
                <dd className="mt-1 text-xl font-semibold text-slate-100">{memberships.length}</dd>
              </div>
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 text-center">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Session status</dt>
                <dd className="mt-1 text-xl font-semibold text-slate-100">Secure</dd>
              </div>
            </dl>
          </section>

          <Outlet />
        </main>
      </div>
    </div>
  )
}