import { useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import { useAuth } from '../hooks/useAuth'
import { useLeagueEvents } from '../hooks/useLeagueEvents'
import { useToast } from '../hooks/useToast'
import type { EventSummary, EventStatus } from '../types/events'
import type { LeagueRole } from '../types/auth'

interface EventFormState {
  name: string
  track: string
  startLocal: string
  laps: string
  distanceKm: string
  status: EventStatus
}

function canManageEvents(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN' || role === 'STEWARD'
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Unknown'
  }
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date)
}

function toLocalInput(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const offset = date.getTimezoneOffset()
  const local = new Date(date.getTime() - offset * 60 * 1000)
  return local.toISOString().slice(0, 16)
}

function fromLocalInput(value: string): string {
  if (!value) {
    return new Date().toISOString()
  }
  const local = new Date(value)
  if (Number.isNaN(local.getTime())) {
    return new Date().toISOString()
  }
  return local.toISOString()
}

function statusTone(status: EventStatus): string {
  if (status === 'COMPLETED') {
    return 'border-emerald-400/60 bg-emerald-500/10 text-emerald-200'
  }
  if (status === 'CANCELLED') {
    return 'border-rose-400/60 bg-rose-500/10 text-rose-200'
  }
  return 'border-sky-400/60 bg-sky-500/10 text-sky-100'
}

const statusOptions: EventStatus[] = ['SCHEDULED', 'COMPLETED', 'CANCELLED']

interface EventModalProps {
  open: boolean
  title: string
  form: EventFormState
  onChange: (state: EventFormState) => void
  onClose: () => void
  onSubmit: () => Promise<void>
  isSubmitting: boolean
  isEdit?: boolean
}

function EventModal({
  open,
  title,
  form,
  onChange,
  onClose,
  onSubmit,
  isSubmitting,
  isEdit = false,
}: EventModalProps): ReactElement | null {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/95 p-8 text-slate-100 shadow-xl shadow-slate-950/60">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold">{title}</h2>
            <p className="mt-2 text-sm text-slate-400">
              Configure the event details. Start time uses your local timezone
              and will be stored in UTC.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              onClose()
            }}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
          >
            Close
          </button>
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Event name
              <input
                value={form.name}
                onChange={(event) => {
                  onChange({ ...form, name: event.target.value })
                }}
                placeholder="GridBoss Grand Prix"
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Track
              <input
                value={form.track}
                onChange={(event) => {
                  onChange({ ...form, track: event.target.value })
                }}
                placeholder="Monza"
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Start time
              <input
                type="datetime-local"
                value={form.startLocal}
                onChange={(event) => {
                  onChange({ ...form, startLocal: event.target.value })
                }}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
              />
            </label>
          </div>

          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Laps
              <input
                value={form.laps}
                onChange={(event) => {
                  onChange({ ...form, laps: event.target.value })
                }}
                placeholder="30"
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Distance (km)
              <input
                value={form.distanceKm}
                onChange={(event) => {
                  onChange({ ...form, distanceKm: event.target.value })
                }}
                placeholder="150"
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
              />
            </label>

            {isEdit ? (
              <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
                Status
                <select
                  value={form.status}
                  onChange={(event) => {
                    onChange({
                      ...form,
                      status: event.target.value as EventStatus,
                    })
                  }}
                  className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
                >
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status.toLowerCase()}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => {
              onClose()
            }}
            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isSubmitting || !form.name.trim() || !form.startLocal}
            onClick={() => {
              void onSubmit()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isSubmitting ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
            ) : null}
            Save event
          </button>
        </div>
      </div>
    </div>
  )
}

interface ConfirmModalProps {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  tone: 'danger' | 'neutral'
  onConfirm: () => Promise<void>
  onClose: () => void
  isConfirming: boolean
}

