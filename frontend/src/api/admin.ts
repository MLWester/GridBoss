import { apiFetch } from './client'
import { ApiError } from './auth'
import type { BillingPlanTier } from '../types/billing'
import type { AdminLeagueSummary, AdminSearchResponse, AdminUserSummary } from '../types/admin'

interface AdminUserSummaryRead {
  id: string
  discord_username: string | null
  email: string | null
  created_at: string
  leagues_owned: number
  billing_plan: string | null
  subscription_status: string | null
  stripe_customer_id: string | null
}

interface AdminLeagueSummaryRead {
  id: string
  name: string
  slug: string
  plan: string | null
  driver_limit: number
  driver_count: number
  owner_id: string | null
  owner_discord_username: string | null
  owner_email: string | null
  billing_plan: string | null
  discord_active: boolean
}

interface AdminSearchResponseRead {
  users: AdminUserSummaryRead[]
  leagues: AdminLeagueSummaryRead[]
}

function normalizePlan(plan?: string | null): BillingPlanTier {
  const upper = (plan ?? 'FREE').toUpperCase()
  if (upper === 'PRO' || upper === 'ELITE') {
    return upper
  }
  return 'FREE'
}

function mapUserSummary(payload: AdminUserSummaryRead): AdminUserSummary {
  return {
    id: payload.id,
    discordUsername: payload.discord_username,
    email: payload.email,
    createdAt: payload.created_at,
    leaguesOwned: payload.leagues_owned,
    billingPlan: normalizePlan(payload.billing_plan),
    subscriptionStatus: payload.subscription_status,
    stripeCustomerId: payload.stripe_customer_id,
  }
}

function mapLeagueSummary(payload: AdminLeagueSummaryRead): AdminLeagueSummary {
  return {
    id: payload.id,
    name: payload.name,
    slug: payload.slug,
    plan: normalizePlan(payload.plan),
    driverLimit: payload.driver_limit,
    driverCount: payload.driver_count,
    ownerId: payload.owner_id,
    ownerDiscordUsername: payload.owner_discord_username,
    ownerEmail: payload.owner_email,
    billingPlan: normalizePlan(payload.billing_plan),
    discordActive: payload.discord_active,
  }
}

export async function fetchAdminSearch(token: string, query: string): Promise<AdminSearchResponse> {
  const params = query ? `?query=${encodeURIComponent(query)}` : ''
  const response = await apiFetch(`/admin/search${params}`, {
    token,
  })

  if (response.status === 404) {
    throw new ApiError('Admin console is not enabled.', response.status)
  }

  if (response.status === 403) {
    throw new ApiError('Founder access required to view the admin console.', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to load admin data', response.status)
  }

  const payload = (await response.json()) as AdminSearchResponseRead
  return {
    users: payload.users.map(mapUserSummary),
    leagues: payload.leagues.map(mapLeagueSummary),
  }
}

export async function toggleLeagueDiscord(
  token: string,
  leagueId: string,
  isActive: boolean,
): Promise<AdminLeagueSummary> {
  const response = await apiFetch(`/admin/leagues/${leagueId}/discord/toggle`, {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ is_active: isActive }),
  })

  if (!response.ok) {
    throw new ApiError('Unable to update Discord integration', response.status)
  }

  const payload = (await response.json()) as AdminLeagueSummaryRead
  return mapLeagueSummary(payload)
}

export async function overrideLeaguePlan(
  token: string,
  leagueId: string,
  plan: BillingPlanTier,
): Promise<AdminLeagueSummary> {
  const response = await apiFetch(`/admin/leagues/${leagueId}/plan`, {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ plan }),
  })

  if (!response.ok) {
    throw new ApiError('Unable to override league plan', response.status)
  }

  const payload = (await response.json()) as AdminLeagueSummaryRead
  return mapLeagueSummary(payload)
}
