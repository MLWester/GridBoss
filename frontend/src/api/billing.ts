import { apiFetch } from './client'
import { ApiError } from './auth'
import type { BillingOverview, BillingPlanTier } from '../types/billing'

interface BillingLeagueUsageRead {
  id: string
  name: string
  slug: string
  plan: string | null
  driver_limit: number
  driver_count: number
}

interface BillingOverviewRead {
  plan: string | null
  current_period_end: string | null
  grace_plan: string | null
  grace_expires_at: string | null
  can_manage_subscription: boolean
  leagues: BillingLeagueUsageRead[]
}

function mapOverview(payload: BillingOverviewRead): BillingOverview {
  return {
    plan: (payload.plan ?? 'FREE').toUpperCase() as BillingPlanTier,
    currentPeriodEnd: payload.current_period_end,
    gracePlan: payload.grace_plan ? (payload.grace_plan.toUpperCase() as BillingPlanTier) : null,
    graceExpiresAt: payload.grace_expires_at,
    canManageSubscription: payload.can_manage_subscription,
    leagues: payload.leagues.map((league) => ({
      id: league.id,
      name: league.name,
      slug: league.slug,
      plan: (league.plan ?? 'FREE').toUpperCase() as BillingPlanTier,
      driverLimit: league.driver_limit,
      driverCount: league.driver_count,
    })),
  }
}

export async function fetchBillingOverview(token: string): Promise<BillingOverview> {
  const response = await apiFetch('/billing/overview', {
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to load billing overview', response.status)
  }

  const payload = (await response.json()) as BillingOverviewRead
  return mapOverview(payload)
}

export async function startBillingCheckout(token: string, plan: Exclude<BillingPlanTier, 'FREE'>): Promise<string> {
  const response = await apiFetch('/billing/checkout', {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ plan }),
  })

  if (response.status === 402) {
    throw new ApiError('Billing plan requires manual approval.', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to start checkout', response.status)
  }

  const payload = (await response.json()) as { url: string }
  return payload.url
}

export async function openBillingPortal(token: string): Promise<string> {
  const response = await apiFetch('/billing/portal', {
    method: 'POST',
    token,
  })

  if (response.status === 400) {
    throw new ApiError('Complete checkout before accessing the billing portal.', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to open billing portal', response.status)
  }

  const payload = (await response.json()) as { url: string }
  return payload.url
}
