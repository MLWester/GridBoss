import { apiFetch } from './client'
import { ApiError } from './auth'
import type {
  ResultEntryRead,
  ResultEntrySummary,
  SubmitResultEntry,
} from '../types/results'

function mapEntry(entry: ResultEntryRead): ResultEntrySummary {
  return {
    driverId: entry.driver_id,
    finishPosition: entry.finish_position,
    status: entry.status,
    bonusPoints:
      typeof entry.bonus_points === 'number' ? entry.bonus_points : 0,
    penaltyPoints:
      typeof entry.penalty_points === 'number' ? entry.penalty_points : 0,
  }
}

export async function fetchEventResults(
  token: string,
  eventId: string,
): Promise<ResultEntrySummary[]> {
  const response = await apiFetch(`/events/${eventId}/results`, {
    token,
  })

  if (response.status === 404) {
    return []
  }

  if (!response.ok) {
    throw new ApiError('Unable to load results', response.status)
  }

  const payload = (await response.json()) as ResultEntryRead[]
  return payload.map(mapEntry)
}

export interface SubmitResultsPayload {
  entries: SubmitResultEntry[]
}

export async function submitEventResults(
  token: string,
  eventId: string,
  payload: SubmitResultsPayload,
  idempotencyKey: string,
): Promise<void> {
  const response = await apiFetch(`/events/${eventId}/results`, {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(payload),
  })

  if (response.status === 404) {
    throw new ApiError('Event not found', response.status)
  }

  if (response.status === 402) {
    const detail = (await response.json().catch(() => null)) as {
      message?: unknown
    } | null
    const message =
      detail?.message != null && typeof detail.message === 'string'
        ? detail.message
        : 'Plan upgrade required to post results'
    throw new ApiError(message, response.status)
  }

  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as {
      message?: unknown
    } | null
    if (detail?.message != null && typeof detail.message === 'string') {
      throw new ApiError(detail.message, response.status)
    }
    throw new ApiError('Unable to submit results', response.status)
  }
}
