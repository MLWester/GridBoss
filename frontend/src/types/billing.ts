export type BillingPlanTier = 'FREE' | 'PRO' | 'ELITE'

export interface BillingLeagueUsage {
  id: string
  name: string
  slug: string
  plan: BillingPlanTier
  driverLimit: number
  driverCount: number
}

export interface BillingOverview {
  plan: BillingPlanTier
  currentPeriodEnd: string | null
  gracePlan: BillingPlanTier | null
  graceExpiresAt: string | null
  canManageSubscription: boolean
  leagues: BillingLeagueUsage[]
}
