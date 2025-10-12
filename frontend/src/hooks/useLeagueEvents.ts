import { useCallback, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createEvent,
  deleteEvent,
  fetchLeagueEvents,
  updateEvent,
} from '../api/events'
import { useAuth } from './useAuth'
import type { EventSummary, EventStatus } from '../types/events'

interface UseLeagueEventsResult {
  events: EventSummary[]
  isLoading: boolean
  isFetching: boolean
  error: Error | null
  refetch: () => Promise<void>
  createEvent: (payload: CreateEventPayload) => Promise<EventSummary>
  updateEvent: (
    eventId: string,
    payload: UpdateEventPayload,
  ) => Promise<EventSummary>
  deleteEvent: (eventId: string) => Promise<void>
  isBypass: boolean
}

export interface CreateEventPayload {
  name: string
  track: string | null
  startTime: string
  laps: number | null
  distanceKm: number | null
  status?: EventStatus
}

export interface UpdateEventPayload {
  name?: string
  track?: string | null
  startTime?: string
  status?: EventStatus
  laps?: number | null
  distanceKm?: number | null
}

function createMockEvents(slug: string): EventSummary[] {
  const now = new Date()
  const upcoming = new Date(now.getTime() + 5 * 24 * 60 * 60 * 1000)
  const upcoming2 = new Date(now.getTime() + 12 * 24 * 60 * 60 * 1000)
  const completed = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

  return [
    {
      id: `${slug}-event-upcoming-1`,
      name: 'GridBoss Showcase',
      track: 'Silverstone Circuit',
      startTime: upcoming.toISOString(),
      status: 'SCHEDULED',
      laps: 28,
      distanceKm: 150,
    },
    {
      id: `${slug}-event-upcoming-2`,
      name: 'Nightfall Sprint',
      track: 'Suzuka',
      startTime: upcoming2.toISOString(),
      status: 'SCHEDULED',
      laps: 18,
      distanceKm: 95,
    },
    {
      id: `${slug}-event-completed-1`,
      name: 'Opening Grand Prix',
      track: 'Spa-Francorchamps',
      startTime: completed.toISOString(),
      status: 'COMPLETED',
      laps: 32,
      distanceKm: 180,
    },
  ]
}

export function useLeagueEvents(slug: string): UseLeagueEventsResult {
  const { accessToken, isBypassAuth } = useAuth()
  const shouldFetch = Boolean(accessToken)
  const queryClient = useQueryClient()

  const [localEvents, setLocalEvents] = useState<EventSummary[]>(
    createMockEvents(slug || 'demo'),
  )

  useEffect(() => {
    setLocalEvents(createMockEvents(slug || 'demo'))
  }, [slug])

  const eventsQuery = useQuery<EventSummary[]>({
    queryKey: ['league-events', slug],
    queryFn: () => fetchLeagueEvents(accessToken ?? '', slug),
    enabled: shouldFetch && Boolean(slug),
    staleTime: 30_000,
  })

  const events = shouldFetch ? (eventsQuery.data ?? []) : localEvents

  const refetch = useCallback(async () => {
    if (!shouldFetch) {
      return
    }
    await queryClient.refetchQueries({
      queryKey: ['league-events', slug],
      exact: true,
    })
  }, [queryClient, shouldFetch, slug])

  const createEventEntry = useCallback(
    async (payload: CreateEventPayload) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      const payloadWithStatus = {
        ...payload,
        status: payload.status ?? 'SCHEDULED',
      }

      if (shouldFetch) {
        const token = accessToken as string
        const created = await createEvent(token, slug, {
          name: payloadWithStatus.name,
          track: payloadWithStatus.track,
          start_time: payloadWithStatus.startTime,
          status: payloadWithStatus.status,
          laps: payloadWithStatus.laps,
          distance_km: payloadWithStatus.distanceKm,
        })
        queryClient.setQueryData<EventSummary[]>(
          ['league-events', slug],
          (current = []) => [...current, created],
        )
        return created
      }

      const event: EventSummary = {
        id: `${slug || 'demo'}-event-${Date.now().toString(36)}`,
        name: payloadWithStatus.name,
        track: payloadWithStatus.track,
        startTime: payloadWithStatus.startTime,
        status: payloadWithStatus.status,
        laps: payloadWithStatus.laps,
        distanceKm: payloadWithStatus.distanceKm,
      }
      setLocalEvents((current) => [...current, event])
      return event
    },
    [slug, shouldFetch, accessToken, queryClient],
  )

  const updateEventEntry = useCallback(
    async (eventId: string, payload: UpdateEventPayload) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        const updated = await updateEvent(token, eventId, {
          name: payload.name,
          track: payload.track,
          start_time: payload.startTime,
          status: payload.status,
          laps: payload.laps,
          distance_km: payload.distanceKm,
        })
        queryClient.setQueryData<EventSummary[]>(
          ['league-events', slug],
          (current = []) =>
            current.map((event) => (event.id === eventId ? updated : event)),
        )
        return updated
      }

      const existing = localEvents.find((event) => event.id === eventId)
      if (!existing) {
        throw new Error('Event not found')
      }
      const updated: EventSummary = {
        ...existing,
        name: payload.name ?? existing.name,
        track: payload.track ?? existing.track,
        startTime: payload.startTime ?? existing.startTime,
        status: payload.status ?? existing.status,
        laps: payload.laps ?? existing.laps,
        distanceKm: payload.distanceKm ?? existing.distanceKm,
      }
      setLocalEvents((current) =>
        current.map((event) => (event.id === eventId ? updated : event)),
      )
      return updated
    },
    [slug, shouldFetch, accessToken, queryClient, localEvents],
  )

  const deleteEventEntry = useCallback(
    async (eventId: string) => {
      if (!slug) {
        throw new Error('Missing league identifier')
      }

      if (shouldFetch) {
        const token = accessToken as string
        await deleteEvent(token, eventId)
        queryClient.setQueryData<EventSummary[]>(
          ['league-events', slug],
          (current = []) => current.filter((event) => event.id !== eventId),
        )
        return
      }

      setLocalEvents((current) =>
        current.filter((event) => event.id !== eventId),
      )
    },
    [slug, shouldFetch, accessToken, queryClient],
  )

  return {
    events,
    isLoading: shouldFetch ? eventsQuery.isLoading : false,
    isFetching: shouldFetch ? eventsQuery.isFetching : false,
    error: shouldFetch ? (eventsQuery.error ?? null) : null,
    refetch,
    createEvent: createEventEntry,
    updateEvent: updateEventEntry,
    deleteEvent: deleteEventEntry,
    isBypass: isBypassAuth || !shouldFetch,
  }
}
