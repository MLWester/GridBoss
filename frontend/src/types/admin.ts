import type { BillingPlanTier } from './billing'

export interface AdminUserSummary {
  id: string
  discordUsername: string | null
  email: string | null
  createdAt: string
  leaguesOwned: number
  billingPlan: BillingPlanTier
  subscriptionStatus: string | null
  stripeCustomerId: string | null
}

export interface AdminLeagueSummary {
  id: string
  name: string
  slug: string
  plan: BillingPlanTier
  driverLimit: number
  driverCount: number
  ownerId: string | null
  ownerDiscordUsername: string | null
  ownerEmail: string | null
  billingPlan: BillingPlanTier
  discordActive: boolean
}

export interface AdminSearchResponse {
  users: AdminUserSummary[]
  leagues: AdminLeagueSummary[]
}
