import { apiFetch } from './client'
import { ApiError } from './auth'
import type { PointsSchemeEntry } from '../types/leagues'

interface PointsSchemeResponse {
  entries: Array<{
    position: number
    points: number
  }>
}

export async function fetchPointsScheme(
  token: string,
  slug: string,
): Promise<PointsSchemeEntry[]> {
  const response = await apiFetch(`/leagues/${slug}/points-scheme`, {
    token,
  })

  if (response.status === 404) {
    return []
  }

  if (!response.ok) {
    throw new ApiError('Unable to load points scheme', response.status)
  }

  const payload = (await response.json()) as PointsSchemeResponse
  return payload.entries.map((entry) => ({
    position: entry.position,
    points: entry.points,
  }))
}

export async function updatePointsScheme(
  token: string,
  slug: string,
  entries: PointsSchemeEntry[],
): Promise<PointsSchemeEntry[]> {
  const response = await apiFetch(`/leagues/${slug}/points-scheme`, {
    method: 'PUT',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ entries }),
  })

  if (!response.ok) {
    throw new ApiError('Unable to save points scheme', response.status)
  }

  const payload = (await response.json()) as PointsSchemeResponse
  return payload.entries.map((entry) => ({
    position: entry.position,
    points: entry.points,
  }))
}
