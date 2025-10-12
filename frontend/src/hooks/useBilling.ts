import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchBillingOverview, openBillingPortal, startBillingCheckout } from '../api/billing'
import { useAuth } from './useAuth'
import type { BillingOverview, BillingPlanTier } from '../types/billing'

export type BillingUpgradePlan = Exclude<BillingPlanTier, 'FREE'>

const MOCK_BILLING_OVERVIEW: BillingOverview = {
  plan: 'FREE',
  currentPeriodEnd: null,
  gracePlan: null,
  graceExpiresAt: null,
  canManageSubscription: false,
  leagues: [
    {
      id: 'demo-league-1',
      name: 'Demo Racing League',
      slug: 'demo-racing-league',
      plan: 'FREE',
      driverLimit: 20,
      driverCount: 18,
    },
    {
      id: 'demo-league-2',
      name: 'Velocity Cup',
      slug: 'velocity-cup',
      plan: 'FREE',
      driverLimit: 20,
      driverCount: 20,
    },
  ],
}

interface UseBillingResult {
  overview: BillingOverview | null
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<BillingOverview | null>
  beginCheckout: (plan: BillingUpgradePlan) => Promise<string>
  launchPortal: () => Promise<string>
  isBypass: boolean
}

export function useBilling(): UseBillingResult {
  const { accessToken, isBypassAuth } = useAuth()
  const queryClient = useQueryClient()
  const shouldFetch = Boolean(accessToken)

  const query = useQuery({
    queryKey: ['billing-overview'],
    queryFn: () => fetchBillingOverview(accessToken ?? ''),
    enabled: shouldFetch,
    staleTime: 60_000,
  })

  const overview = shouldFetch ? query.data ?? null : MOCK_BILLING_OVERVIEW

  const refresh = useCallback(async () => {
    if (!shouldFetch) {
      return MOCK_BILLING_OVERVIEW
    }
    const result = await query.refetch()
    return result.data ?? null
  }, [shouldFetch, query])

  const beginCheckout = useCallback(
    async (plan: BillingUpgradePlan) => {
      if (!shouldFetch) {
        return `https://billing.gridboss.dev/checkout/${plan.toLowerCase()}`
      }

      if (!accessToken) {
        throw new Error('Not authenticated')
      }

      const url = await startBillingCheckout(accessToken, plan)
      await queryClient.invalidateQueries({ queryKey: ['billing-overview'], exact: true })
      return url
    },
    [shouldFetch, accessToken, queryClient],
  )

  const launchPortal = useCallback(async () => {
    if (!shouldFetch) {
      return 'https://billing.gridboss.dev/portal'
    }

    if (!accessToken) {
      throw new Error('Not authenticated')
    }

    return openBillingPortal(accessToken)
  }, [shouldFetch, accessToken])

  let resolvedError: Error | null = null
  if (shouldFetch && query.isError) {
    resolvedError =
      query.error instanceof Error
        ? query.error
        : new Error('Unknown error while loading billing overview')
  }

  return {
    overview,
    isLoading: shouldFetch ? query.isLoading : false,
    error: resolvedError,
    refresh,
    beginCheckout,
    launchPortal,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
