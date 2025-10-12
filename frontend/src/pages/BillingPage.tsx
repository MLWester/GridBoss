import { useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useBilling, type BillingUpgradePlan } from '../hooks/useBilling'
import { useToast } from '../hooks/useToast'
import type { BillingOverview, BillingPlanTier } from '../types/billing'

const PLAN_SEQUENCE: BillingPlanTier[] = ['FREE', 'PRO', 'ELITE']

interface PlanFeature {
  text: string
  gated?: boolean
}

interface PlanOption {
  tier: BillingPlanTier
  label: string
  price: string
  description: string
  features: PlanFeature[]
}

const PLAN_OPTIONS: PlanOption[] = [
  {
    tier: 'FREE',
    label: 'Free',
    price: '$0',
    description: 'Organize seasons and manage rosters with the core toolkit.',
    features: [
      { text: 'Up to 20 drivers per league' },
      { text: 'Manual Discord announcements' },
      { text: 'Community support' },
    ],
  },
  {
    tier: 'PRO',
    label: 'Pro',
    price: '$29/mo',
    description: 'Scale your league with automation and increased capacity.',
    features: [
      { text: 'Up to 100 drivers per league', gated: true },
      { text: 'Automated Discord announcements', gated: true },
      { text: 'Test announcements button', gated: true },
    ],
  },
  {
    tier: 'ELITE',
    label: 'Elite',
    price: '$99/mo',
    description: 'Enterprise-grade controls, limits, and concierge support.',
    features: [
      { text: 'Unlimited drivers', gated: true },
      { text: 'Webhooks for broadcast partners', gated: true },
      { text: 'Priority steward & billing support', gated: true },
    ],
  },
]

function formatPlan(plan: BillingPlanTier): string {
  return plan.charAt(0) + plan.slice(1).toLowerCase()
}

