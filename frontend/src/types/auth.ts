export type LeagueRole = 'OWNER' | 'ADMIN' | 'STEWARD' | 'DRIVER'

export interface UserSummary {
  id: string
  discord_id: string | null
  discord_username: string | null
  avatar_url: string | null
  email: string | null
}

export interface MembershipSummary {
  league_id: string
  league_slug: string
  league_name: string
  role: LeagueRole
}

export interface BillingPlanSummary {
  plan: string | null
  current_period_end: string | null
}

export interface MeResponse {
  user: UserSummary
  memberships: MembershipSummary[]
  billingPlan: BillingPlanSummary | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
