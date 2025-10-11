import { Fragment, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import { useAuth } from '../hooks/useAuth'
import { useLeagueDrivers } from '../hooks/useLeagueDrivers'
import { useToast } from '../hooks/useToast'
import type { DriverSummary, BulkDriverInput } from '../types/drivers'
import type { TeamSummary } from '../types/teams'
import type { LeagueRole } from '../types/auth'

interface EditDraft {
  displayName: string
  teamId: string | null
}

type ParsedRowStatus = 'ready' | 'conflict' | 'invalid'

interface ParsedDriverRow {
  line: string
  displayName: string
  teamId: string | null
  teamName: string | null
  status: ParsedRowStatus
  message: string | null
}

function LoadingSkeleton(): ReactElement {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          key={index}
          className="grid grid-cols-[2fr_2fr_1fr_1fr] items-center gap-3 rounded-2xl border border-slate-800/70 bg-slate-900/40 p-4"
        >
          <div className="h-5 w-40 rounded bg-slate-800" />
          <div className="h-5 w-32 rounded bg-slate-800" />
          <div className="h-5 w-24 rounded bg-slate-800" />
          <div className="flex justify-end gap-2">
            <div className="h-6 w-16 rounded-full bg-slate-800" />
          </div>
        </div>
      ))}
    </div>
  )
}

function LinkedBadge({ driver }: { driver: DriverSummary }): ReactElement {
  if (!driver.linkedUser) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-slate-700/60 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        Offline
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/50 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-200">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" /> Linked
    </span>
  )
}

function parseBulkInput(
  value: string,
  drivers: DriverSummary[],
  teams: TeamSummary[],
): ParsedDriverRow[] {
  const lines = value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  const existingNames = new Set(drivers.map((driver) => driver.displayName.toLowerCase()))
  const seenNames = new Set<string>()

  return lines.map((line) => {
    const [namePart, teamPart] = line.split(/\t|,/).map((part) => part.trim())
    const displayName = namePart

    if (!displayName) {
      return {
        line,
        displayName: '',
        teamId: null,
        teamName: null,
        status: 'invalid' as ParsedRowStatus,
        message: 'Driver name is required',
      }
    }

    const nameKey = displayName.toLowerCase()
    if (seenNames.has(nameKey)) {
      return {
        line,
        displayName,
        teamId: null,
        teamName: null,
        status: 'conflict' as ParsedRowStatus,
        message: 'Duplicate name in paste',
      }
    }

    if (existingNames.has(nameKey)) {
      return {
        line,
        displayName,
        teamId: null,
        teamName: null,
        status: 'conflict' as ParsedRowStatus,
        message: 'Already exists in roster',
      }
    }

    seenNames.add(nameKey)

    if (!teamPart) {
      return {
        line,
        displayName,
        teamId: null,
        teamName: null,
        status: 'ready' as ParsedRowStatus,
        message: null,
      }
    }

    const targetTeam = teams.find((team) => team.name.toLowerCase() === teamPart.toLowerCase())
    if (!targetTeam) {
      return {
        line,
        displayName,
        teamId: null,
        teamName: null,
        status: 'conflict' as ParsedRowStatus,
        message: `Team "${teamPart}" not found`,
      }
    }

    return {
      line,
      displayName,
      teamId: targetTeam.id,
      teamName: targetTeam.name,
      status: 'ready' as ParsedRowStatus,
      message: null,
    }
  })
}

interface BulkDriversModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (items: BulkDriverInput[]) => Promise<void>
  drivers: DriverSummary[]
  teams: TeamSummary[]
}