function formatDate(value: string | null): string {
  if (!value) {
    return 'N/A'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'N/A'
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

function planRank(plan: BillingPlanTier): number {
  return PLAN_SEQUENCE.indexOf(plan)
}

function nextPlan(plan: BillingPlanTier): BillingUpgradePlan | null {
  const rank = planRank(plan)
  if (rank < PLAN_SEQUENCE.length - 1) {
    return PLAN_SEQUENCE[rank + 1] as BillingUpgradePlan
  }
  return null
}

function getGraceBanner(overview: BillingOverview | null): string | null {
  if (!overview?.gracePlan || !overview.graceExpiresAt) {
    return null
  }
  const expiresAt = new Date(overview.graceExpiresAt)
  if (Number.isNaN(expiresAt.getTime())) {
    return null
  }
  if (expiresAt.getTime() <= Date.now()) {
    return null
  }
  const formattedExpiry = new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(expiresAt)
  return `A downgrade to ${formatPlan(
    overview.plan,
  )} is scheduled. ${formatPlan(overview.gracePlan)} benefits remain active until ${formattedExpiry}.`
}

function percentUsage(driverCount: number, driverLimit: number): number {
  if (driverLimit <= 0) {
    return 0
  }
  return Math.min(100, Math.round((driverCount / driverLimit) * 100))
}

export function BillingPage(): ReactElement {
  const {
    overview,
    isLoading,
    error,
    refresh,
    beginCheckout,
    launchPortal,
    isBypass,
  } = useBilling()
  const { showToast } = useToast()

  const [pendingPlan, setPendingPlan] = useState<BillingUpgradePlan | null>(
    null,
  )
  const [isPortalLoading, setIsPortalLoading] = useState(false)

  const accountPlan: BillingPlanTier = overview?.plan ?? 'FREE'
  const leagues = overview?.leagues ?? []
  const graceBanner = useMemo(() => getGraceBanner(overview), [overview])

  const handleCheckout = async (plan: BillingUpgradePlan) => {
    setPendingPlan(plan)
    try {
      const url = await beginCheckout(plan)
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
      showToast({
        title: `${formatPlan(plan)} checkout started`,
        description: 'Complete the checkout flow to apply the new plan.',
        variant: 'info',
      })
      await refresh()
    } catch (checkoutError) {
      const description =
        checkoutError instanceof Error
          ? checkoutError.message
          : 'Unable to start the checkout session.'
      showToast({
        title: 'Checkout failed',
        description,
        variant: 'error',
      })
    } finally {
      setPendingPlan(null)
    }
  }

  const handlePortal = async () => {
    setIsPortalLoading(true)
    try {
      const url = await launchPortal()
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
      showToast({
        title: 'Portal opened',
        description:
          'Manage your subscription inside the Stripe customer portal.',
        variant: 'success',
      })
    } catch (portalError) {
      const description =
        portalError instanceof Error
          ? portalError.message
          : 'Unable to open the billing portal. Please try again later.'
      showToast({
        title: 'Portal unavailable',
        description,
        variant: 'error',
      })
    } finally {
      setIsPortalLoading(false)
    }
  }

  if (isLoading && !overview) {
    return (
      <div className="space-y-6">
        <div className="rounded-3xl border border-slate-800/70 bg-slate-900/50 p-6">
          <div className="h-5 w-32 rounded bg-slate-800" />
          <div className="mt-3 h-4 w-48 rounded bg-slate-800" />
          <div className="mt-5 flex gap-3">
            <div className="h-10 w-32 rounded-full bg-slate-800" />
            <div className="h-10 w-28 rounded-full bg-slate-800" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <div
              key={index}
              className="rounded-3xl border border-slate-800/70 bg-slate-900/50 p-5"
            >
              <div className="h-4 w-24 rounded bg-slate-800" />
              <div className="mt-2 h-8 w-32 rounded bg-slate-800" />
              <div className="mt-4 space-y-2">
                <div className="h-3 w-full rounded bg-slate-800" />
                <div className="h-3 w-3/4 rounded bg-slate-800" />
                <div className="h-3 w-2/3 rounded bg-slate-800" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {isBypass ? (
        <div className="rounded-3xl border border-blue-500/40 bg-blue-500/10 p-4 text-sm text-blue-100">
          Billing demo mode active: upgrade and portal actions open mock URLs
          locally.
        </div>
      ) : null}

      {error ? (
        <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-5 text-sm text-rose-100">
          <p className="font-semibold">
            We could not load billing information.
          </p>
          <p className="mt-2 text-rose-100/80">{error.message}</p>
          <button
            type="button"
            onClick={() => {
              void refresh()
            }}
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-rose-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-rose-100 transition hover:border-rose-200"
          >
            Retry
          </button>
        </div>
      ) : null}

      {graceBanner ? (
        <div className="rounded-3xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
          {graceBanner}
        </div>
      ) : null}

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-100">
              Billing overview
            </h2>
            <p className="text-sm text-slate-200">
              Current plan:{' '}
              <span className="font-semibold text-slate-200">
                {formatPlan(accountPlan)}
              </span>
            </p>
            <p className="text-xs text-slate-200">
              Next renewal: {formatDate(overview?.currentPeriodEnd ?? null)}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              void handlePortal()
            }}
            disabled={!overview?.canManageSubscription || isPortalLoading}
            title={
              overview?.canManageSubscription
                ? undefined
                : 'Complete a checkout first to configure the customer portal.'
            }
            className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-5 py-2 text-sm font-semibold uppercase tracking-wide text-slate-200 transition hover:border-slate-500 hover:text-slate-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-300"
          >
            {isPortalLoading ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
            ) : null}
            Manage subscription
          </button>
        </header>
      </section>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold text-slate-100">
              Driver usage
            </h3>
            <p className="text-sm text-slate-200">
              Track roster sizes for each owned league.
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

        <div className="mt-5 space-y-4">
          {leagues.length === 0 ? (
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 text-sm text-slate-200">
              You have not created any leagues yet. Create a league to start
              tracking driver slots.
            </div>
          ) : (
            leagues.map((league) => {
              const usage = percentUsage(league.driverCount, league.driverLimit)
              const atLimit = league.driverCount >= league.driverLimit
              const suggestedUpgrade = nextPlan(accountPlan)
              return (
                <div
                  key={league.id}
                  className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/20"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-slate-100">
                        {league.name}
                      </p>
                      <p className="text-xs text-slate-200">
                        slug: {league.slug}
                      </p>
                    </div>
                    <div className="space-y-1 text-right text-xs text-slate-200">
                      <p>
                        Limit:{' '}
                        <span className="font-semibold text-slate-200">
                          {league.driverLimit}
                        </span>
                      </p>
                      <p>
                        Used:{' '}
                        <span className="font-semibold text-slate-200">
                          {league.driverCount}
                        </span>
                      </p>
                      {atLimit ? (
                        <span
                          className="inline-flex items-center rounded-full border border-amber-400/60 bg-amber-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-100"
                          title={
                            suggestedUpgrade
                              ? `Upgrade to ${formatPlan(
                                  suggestedUpgrade,
                                )} to unlock additional driver slots.`
                              : 'Driver limit reached for your current plan.'
                          }
                        >
                          Limit reached
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-4 h-2 w-full rounded-full bg-slate-800">
                    <div
                      className="h-2 rounded-full bg-sky-500 transition-[width]"
                      style={{ width: `${String(usage)}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-slate-200">Usage: {usage}%</p>
                </div>
              )
            })
          )}
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="text-xl font-semibold text-slate-100">
          Choose the right plan
        </h3>
        <div className="grid gap-4 md:grid-cols-3">
          {PLAN_OPTIONS.map((option) => {
            const currentPlan = accountPlan
            const currentRank = planRank(currentPlan)
            const optionRank = planRank(option.tier)
            const isCurrent = optionRank === currentRank
            const isDowngrade = optionRank < currentRank
            const isUpgrade = optionRank > currentRank
            const isPending = pendingPlan === option.tier
            const buttonDisabled =
              isCurrent || isDowngrade || (isPending && !isCurrent)
            const buttonTitle = isDowngrade
              ? 'Use the customer portal to manage downgrades.'
              : isCurrent
                ? 'You are already on this plan.'
                : undefined

            return (
              <div
                key={option.tier}
                className={`flex flex-col rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30 ${isCurrent ? 'border-sky-500/60' : ''}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-200">
                      {option.label}
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-slate-100">
                      {option.price}
                    </p>
                  </div>
                  {isCurrent ? (
                    <span className="rounded-full border border-sky-500/60 bg-sky-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-sky-200">
                      Current
                    </span>
                  ) : null}
                </div>
                <p className="mt-3 text-sm text-slate-200">
                  {option.description}
                </p>
                <ul className="mt-4 space-y-2 text-sm text-slate-200">
                  {option.features.map((feature) => {
                    const gatedTooltip =
                      feature.gated && optionRank > currentRank
                        ? `Upgrade to ${formatPlan(option.tier)} to unlock this feature.`
                        : undefined
                    return (
                      <li
                        key={feature.text}
                        className="flex items-center gap-2"
                        title={gatedTooltip}
                      >
                        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-sky-500/10 text-sky-300">
                          ✓
                        </span>
                        <span
                          className={
                            feature.gated && optionRank > currentRank
                              ? 'text-slate-200'
                              : ''
                          }
                        >
                          {feature.text}
                        </span>
                      </li>
                    )
                  })}
                </ul>
                <div className="mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      if (isUpgrade) {
                        void handleCheckout(option.tier as BillingUpgradePlan)
                      }
                    }}
                    disabled={buttonDisabled || (!isUpgrade && !isCurrent)}
                    title={buttonTitle}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold uppercase tracking-wide text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-300"
                  >
                    {isPending ? (
                      <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                    ) : null}
                    {isCurrent
                      ? 'Current plan'
                      : isDowngrade
                        ? 'Downgrade via portal'
                        : `Upgrade to ${option.label}`}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
