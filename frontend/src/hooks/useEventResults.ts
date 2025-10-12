import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchEventResults, submitEventResults } from '../api/results'
import { useAuth } from './useAuth'
import type {
  ResultEntrySummary,
  ResultStatus,
  SubmitResultEntry,
} from '../types/results'
import type { DriverSummary } from '../types/drivers'

interface UseEventResultsResult {
  entries: ResultEntrySummary[]
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
  setEntries: (entries: ResultEntrySummary[]) => void
  submit: (entries: ResultEntrySummary[]) => Promise<void>
  isBypass: boolean
}

const defaultStatuses: ResultStatus[] = ['FINISHED', 'DNF', 'DNS', 'DSQ']

function asResultEntries(drivers: DriverSummary[]): ResultEntrySummary[] {
  return drivers.map<ResultEntrySummary>((driver, index) => ({
    driverId: driver.id,
    finishPosition: index + 1,
    status: 'FINISHED',
    bonusPoints: 0,
    penaltyPoints: 0,
  }))
}

function generateIdempotencyKey(): string {
  if (
    typeof window !== 'undefined' &&
    typeof window.crypto !== 'undefined' &&
    typeof window.crypto.randomUUID === 'function'
  ) {
    return window.crypto.randomUUID()
  }
  return `idemp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export function useEventResults(
  eventId: string | null,
  drivers: DriverSummary[],
): UseEventResultsResult {
  const { accessToken, isBypassAuth } = useAuth()
  const shouldFetch = Boolean(accessToken) && Boolean(eventId)
  const queryClient = useQueryClient()

  const defaultEntries = useMemo(() => asResultEntries(drivers), [drivers])
  const [localEntries, setLocalEntries] =
    useState<ResultEntrySummary[]>(defaultEntries)

  useEffect(() => {
    if (!eventId) {
      setLocalEntries(defaultEntries)
    }
  }, [defaultEntries, eventId])

  const resultsQuery = useQuery<ResultEntrySummary[]>({
    queryKey: ['event-results', eventId],
    queryFn: () => fetchEventResults(accessToken ?? '', eventId ?? ''),
    enabled: shouldFetch,
    staleTime: 0,
  })

  const entries = shouldFetch
    ? (resultsQuery.data ?? defaultEntries)
    : localEntries

  const setEntries = useCallback(
    (next: ResultEntrySummary[]) => {
      if (shouldFetch) {
        queryClient.setQueryData<ResultEntrySummary[]>(
          ['event-results', eventId],
          next,
        )
      } else {
        setLocalEntries(next)
      }
    },
    [eventId, queryClient, shouldFetch],
  )

  const refresh = useCallback(async () => {
    if (!eventId) return
    if (!shouldFetch) {
      setLocalEntries(asResultEntries(drivers))
      return
    }
    await queryClient.invalidateQueries({
      queryKey: ['event-results', eventId],
      exact: true,
    })
  }, [drivers, eventId, queryClient, shouldFetch])

  const submit = useCallback(
    async (payload: ResultEntrySummary[]) => {
      if (!eventId) {
        throw new Error('No event selected')
      }

      const normalized = payload.map<ResultEntrySummary>((entry, index) => ({
        driverId: entry.driverId,
        finishPosition: index + 1,
        status: defaultStatuses.includes(entry.status)
          ? entry.status
          : 'FINISHED',
        bonusPoints: entry.bonusPoints,
        penaltyPoints: entry.penaltyPoints,
      }))
      const submitEntries: SubmitResultEntry[] = normalized.map((entry) => ({
        driverId: entry.driverId,
        finishPosition: entry.finishPosition,
        status: entry.status,
        bonusPoints: entry.bonusPoints,
        penaltyPoints: entry.penaltyPoints,
      }))

      if (shouldFetch) {
        if (!accessToken) {
          throw new Error('Not authenticated')
        }
        const idempotencyKey = generateIdempotencyKey()
        await submitEventResults(
          accessToken,
          eventId,
          { entries: submitEntries },
          idempotencyKey,
        )
        await refresh()
        return
      }

      setLocalEntries(normalized)
    },
    [eventId, shouldFetch, accessToken, refresh],
  )

  return {
    entries,
    isLoading: shouldFetch ? resultsQuery.isLoading : false,
    error: shouldFetch ? (resultsQuery.error ?? null) : null,
    refresh,
    setEntries,
    submit,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
