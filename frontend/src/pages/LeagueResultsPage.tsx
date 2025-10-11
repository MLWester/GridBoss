import { Fragment, useEffect, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import { useAuth } from '../hooks/useAuth'
import { useLeagueEvents } from '../hooks/useLeagueEvents'
import { useLeagueDrivers } from '../hooks/useLeagueDrivers'
import { useEventResults } from '../hooks/useEventResults'
import { useToast } from '../hooks/useToast'
import type { ResultEntrySummary, ResultStatus } from '../types/results'
import type { LeagueRole } from '../types/auth'
import type { DriverSummary } from '../types/drivers'

interface DragState {
  sourceIndex: number
  destinationIndex: number
}

function canManageResults(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN' || role === 'STEWARD'
}

function classNames(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

const driverStatusOptions: ResultStatus[] = ['FINISHED', 'DNF', 'DNS', 'DSQ']

function formatDriverName(driver: DriverSummary): string {
  return driver.displayName
}

function buildDriverLookup(drivers: DriverSummary[]): Partial<Record<string, DriverSummary>> {
  const map: Partial<Record<string, DriverSummary>> = {}
  for (const driver of drivers) {
    map[driver.id] = driver
  }
  return map
}

export function LeagueResultsPage(): ReactElement {
  const { slug = '' } = useParams<{ slug: string }>()
  const { overview } = useOutletContext<LeagueOutletContext>()
  const { memberships, isLoading: isAuthLoading } = useAuth()
  const { showToast } = useToast()

  const {
    events,
    isLoading: isEventsLoading,
    error: eventsError,
    isBypass: isEventsBypass,
  } = useLeagueEvents(slug)
  const {
    drivers,
    isLoading: isDriversLoading,
    error: driversError,
    isBypass: isDriversBypass,
  } = useLeagueDrivers(slug)

  const membership = useMemo(
    () => memberships.find((item) => item.league_slug === slug) ?? null,
    [memberships, slug],
  )

  const role: LeagueRole | null = membership?.role ?? overview?.league.role ?? null
  const canEdit = canManageResults(role)

  const orderedEvents = useMemo(() => {
    const sorted = [...events]
    sorted.sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())
    return sorted
  }, [events])

  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)

  useEffect(() => {
    if (orderedEvents.length === 0) {
      setSelectedEventId(null)
      return
    }
    if (selectedEventId !== null && orderedEvents.some((event) => event.id === selectedEventId)) {
      return
    }
    setSelectedEventId(orderedEvents[0]?.id ?? null)
  }, [orderedEvents, selectedEventId])

  const selectedEvent = orderedEvents.find((event) => event.id === selectedEventId) || null

  const driverLookup = useMemo(() => buildDriverLookup(drivers), [drivers])

  const {
    entries,
    isLoading: isResultsLoading,
    error: resultsError,
    setEntries,
    submit,
    isBypass: isResultsBypass,
  } = useEventResults(selectedEventId, drivers)

  const [draftEntries, setDraftEntries] = useState<ResultEntrySummary[]>(entries)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)
  const [dragState, setDragState] = useState<DragState | null>(null)

  useEffect(() => {
    setDraftEntries(entries)
  }, [entries])

  const handleReorder = (sourceIndex: number, destinationIndex: number) => {
    if (sourceIndex === destinationIndex || sourceIndex < 0 || destinationIndex < 0) {
      return
    }
    setDraftEntries((current) => {
      const clone = [...current]
      const [item] = clone.splice(sourceIndex, 1)
      clone.splice(destinationIndex, 0, item)
      return clone.map((entry, index) => ({ ...entry, finishPosition: index + 1 }))
    })
  }

  const handleSubmit = async () => {
    if (!selectedEventId) {
      showToast({
        title: 'Select an event',
        description: 'Choose an event before submitting results.',
        variant: 'error',
      })
      return
    }

    const missingDriver = draftEntries.find((entry) => !driverLookup[entry.driverId])
    if (missingDriver) {
      showToast({
        title: 'Unknown driver',
        description: 'One or more drivers are missing from the roster. Refresh the page and try again.',
        variant: 'error',
      })
      return
    }

    setIsSubmitting(true)
    setPlanError(null)
    try {
      await submit(draftEntries)
      setEntries(draftEntries.map((entry, index) => ({ ...entry, finishPosition: index + 1 })))
      showToast({
        title: 'Results submitted',
        description: 'Standings will update once the background job completes.',
        variant: 'success',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to submit results'
      if (message.toLowerCase().includes('plan')) {
        setPlanError(message)
      }
      showToast({
        title: 'Submission failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleStatusChange = (index: number, status: ResultStatus) => {
    setDraftEntries((current) =>
      current.map((entry, idx) => (idx === index ? { ...entry, status } : entry)),
    )
  }

  const handleInputChange = (index: number, field: 'bonusPoints' | 'penaltyPoints', value: string) => {
    const numeric = value === '' ? 0 : Number.parseInt(value, 10) || 0
    setDraftEntries((current) =>
      current.map((entry, idx) => (idx === index ? { ...entry, [field]: numeric } : entry)),
    )
  }

  const handleDragStart = (index: number) => {
    setDragState({ sourceIndex: index, destinationIndex: index })
  }

  const handleDragEnter = (index: number) => {
    setDragState((current) => {
      if (!current) return null
      return { ...current, destinationIndex: index }
    })
  }

  const handleDragEnd = () => {
    if (dragState && dragState.sourceIndex !== dragState.destinationIndex) {
      handleReorder(dragState.sourceIndex, dragState.destinationIndex)
    }
    setDragState(null)
  }

  if (isAuthLoading || isEventsLoading || isDriversLoading || isResultsLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index.toString()}
            className="grid grid-cols-[auto_1fr_1fr_1fr] items-center gap-3 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-4"
          >
            <div className="h-8 w-8 rounded-full bg-slate-800" />
            <div className="h-4 w-full rounded bg-slate-800" />
            <div className="h-4 w-3/4 rounded bg-slate-800" />
            <div className="h-8 w-20 rounded-full bg-slate-800" />
          </div>
        ))}
      </div>
    )
  }

  if (eventsError || driversError || resultsError) {
    const message =
      eventsError?.message ?? driversError?.message ?? resultsError?.message ?? 'Unknown error loading results'
    return (
      <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-100">
        <p className="font-semibold">We could not load everything needed for results entry.</p>
        <p className="mt-1 text-rose-100/80">{message}</p>
      </div>
    )
  }

  if (!selectedEvent) {
    return (
      <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-300">
        <p>No events available yet. Schedule an event first before entering results.</p>
      </div>
    )
  }

  const infoBanner =
    isEventsBypass || isDriversBypass || isResultsBypass
      ? 'Bypass mode: results are stored locally and reset on refresh.'
      : 'After submitting, standings refresh runs in the background. If they look stale, give it a few seconds.'

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-100">Event results</h2>
            <p className="text-sm text-slate-400">{infoBanner}</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-400" htmlFor="event-select">
              Event
            </label>
            <select
              id="event-select"
              value={selectedEventId ?? ''}
              onChange={(event) => {
                setSelectedEventId(event.target.value || null)
              }}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
            >
              {orderedEvents.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {planError ? (
        <div className="rounded-3xl border border-amber-500/50 bg-amber-500/10 p-4 text-sm text-amber-100">
          <p className="font-semibold">Plan limitation</p>
          <p className="mt-1 text-amber-100/90">{planError}</p>
        </div>
      ) : null}

      <div className="space-y-3">
        {draftEntries.map((entry, index) => {
          const driver = driverLookup[entry.driverId]
          return (
            <div
              key={entry.driverId}
              draggable={canEdit}
              onDragStart={() => {
                handleDragStart(index)
              }}
              onDragEnter={() => {
                if (dragState) {
                  handleDragEnter(index)
                }
              }}
              onDragEnd={() => {
                handleDragEnd()
              }}
              onDragOver={(event) => {
                if (canEdit) {
                  event.preventDefault()
                }
              }}
              className={classNames(
                'grid grid-cols-[auto_1.2fr_1.2fr_1.2fr_1fr_1fr] items-center gap-3 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-4 shadow shadow-slate-950/30',
                dragState?.destinationIndex === index ? 'border-sky-500/60' : '',
              )}
            >
              <div className="flex flex-col items-center justify-center">
                <span className="text-sm font-semibold text-slate-200">{index + 1}</span>
                {canEdit ? (
                  <div className="mt-2 flex flex-col gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        handleReorder(index, Math.max(0, index - 1))
                      }}
                      className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-700 text-[10px] font-semibold uppercase text-slate-300 transition hover:border-sky-500 hover:text-sky-100"
                    >
                      Up
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        handleReorder(index, Math.min(draftEntries.length - 1, index + 1))
                      }}
                      className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-700 text-[10px] font-semibold uppercase text-slate-300 transition hover:border-sky-500 hover:text-sky-100"
                    >
                      Down
                    </button>
                  </div>
                ) : null}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-100">
                  {driver ? formatDriverName(driver) : 'Unknown driver'}
                </p>
                <p className="text-xs text-slate-500">{driver?.teamName ?? 'Unassigned'}</p>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Status</label>
                <select
                  value={entry.status}
                  disabled={!canEdit}
                  onChange={(event) => {
                    handleStatusChange(index, event.target.value as ResultStatus)
                  }}
                  className="mt-1 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40 disabled:opacity-60"
                >
                  {driverStatusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status.toLowerCase()}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Bonus</label>
                <input
                  type="number"
                  inputMode="numeric"
                  value={entry.bonusPoints}
                  disabled={!canEdit}
                  onChange={(event) => {
                    handleInputChange(index, 'bonusPoints', event.target.value)
                  }}
                  className="mt-1 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40 disabled:opacity-60"
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Penalty</label>
                <input
                  type="number"
                  inputMode="numeric"
                  value={entry.penaltyPoints}
                  disabled={!canEdit}
                  onChange={(event) => {
                    handleInputChange(index, 'penaltyPoints', event.target.value)
                  }}
                  className="mt-1 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40 disabled:opacity-60"
                />
              </div>
              <div className="text-xs text-slate-500">
                <p>Base points calculated server-side.</p>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          Need to tweak? Reorder drivers, adjust modifiers, and submit again. Standings recompute automatically.
        </p>
        {canEdit ? (
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => {
              void handleSubmit()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isSubmitting ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
            ) : null}
            Submit results
          </button>
        ) : (
          <span className="text-xs text-slate-500">Read-only access</span>
        )}
      </div>

      <Fragment>
        <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-4 text-xs text-slate-400">
          <p>
            Worker queue running slow? Refresh after a few seconds. If standings still look stale, the background job is
            catching up.
          </p>
        </div>
      </Fragment>
    </div>
  )
}