function BulkDriversModal({
  open,
  onClose,
  onSubmit,
  drivers,
  teams,
}: BulkDriversModalProps): ReactElement | null {
  const [input, setInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const rows = useMemo(() => parseBulkInput(input, drivers, teams), [input, drivers, teams])

  const readyRows = rows.filter((row) => row.status === 'ready')
  const hasConflicts = rows.some((row) => row.status !== 'ready')

  const handleSubmit = async () => {
    if (readyRows.length === 0) {
      return
    }
    setIsSubmitting(true)
    try {
      const payload: BulkDriverInput[] = readyRows.map((row) => ({
        display_name: row.displayName,
        team_id: row.teamId,
      }))
      await onSubmit(payload)
      setInput('')
      onClose()
    } catch {
      // Error feedback handled by parent toast; keep modal open.
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/95 p-8 shadow-xl shadow-slate-950/60">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-100">Bulk add drivers</h2>
            <p className="mt-1 text-sm text-slate-400">
              Paste a list of names, optionally followed by a comma and team. Existing drivers and duplicates will be
              flagged.
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

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Driver list
            </label>
            <textarea
              value={input}
              onChange={(event) => {
                setInput(event.target.value)
              }}
              placeholder={'Jamie Chen, Aurora GP\nAlex Rivera'}
              className="h-48 w-full rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
            />
            <p className="text-xs text-slate-500">
              Format: `Driver Name, Team Name`. Team is optional. Use tab or comma separators. Existing team names:{' '}
              {teams.length > 0 ? teams.map((team) => team.name).join(', ') : 'none yet'}.
            </p>
          </div>

          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Preview</p>
            <div className="max-h-64 overflow-y-auto rounded-2xl border border-slate-800">
              {rows.length === 0 ? (
                <div className="p-4 text-sm text-slate-500">Paste drivers to see the preview.</div>
              ) : (
                <ul className="divide-y divide-slate-800 text-sm">
                  {rows.map((row, index) => (
                    <li
                      key={`${row.line}-${index.toString()}`}
                      className={`flex flex-col gap-1 p-3 ${
                        row.status === 'ready'
                          ? ''
                          : row.status === 'conflict'
                            ? 'bg-rose-500/5'
                            : 'bg-amber-500/5'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 text-slate-100">
                        <span>{row.displayName || <span className="text-slate-500">Unnamed driver</span>}</span>
                        <span className="text-xs uppercase tracking-wide text-slate-400">
                          {row.teamName ?? 'Unassigned'}
                        </span>
                      </div>
                      {row.status !== 'ready' && row.message ? (
                        <p className="text-xs text-rose-300">{row.message}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {rows.length > 0 ? (
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>{readyRows.length} ready</span>
                {hasConflicts ? <span className="text-rose-300">Resolve conflicts to continue</span> : null}
              </div>
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
            disabled={readyRows.length === 0 || isSubmitting}
            onClick={() => {
              void handleSubmit()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isSubmitting ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-950" />
            ) : null}
            Add drivers
          </button>
        </div>
      </div>
    </div>
  )
}

function canManageDrivers(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN'
}

export function LeagueDriversPage(): ReactElement {
  const { slug = '' } = useParams<{ slug: string }>()
  const { overview } = useOutletContext<LeagueOutletContext>()
  const { memberships, isLoading: isAuthLoading } = useAuth()
  const { showToast } = useToast()
  const {
    drivers,
    teams,
    isLoading,
    isFetching,
    error,
    refetch,
    updateDriver,
    bulkCreateDrivers,
    isBypass,
  } = useLeagueDrivers(slug)

  const membership = useMemo(
    () => memberships.find((item) => item.league_slug === slug) ?? null,
    [memberships, slug],
  )

  const role: LeagueRole | null = membership?.role ?? overview?.league.role ?? null
  const canEdit = canManageDrivers(role)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<EditDraft>({ displayName: '', teamId: null })
  const [isSaving, setIsSaving] = useState(false)
  const [isBulkOpen, setIsBulkOpen] = useState(false)

  const startEdit = (driver: DriverSummary) => {
    setEditingId(driver.id)
    setEditDraft({
      displayName: driver.displayName,
      teamId: driver.teamId,
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditDraft({ displayName: '', teamId: null })
  }

  const handleSave = async (driver: DriverSummary) => {
    const trimmedName = editDraft.displayName.trim()
    if (!trimmedName) {
      showToast({
        title: 'Driver name required',
        description: 'Please provide a display name before saving.',
        variant: 'error',
      })
      return
    }
    const hasChanges = trimmedName !== driver.displayName || editDraft.teamId !== driver.teamId
    if (!hasChanges) {
      cancelEdit()
      return
    }

    setIsSaving(true)
    try {
      await updateDriver(driver.id, {
        display_name: trimmedName,
        team_id: editDraft.teamId ?? null,
      })
      showToast({
        title: 'Driver updated',
        description: `${trimmedName} has been updated.`,
        variant: 'success',
      })
      cancelEdit()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to update driver'
      showToast({
        title: 'Update failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleBulkSubmit = async (items: BulkDriverInput[]) => {
    try {
      await bulkCreateDrivers(items)
      const addedCount = items.length
      const noun = addedCount === 1 ? 'driver' : 'drivers'
      showToast({
        title: 'Drivers added',
        description: `${addedCount.toString()} ${noun} added to the roster.`,
        variant: 'success',
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to add drivers'
      showToast({
        title: 'Bulk import failed',
        description: message,
        variant: 'error',
      })
    }
  }

  if (isLoading || isAuthLoading) {
    return <LoadingSkeleton />
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-100">
        <p className="font-semibold">We could not load the drivers roster.</p>
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

  return (
    <Fragment>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">Drivers roster</h2>
          <p className="text-sm text-slate-400">
            Manage driver display names and team assignments. {isBypass ? 'This is mock data for bypass mode.' : null}
          </p>
        </div>
        {canEdit ? (
          <button
            type="button"
            onClick={() => {
              setIsBulkOpen(true)
            }}
            className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
          >
            Bulk import
          </button>
        ) : null}
      </div>

      {drivers.length === 0 ? (
        <div className="mt-6 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-300">
          <p className="text-slate-100">No drivers yet</p>
          <p className="mt-2 text-slate-400">
            Bulk import your roster or use upcoming PBIs to invite drivers by email and Discord.
          </p>
          {canEdit ? (
            <button
              type="button"
              onClick={() => {
                setIsBulkOpen(true)
              }}
              className="mt-4 inline-flex items-center gap-2 rounded-full border border-sky-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-sky-200 transition hover:border-sky-200"
            >
              Launch bulk paste
            </button>
          ) : null}
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {drivers.map((driver) => {
            const isEditing = editingId === driver.id
            const showActions = canEdit
            return (
              <div
                key={driver.id}
                className="grid grid-cols-1 gap-4 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/30 md:grid-cols-[2fr,2fr,1fr,auto]"
              >
                <div className="space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Display name</p>
                  {isEditing ? (
                    <input
                      value={editDraft.displayName}
                      onChange={(event) => {
                        setEditDraft((current) => ({ ...current, displayName: event.target.value }))
                      }}
                      className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
                    />
                  ) : (
                    <p className="text-sm font-semibold text-slate-100">{driver.displayName}</p>
                  )}
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Team</p>
                  {isEditing ? (
                    <select
                      value={editDraft.teamId ?? ''}
                      onChange={(event) => {
                        setEditDraft((current) => ({
                          ...current,
                          teamId: event.target.value ? event.target.value : null,
                        }))
                      }}
                      className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
                    >
                      <option value="">Unassigned</option>
                      {teams.map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-sm text-slate-300">{driver.teamName ?? 'Unassigned'}</p>
                  )}
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Link</p>
                  <LinkedBadge driver={driver} />
                  {driver.userName ? (
                    <p className="text-xs text-slate-500">Discord: {driver.userName}</p>
                  ) : null}
                </div>

                {showActions ? (
                  <div className="flex items-end justify-end gap-2">
                    {isEditing ? (
                      <Fragment>
                        <button
                          type="button"
                          onClick={() => {
                            cancelEdit()
                          }}
                          disabled={isSaving}
                          className="rounded-full border border-slate-700 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:opacity-60"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          disabled={isSaving}
                          onClick={() => {
                            void handleSave(driver)
                          }}
                          className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                        >
                          {isSaving ? (
                            <span className="inline-flex h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                          ) : null}
                          Save
                        </button>
                      </Fragment>
                    ) : (
                      <button
                        type="button"
                        disabled={isFetching}
                        onClick={() => {
                          startEdit(driver)
                        }}
                        className="rounded-full border border-slate-700 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:opacity-60"
                      >
                        Edit
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="flex items-end justify-end">
                    <span className="text-xs text-slate-500">Read only</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <BulkDriversModal
        open={isBulkOpen}
        onClose={() => {
          setIsBulkOpen(false)
        }}
        onSubmit={handleBulkSubmit}
        drivers={drivers}
        teams={teams}
      />
    </Fragment>
  )
}
