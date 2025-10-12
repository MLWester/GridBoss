import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchPointsScheme, updatePointsScheme } from '../api/points'
import { useAuth } from './useAuth'
import type { PointsSchemeEntry } from '../types/leagues'

export const DEFAULT_POINTS_SCHEME: PointsSchemeEntry[] = [
  { position: 1, points: 25 },
  { position: 2, points: 18 },
  { position: 3, points: 15 },
  { position: 4, points: 12 },
  { position: 5, points: 10 },
  { position: 6, points: 8 },
  { position: 7, points: 6 },
  { position: 8, points: 4 },
  { position: 9, points: 2 },
  { position: 10, points: 1 },
]

function clonePoints(entries: PointsSchemeEntry[]): PointsSchemeEntry[] {
  return entries.map((entry) => ({ ...entry }))
}

export function usePointsScheme(slug: string | null) {
  const { accessToken, isBypassAuth } = useAuth()
  const shouldFetch = Boolean(accessToken) && Boolean(slug)
  const queryClient = useQueryClient()

  const [localScheme, setLocalScheme] = useState<PointsSchemeEntry[]>(clonePoints(DEFAULT_POINTS_SCHEME))

  useEffect(() => {
    setLocalScheme(clonePoints(DEFAULT_POINTS_SCHEME))
  }, [slug])

  const schemeQuery = useQuery<PointsSchemeEntry[]>({
    queryKey: ['points-scheme', slug],
    queryFn: () => fetchPointsScheme(accessToken ?? '', slug ?? ''),
    enabled: shouldFetch,
    staleTime: 60_000,
  })

  const entries = useMemo(() => {
    if (shouldFetch) {
      const data = schemeQuery.data
      if (!data || data.length === 0) {
        return clonePoints(DEFAULT_POINTS_SCHEME)
      }
      return clonePoints(data)
    }
    return clonePoints(localScheme)
  }, [schemeQuery.data, localScheme, shouldFetch])

  const save = useCallback(
    async (next: PointsSchemeEntry[]) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const saved = await updatePointsScheme(token, slug, next)
        queryClient.setQueryData<PointsSchemeEntry[]>(['points-scheme', slug], saved)
        return clonePoints(saved)
      }

      const snapshot = clonePoints(next)
      setLocalScheme(snapshot)
      return snapshot
    },
    [slug, shouldFetch, accessToken, queryClient],
  )

  const resetToDefault = useCallback(() => {
    if (!slug) {
      return clonePoints(DEFAULT_POINTS_SCHEME)
    }

    if (shouldFetch) {
      queryClient.setQueryData<PointsSchemeEntry[]>(['points-scheme', slug], clonePoints(DEFAULT_POINTS_SCHEME))
    } else {
      setLocalScheme(clonePoints(DEFAULT_POINTS_SCHEME))
    }

    return clonePoints(DEFAULT_POINTS_SCHEME)
  }, [slug, shouldFetch, queryClient])

  return {
    entries,
    isLoading: shouldFetch ? schemeQuery.isLoading : false,
    error: shouldFetch ? schemeQuery.error ?? null : null,
    save,
    resetToDefault,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
