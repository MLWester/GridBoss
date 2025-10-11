import { Fragment, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import { useAuth } from '../hooks/useAuth'
import { useLeagueDrivers } from '../hooks/useLeagueDrivers'
import { useToast } from '../hooks/useToast'
import type { LeagueRole } from '../types/auth'
import type { DriverSummary } from '../types/drivers'
import type { TeamSummary } from '../types/teams'

interface TeamFormState {
  name: string
  driverIds: string[]
}

function canManageTeams(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN'
}

function LoadingSkeleton(): ReactElement {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index.toString()}
          className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/40"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="h-5 w-32 rounded bg-slate-800" />
              <div className="mt-2 h-4 w-20 rounded bg-slate-800" />
            </div>
            <div className="h-6 w-16 rounded-full bg-slate-800" />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {Array.from({ length: 4 }).map((__, chip) => (
              <div key={chip.toString()} className="h-7 w-20 rounded-full bg-slate-800" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

interface TeamModalProps {
  open: boolean
  title: string
  form: TeamFormState
  onChange: (state: TeamFormState) => void
  drivers: DriverSummary[]
  onClose: () => void
  onSubmit: () => Promise<void>
  isSubmitting: boolean
}

function TeamModal({
  open,
  title,
  form,
  onChange,
  drivers,
  onClose,
  onSubmit,
  isSubmitting,
}: TeamModalProps): ReactElement | null {
  if (!open) {
    return null
  }

  const toggleDriver = (driverId: string) => {
    onChange({
      ...form,
      driverIds: form.driverIds.includes(driverId)
        ? form.driverIds.filter((id) => id !== driverId)
        : [...form.driverIds, driverId],
    })
  }

  const assignedLookup = new Set(form.driverIds)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/95 p-8 shadow-xl shadow-slate-950/60">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-slate-100">{title}</h2>
            <p className="mt-1 text-sm text-slate-400">
              Give your team a name and pick the drivers that should belong to it. Drivers can only belong to one team
              at a time.
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

        <div className="mt-6 space-y-5">
          <div className="space-y-2">
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400" htmlFor="team-name">
              Team name
            </label>
            <input
              id="team-name"
              value={form.name}
              onChange={(event) => {
                onChange({ ...form, name: event.target.value })
              }}
              placeholder="Aurora GP"
              className="w-full rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
            />
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Drivers</p>
            <div className="mt-3 grid gap-2">
              {drivers.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No drivers available yet. Add drivers first to build out teams.
                </p>
              ) : (
                drivers.map((driver) => {
                  const isSelected = assignedLookup.has(driver.id)
                  return (
                    <label
                      key={driver.id}
                      className={`flex items-center justify-between gap-3 rounded-2xl border px-4 py-2 text-sm transition ${
                        isSelected
                          ? 'border-sky-500/60 bg-sky-500/10 text-sky-100'
                          : 'border-slate-800 bg-slate-900/40 text-slate-100 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {
                            toggleDriver(driver.id)
                          }}
                          className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-sky-500 focus:ring-sky-500/40"
                        />
                        <span>{driver.displayName}</span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {driver.teamId && driver.teamName ? `Currently: ${driver.teamName}` : 'Unassigned'}
                      </span>
                    </label>
                  )
                })
              )}
            </div>
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
            disabled={isSubmitting || !form.name.trim()}
            onClick={() => {
              void onSubmit()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isSubmitting ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
            ) : null}
            Save team
          </button>
        </div>
      </div>
    </div>
  )
}

interface DeleteModalProps {
  open: boolean
  team: TeamSummary | null
  onConfirm: () => Promise<void>
  onClose: () => void
  isDeleting: boolean
}

function DeleteModal({ open, team, onConfirm, onClose, isDeleting }: DeleteModalProps): ReactElement | null {
  if (!open || !team) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-950/95 p-8 text-slate-100 shadow-xl shadow-slate-950/60">
        <h3 className="text-xl font-semibold">Delete team</h3>
        <p className="mt-3 text-sm text-slate-300">
          Removing <span className="font-semibold">{team.name}</span> will unassign its drivers. You can reassign them
          later from the teams or drivers tab.
        </p>
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
            disabled={isDeleting}
            onClick={() => {
              void onConfirm()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-rose-500 px-5 py-2 text-sm font-semibold text-rose-50 transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isDeleting ? (
              <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-rose-200 border-t-rose-700" />
            ) : null}
            Delete team
          </button>
        </div>
      </div>
    </div>
  )
}

export function LeagueTeamsPage(): ReactElement {
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
    createTeam,
    updateTeam,
    deleteTeam,
    isBypass,
  } = useLeagueDrivers(slug)

  const membership = useMemo(
    () => memberships.find((item) => item.league_slug === slug) ?? null,
    [memberships, slug],
  )

  const role: LeagueRole | null = membership?.role ?? overview?.league.role ?? null
  const canEdit = canManageTeams(role)

  const [isCreating, setIsCreating] = useState(false)
  const [editTarget, setEditTarget] = useState<TeamSummary | null>(null)
  const [formState, setFormState] = useState<TeamFormState>({ name: '', driverIds: [] })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<TeamSummary | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const startCreate = () => {
    setFormState({ name: '', driverIds: [] })
    setIsCreating(true)
  }

  const startEdit = (team: TeamSummary) => {
    setEditTarget(team)
    setFormState({ name: team.name, driverIds: [...team.driverIds] })
  }

  const closeModals = () => {
    setIsCreating(false)
    setEditTarget(null)
    setFormState({ name: '', driverIds: [] })
  }

  const availableDrivers = useMemo(
    () => drivers.slice().sort((a, b) => a.displayName.localeCompare(b.displayName)),
    [drivers],
  )

  const handleCreate = async () => {
    setIsSubmitting(true)
    try {
      const trimmedName = formState.name.trim()
      const team = await createTeam({ name: trimmedName, driverIds: formState.driverIds })
      showToast({
        title: 'Team created',
        description: `${team.name} is ready. Drivers assigned have been moved from their previous teams.`,
        variant: 'success',
      })
      closeModals()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create team'
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
      const trimmedName = formState.name.trim()
      const team = await updateTeam(editTarget.id, { name: trimmedName, driverIds: formState.driverIds })
      showToast({
        title: 'Team updated',
        description: `${team.name} has been refreshed.`,
        variant: 'success',
      })
      closeModals()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update team'
      showToast({
        title: 'Update failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) {
      return
    }
    setIsDeleting(true)
    try {
      await deleteTeam(deleteTarget.id)
      showToast({
        title: 'Team deleted',
        description: `${deleteTarget.name} was removed and its drivers are now unassigned.`,
        variant: 'success',
      })
      setDeleteTarget(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete team'
      showToast({
        title: 'Delete failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading || isAuthLoading) {
    return <LoadingSkeleton />
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-100">
        <p className="font-semibold">We could not load the teams.</p>
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

  const renderDriverBadges = (team: TeamSummary) => {
    if (team.driverIds.length === 0) {
      return <p className="text-sm text-slate-500">No drivers assigned yet.</p>
    }

    return (
      <div className="flex flex-wrap gap-2">
        {team.driverIds.map((driverId) => {
          const driver = drivers.find((item) => item.id === driverId)
          return (
            <span
              key={driverId}
              className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-xs text-slate-200"
            >
              <span className="inline-block h-2 w-2 rounded-full bg-sky-400" />
              {driver?.displayName ?? 'Driver removed'}
            </span>
          )
        })}
      </div>
    )
  }

  return (
    <Fragment>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">Teams</h2>
          <p className="text-sm text-slate-400">
            Organise your roster into teams. {isBypass ? 'This view is populated with mock data while bypass mode is active.' : null}
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
            New team
          </button>
        ) : null}
      </div>

      {teams.length === 0 ? (
        <div className="mt-6 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-300">
          <p className="text-slate-100">No teams yet</p>
          <p className="mt-2 text-slate-400">
            Create a team to start grouping drivers. You can reassign drivers at any time, and upcoming PBIs will add
            more team analytics.
          </p>
          {canEdit ? (
            <button
              type="button"
              onClick={() => {
                startCreate()
              }}
              className="mt-4 inline-flex items-center gap-2 rounded-full border border-sky-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-sky-200 transition hover:border-sky-200"
            >
              Create your first team
            </button>
          ) : (
            <p className="mt-4 text-xs text-slate-500">You need elevated permissions to manage teams.</p>
          )}
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {teams.map((team) => (
            <div
              key={team.id}
              className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/40"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold text-slate-100">{team.name}</p>
                  <p className="text-xs text-slate-500">
                    {team.driverCount.toString()} {team.driverCount === 1 ? 'driver' : 'drivers'}
                  </p>
                </div>
                {canEdit ? (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={isFetching}
                      onClick={() => {
                        startEdit(team)
                      }}
                      className="rounded-full border border-slate-700 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:opacity-60"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      disabled={isFetching}
                      onClick={() => {
                        setDeleteTarget(team)
                      }}
                      className="rounded-full border border-rose-500/60 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-rose-200 transition hover:border-rose-400 hover:text-rose-100 disabled:opacity-60"
                    >
                      Delete
                    </button>
                  </div>
                ) : (
                  <span className="text-xs text-slate-500">Read only</span>
                )}
              </div>

              <div className="mt-4">{renderDriverBadges(team)}</div>
            </div>
          ))}
        </div>
      )}

      <TeamModal
        open={isCreating}
        title="Create team"
        form={formState}
        onChange={setFormState}
        drivers={availableDrivers}
        onClose={closeModals}
        onSubmit={handleCreate}
        isSubmitting={isSubmitting}
      />

      <TeamModal
        open={editTarget != null}
        title="Edit team"
        form={formState}
        onChange={setFormState}
        drivers={availableDrivers}
        onClose={closeModals}
        onSubmit={handleUpdate}
        isSubmitting={isSubmitting}
      />

      <DeleteModal
        open={deleteTarget != null}
        team={deleteTarget}
        onConfirm={handleDelete}
        onClose={() => {
          setDeleteTarget(null)
        }}
        isDeleting={isDeleting}
      />
    </Fragment>
  )
}
