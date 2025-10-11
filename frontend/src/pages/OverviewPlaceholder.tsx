import { useMemo } from 'react'
import { useAuth } from '../hooks/useAuth'

const upcomingFeatures = [
  {
    title: 'Interactive dashboard',
    detail: 'Command center with upcoming events, standings tiles, and billing callouts.',
    status: 'PBI-023 in progress',
  },
  {
    title: 'League management suite',
    detail: 'Tabs for drivers, teams, and events with optimistic updates and RBAC.',
    status: 'PBI-024 to PBI-027',
  },
  {
    title: 'Results workflow',
    detail: 'Drag-and-drop grid, idempotency headers, and Discord announcements.',
    status: 'PBI-028 lined up',
  },
]

const buildTimeline = [
  {
    label: 'Auth shell deployed',
    caption: 'Secure Discord login, token capture, and session refresh are live.',
  },
  {
    label: 'Management modules next',
    caption: 'Dashboard and league CRUD flow into upcoming PBIs.',
  },
  {
    label: 'Cross-service observability',
    caption: 'Structured logging, health checks, and seed data already in place.',
  },
]

function formatPlan(plan: string | null | undefined): string {
  if (!plan) return 'FREE'
  return plan.replace(/_/g, ' ').toUpperCase()
}

export function OverviewPlaceholder(): JSX.Element {
  const { user, memberships, billingPlan } = useAuth()

  const membershipPreview = useMemo(() => memberships.slice(0, 3), [memberships])
  const leftover = Math.max(0, memberships.length - membershipPreview.length)
  const displayName = user?.discord_username ?? user?.email ?? 'Driver'
  const planLabel = formatPlan(billingPlan?.plan)

  return (
    <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
      <div className="space-y-6">
        <article className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/40">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">Welcome</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-100">{displayName}, your console is ready</h2>
          <p className="mt-3 text-sm text-slate-400">
            The shell already handles authentication, protected routing, and contextual layouts. As feature PBIs arrive this
            space will light up with live data, quick actions, and racing insights tailored to your leagues.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Current plan</p>
              <p className="mt-2 text-lg font-semibold text-slate-100">{planLabel}</p>
              <p className="mt-1 text-xs text-slate-400">
                {billingPlan?.current_period_end
                  ? `Next renewal ${new Intl.DateTimeFormat(undefined, {
                      month: 'short',
                      day: 'numeric',
                    }).format(new Date(billingPlan.current_period_end))}`
                  : 'Billing sync ready when Stripe connects'}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Leagues connected</p>
              <p className="mt-2 text-lg font-semibold text-slate-100">{memberships.length}</p>
              <p className="mt-1 text-xs text-slate-400">Discord roles and RBAC ready for upcoming modules.</p>
            </div>
          </div>
        </article>

        <article className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/40">
          <h3 className="text-lg font-semibold text-slate-100">On the near-term roadmap</h3>
          <ul className="mt-4 space-y-4">
            {upcomingFeatures.map((feature) => (
              <li key={feature.title} className="rounded-2xl border border-slate-800/60 bg-slate-900/60 p-4">
                <div className="flex items-baseline justify-between">
                  <p className="text-sm font-semibold text-slate-100">{feature.title}</p>
                  <span className="text-xs font-semibold uppercase tracking-wide text-sky-300">{feature.status}</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{feature.detail}</p>
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/40">
          <h3 className="text-lg font-semibold text-slate-100">Build timeline</h3>
          <ol className="mt-4 space-y-3 text-sm text-slate-300">
            {buildTimeline.map((item, index) => (
              <li key={item.label} className="flex items-start gap-3">
                <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-700/70 bg-slate-900/70 text-xs font-semibold text-sky-300">
                  {index + 1}
                </span>
                <div>
                  <p className="font-semibold text-slate-100">{item.label}</p>
                  <p className="text-xs text-slate-400">{item.caption}</p>
                </div>
              </li>
            ))}
          </ol>
        </article>
      </div>

      <aside className="space-y-6">
        <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/40">
          <h3 className="text-lg font-semibold text-slate-100">League preview</h3>
          <p className="mt-2 text-sm text-slate-400">
            Authentication is wired, so the frontend already knows your memberships. These will power navigation shortcuts once
            the dashboard comes online.
          </p>
          <ul className="mt-4 space-y-3 text-sm text-slate-300">
            {membershipPreview.length > 0 ? (
              membershipPreview.map((membership) => (
                <li key={membership.league_id} className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3">
                  <p className="font-semibold text-slate-100">{membership.league_name}</p>
                  <p className="text-xs text-slate-400">Role: {membership.role}</p>
                </li>
              ))
            ) : (
              <li className="rounded-2xl border border-dashed border-slate-800/70 bg-slate-900/40 p-3 text-xs text-slate-400">
                Link a league to populate this list.
              </li>
            )}
          </ul>
          {leftover > 0 ? (
            <p className="mt-2 text-xs text-slate-500">{leftover} more league(s) will appear once navigation is live.</p>
          ) : null}
        </div>

        <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/40">
          <h3 className="text-lg font-semibold text-slate-100">What works today</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li>- Discord login redirects and token storage.</li>
            <li>- React Query ready for API integrations.</li>
            <li>- Protected layout with contextual state.</li>
            <li>- Design system using Tailwind and reusable components.</li>
          </ul>
        </div>
      </aside>
    </section>
  )
}
