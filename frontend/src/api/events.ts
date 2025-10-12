import { apiFetch } from './client'
import { ApiError } from './auth'
import type { EventRead, EventSummary, EventStatus } from '../types/events'

function mapEvent(event: EventRead): EventSummary {
  return {
    id: event.id,
    name: event.name,
    track: event.track ?? null,
    startTime: event.start_time,
    status: event.status,
    laps: typeof event.laps === 'number' ? event.laps : null,
    distanceKm:
      typeof event.distance_km === 'number' ? event.distance_km : null,
  }
}

export async function fetchLeagueEvents(
  token: string,
  slug: string,
): Promise<EventSummary[]> {
  const response = await apiFetch(`/leagues/${slug}/events`, {
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to load events', response.status)
  }

  const payload = (await response.json()) as EventRead[]
  return payload.map(mapEvent)
}

interface CreateEventRequest {
  name: string
  track: string | null
  start_time: string
  status?: EventStatus
  laps?: number | null
  distance_km?: number | null
}

export async function createEvent(
  token: string,
  slug: string,
  body: CreateEventRequest,
): Promise<EventSummary> {
  const response = await apiFetch(`/leagues/${slug}/events`, {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new ApiError('Unable to create event', response.status)
  }

  const payload = (await response.json()) as EventRead
  return mapEvent(payload)
}

interface UpdateEventRequest {
  name?: string
  track?: string | null
  start_time?: string
  status?: EventStatus
  laps?: number | null
  distance_km?: number | null
}

export async function updateEvent(
  token: string,
  eventId: string,
  body: UpdateEventRequest,
): Promise<EventSummary> {
  const response = await apiFetch(`/events/${eventId}`, {
    method: 'PATCH',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 404) {
    throw new ApiError('Event not found', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to update event', response.status)
  }

  const payload = (await response.json()) as EventRead
  return mapEvent(payload)
}

export async function deleteEvent(
  token: string,
  eventId: string,
): Promise<void> {
  const response = await apiFetch(`/events/${eventId}`, {
    method: 'DELETE',
    token,
  })

  if (response.status === 404) {
    throw new ApiError('Event not found', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to delete event', response.status)
  }
}