function ConfirmModal({
  open,
  title,
  description,
  confirmLabel,
  tone,
  onConfirm,
  onClose,
  isConfirming,
}: ConfirmModalProps): ReactElement | null {
  if (!open) return null

  const buttonClasses =
    tone === 'danger'
      ? 'inline-flex items-center gap-2 rounded-full bg-rose-500 px-5 py-2 text-sm font-semibold text-rose-50 transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400'
      : 'inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-950/95 p-8 text-slate-100 shadow-xl shadow-slate-950/60">
        <h3 className="text-xl font-semibold">{title}</h3>
        <p className="mt-3 text-sm text-slate-300">{description}</p>
        <div className="mt-6 flex items-center justify-end gap-3 text-sm">
          <button
            type="button"
            onClick={() => {
              onClose()
            }}
            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isConfirming}
            onClick={() => {
              void onConfirm()
            }}
            className={buttonClasses}
          >
            {isConfirming ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
            ) : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function partitionEvents(events: EventSummary[]): {
  upcoming: EventSummary[]
  completed: EventSummary[]
} {
  const now = Date.now()
  const upcoming: EventSummary[] = []
  const completed: EventSummary[] = []
  for (const event of events) {
    const start = new Date(event.startTime).getTime()
    if (
      event.status === 'COMPLETED' ||
      event.status === 'CANCELLED' ||
      start < now
    ) {
      completed.push(event)
    } else {
      upcoming.push(event)
    }
  }

  upcoming.sort(
    (a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime(),
  )
  completed.sort(
    (a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime(),
  )
  return { upcoming, completed }
}

export function LeagueEventsPage(): ReactElement {
  const { slug = '' } = useParams<{ slug: string }>()
  const { overview } = useOutletContext<LeagueOutletContext>()
  const { memberships, isLoading: isAuthLoading } = useAuth()
  const { showToast } = useToast()
  const {
    events,
    isLoading,
    isFetching,
    error,
    refetch,
    createEvent,
    updateEvent,
    deleteEvent,
    isBypass,
  } = useLeagueEvents(slug)

  const membership = useMemo(
    () => memberships.find((item) => item.league_slug === slug) ?? null,
    [memberships, slug],
  )

  const role: LeagueRole | null =
    membership?.role ?? overview?.league.role ?? null
  const canEdit = canManageEvents(role)

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<EventSummary | null>(null)
  const [formState, setFormState] = useState<EventFormState>({
    name: '',
    track: '',
    startLocal: '',
    laps: '',
    distanceKm: '',
    status: 'SCHEDULED',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [confirmState, setConfirmState] = useState<{
    type: 'cancel' | 'delete' | null
    event: EventSummary | null
  }>({ type: null, event: null })
  const [isConfirming, setIsConfirming] = useState(false)

  const { upcoming, completed } = useMemo(
    () => partitionEvents(events),
    [events],
  )

  const startCreate = () => {
    const defaultStart = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)
    setFormState({
      name: '',
      track: '',
      startLocal: toLocalInput(defaultStart.toISOString()),
      laps: '',
      distanceKm: '',
      status: 'SCHEDULED',
    })
    setIsCreateOpen(true)
  }

  const startEdit = (event: EventSummary) => {
    setEditTarget(event)
    setFormState({
      name: event.name,
      track: event.track ?? '',
      startLocal: toLocalInput(event.startTime),
      laps: event.laps != null ? event.laps.toString() : '',
      distanceKm: event.distanceKm != null ? event.distanceKm.toString() : '',
      status: event.status,
    })
  }

  const closeModals = () => {
    setIsCreateOpen(false)
    setEditTarget(null)
    setFormState({
      name: '',
      track: '',
      startLocal: '',
      laps: '',
      distanceKm: '',
      status: 'SCHEDULED',
    })
  }

  const handleCreate = async () => {
    setIsSubmitting(true)
    try {
      const payload = {
        name: formState.name.trim(),
        track: formState.track.trim() || null,
        startTime: fromLocalInput(formState.startLocal),
        laps: formState.laps
          ? Number.parseInt(formState.laps, 10) || null
          : null,
        distanceKm: formState.distanceKm
          ? Number.parseFloat(formState.distanceKm) || null
          : null,
        status: 'SCHEDULED' as EventStatus,
      }
      const event = await createEvent(payload)
      showToast({
        title: 'Event created',
        description: `${event.name} has been scheduled.`,
        variant: 'success',
      })
      closeModals()
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to create event'
      showToast({
        title: 'Create failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUpdate = async () => {
    if (!editTarget) {
      return
    }
    setIsSubmitting(true)
    try {
      const payload = {
        name: formState.name.trim(),
        track: formState.track.trim() || null,
        startTime: formState.startLocal
          ? fromLocalInput(formState.startLocal)
          : undefined,
        status: formState.status,
        laps: formState.laps
          ? Number.parseInt(formState.laps, 10) || null
          : null,
        distanceKm: formState.distanceKm
          ? Number.parseFloat(formState.distanceKm) || null
          : null,
      }
      const updated = await updateEvent(editTarget.id, payload)
      showToast({
        title: 'Event updated',
        description: `${updated.name} has been updated.`,
        variant: 'success',
      })
      closeModals()
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to update event'
      showToast({
        title: 'Update failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancelEvent = async (event: EventSummary) => {
    setIsConfirming(true)
    try {
      await updateEvent(event.id, { status: 'CANCELLED' })
      showToast({
        title: 'Event cancelled',
        description: `${event.name} has been marked as cancelled.`,
        variant: 'success',
      })
      setConfirmState({ type: null, event: null })
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to cancel event'
      showToast({
        title: 'Cancel failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsConfirming(false)
    }
  }

  const handleDeleteEvent = async (event: EventSummary) => {
    setIsConfirming(true)
    try {
      await deleteEvent(event.id)
      showToast({
        title: 'Event deleted',
        description: `${event.name} has been removed.`,
        variant: 'success',
      })
      setConfirmState({ type: null, event: null })
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to delete event'
      showToast({
        title: 'Delete failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsConfirming(false)
    }
  }

  if (isLoading || isAuthLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index.toString()}
            className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/30"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="h-5 w-32 rounded bg-slate-800" />
              <div className="h-6 w-16 rounded-full bg-slate-800" />
            </div>
            <div className="mt-3 h-4 w-24 rounded bg-slate-800" />
            <div className="mt-4 h-3 w-full rounded bg-slate-800" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-100">
        <p className="font-semibold">We could not load the events schedule.</p>
        <p className="mt-1 text-rose-100/80">{error.message}</p>
        <button
          type="button"
          onClick={() => {
            void refetch()
          }}
          className="mt-4 inline-flex items-center gap-2 rounded-full border border-rose-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-rose-100 transition hover:border-rose-200"
        >
          Retry
        </button>
      </div>
    )
  }

  const renderEventCard = (event: EventSummary) => {
    const manageButtons = canEdit && (
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={isFetching}
          onClick={() => {
            startEdit(event)
          }}
          className="rounded-full border border-slate-700 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:opacity-60"
        >
          Edit
        </button>
        {event.status !== 'CANCELLED' && (
          <button
            type="button"
            disabled={isFetching}
            onClick={() => {
              setConfirmState({ type: 'cancel', event })
            }}
            className="rounded-full border border-amber-500/60 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-amber-200 transition hover:border-amber-400 hover:text-amber-100 disabled:opacity-60"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          disabled={isFetching}
          onClick={() => {
            setConfirmState({ type: 'delete', event })
          }}
          className="rounded-full border border-rose-500/60 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-rose-200 transition hover:border-rose-400 hover:text-rose-100 disabled:opacity-60"
        >
          Delete
        </button>
      </div>
    )

    return (
      <div
        key={event.id}
        className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/30"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">
              {event.name}
            </h3>
            <p className="text-sm text-slate-400">
              {event.track ?? 'Track TBD'}
            </p>
          </div>
          <span
            className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusTone(event.status)}`}
          >
            {event.status.toLowerCase()}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-slate-300">
          <span>{formatDate(event.startTime)}</span>
          {event.laps != null ? (
            <span>{event.laps.toString()} laps</span>
          ) : null}
          {event.distanceKm != null ? (
            <span>{event.distanceKm.toString()} km</span>
          ) : null}
        </div>
        {manageButtons ? <div className="mt-4">{manageButtons}</div> : null}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">Events</h2>
          <p className="text-sm text-slate-400">
            Manage race weekends and keep your roster informed.{' '}
            {isBypass
              ? 'These entries use mock events while bypass mode is active.'
              : null}
          </p>
        </div>
        {canEdit ? (
          <button
            type="button"
            onClick={() => {
              startCreate()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
          >
            Schedule event
          </button>
        ) : null}
      </div>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Upcoming
        </h3>
        <div className="mt-3 space-y-3">
          {upcoming.length === 0 ? (
            <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 text-sm text-slate-300">
              <p>No upcoming events on the calendar.</p>
              {canEdit ? (
                <button
                  type="button"
                  onClick={() => {
                    startCreate()
                  }}
                  className="mt-4 inline-flex items-center gap-2 rounded-full border border-sky-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-sky-200 transition hover:border-sky-200"
                >
                  Schedule one now
                </button>
              ) : null}
            </div>
          ) : (
            upcoming.map(renderEventCard)
          )}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Completed & cancelled
        </h3>
        <div className="mt-3 space-y-3">
          {completed.length === 0 ? (
            <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 text-sm text-slate-300">
              <p>
                Completed events will appear here once results start rolling in.
              </p>
            </div>
          ) : (
            completed.map(renderEventCard)
          )}
        </div>
      </section>

      <EventModal
        open={isCreateOpen}
        title="Schedule event"
        form={formState}
        onChange={setFormState}
        onClose={closeModals}
        onSubmit={handleCreate}
        isSubmitting={isSubmitting}
      />

      <EventModal
        open={editTarget != null}
        title="Edit event"
        form={formState}
        onChange={setFormState}
        onClose={closeModals}
        onSubmit={handleUpdate}
        isSubmitting={isSubmitting}
        isEdit
      />

      <ConfirmModal
        open={confirmState.type === 'cancel' && confirmState.event != null}
        title="Cancel event"
        description={`This will mark "${confirmState.event?.name ?? ''}" as cancelled. Drivers will see it moved to the completed list.`}
        confirmLabel="Cancel event"
        tone="neutral"
        onConfirm={() => {
          if (confirmState.event) {
            return handleCancelEvent(confirmState.event)
          }
          return Promise.resolve()
        }}
        onClose={() => {
          setConfirmState({ type: null, event: null })
        }}
        isConfirming={isConfirming}
      />

      <ConfirmModal
        open={confirmState.type === 'delete' && confirmState.event != null}
        title="Delete event"
        description={`This will permanently remove "${confirmState.event?.name ?? ''}".`}
        confirmLabel="Delete event"
        tone="danger"
        onConfirm={() => {
          if (confirmState.event) {
            return handleDeleteEvent(confirmState.event)
          }
          return Promise.resolve()
        }}
        onClose={() => {
          setConfirmState({ type: null, event: null })
        }}
        isConfirming={isConfirming}
      />
    </div>
  )
}
