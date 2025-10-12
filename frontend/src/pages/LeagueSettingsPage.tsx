import { Fragment, useEffect, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { updateLeagueGeneral } from '../api/leagues'
import { usePointsScheme, DEFAULT_POINTS_SCHEME } from '../hooks/usePointsScheme'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import type { LeagueRole } from '../types/auth'
import type { PointsSchemeEntry, UpdateLeagueGeneralRequest } from '../types/leagues'
import { useDiscordIntegration } from '../hooks/useDiscordIntegration'

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

function canEditGeneral(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN'
}

function canEditPoints(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN'
}

function formatTestTimestamp(value: string | null): string {
  if (!value) {
    return 'Never tested'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Never tested'
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date)
}
function sanitizeSlug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/--+/g, '-')
    .replace(/(^-|-$)+/g, '')
    .slice(0, 50)
}

interface GeneralErrors {
  name?: string
  slug?: string
}

interface PointsRow {
  position: number
  points: string
}

function toRows(entries: PointsSchemeEntry[]): PointsRow[] {
  return entries.map((entry) => ({
    position: entry.position,
    points: entry.points.toString(),
  }))
}

function arePointsEqual(rows: PointsRow[], entries: PointsSchemeEntry[]): boolean {
  if (rows.length !== entries.length) {
    return false
  }
  return rows.every((row, index) => {
    const targetPoints = entries[index]?.points
    return Number.parseInt(row.points, 10) === targetPoints
  })
}

export function LeagueSettingsPage(): ReactElement {
  const { slug = '' } = useParams<{ slug: string }>()
  const { overview, refetch, isBypass } = useOutletContext<LeagueOutletContext>()
  const { accessToken, isLoading: isAuthLoading, billingPlan } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const membership = useMemo(
    () => overview?.league.role ?? null,
    [overview?.league.role],
  )

  const canEditGeneralSettings = canEditGeneral(membership)
  const canEditPointsScheme = canEditPoints(membership)
  const canManageDiscord = canEditGeneral(membership)

  const plan = useMemo(() => (overview?.league.plan ?? billingPlan?.plan ?? 'FREE').toUpperCase(), [overview?.league.plan, billingPlan?.plan])
  const isProPlan = plan === 'PRO' || plan === 'ELITE'

  const [generalForm, setGeneralForm] = useState({
    name: overview?.league.name ?? '',
    slug: overview?.league.slug ?? slug,
  })
  const [generalErrors, setGeneralErrors] = useState<GeneralErrors>({})

  useEffect(() => {
    setGeneralForm({
      name: overview?.league.name ?? '',
      slug: overview?.league.slug ?? slug,
    })
  }, [overview?.league.name, overview?.league.slug, slug])

  const generalMutation = useMutation({
    mutationFn: async (payload: UpdateLeagueGeneralRequest) => {
      if (!accessToken) {
        throw new Error('Not authenticated')
      }
      return updateLeagueGeneral(accessToken, slug, payload)
    },
  })

  const { entries: pointsEntries, isLoading: isPointsLoading, error: pointsError, save, resetToDefault, isBypass: isPointsBypass } =
    usePointsScheme(slug)

  const {
    status: discordStatus,
    isLoading: isDiscordLoading,
    error: discordError,
    refresh: refreshDiscord,
    beginLink,
    disconnect,
    sendTest,
    isBypass: isDiscordBypass,
  } = useDiscordIntegration(slug)

  const [pointsRows, setPointsRows] = useState<PointsRow[]>(toRows(pointsEntries))
  const [pointsErrors, setPointsErrors] = useState<Record<number, string>>({})
  const [isPointsSaving, setIsPointsSaving] = useState(false)
  const [isLinkingDiscord, setIsLinkingDiscord] = useState(false)
  const [isTestingDiscord, setIsTestingDiscord] = useState(false)
  const [isDisconnectingDiscord, setIsDisconnectingDiscord] = useState(false)

  useEffect(() => {
    setPointsRows(toRows(pointsEntries))
  }, [pointsEntries])

  const isGeneralDirty =
    generalForm.name !== (overview?.league.name ?? '') || generalForm.slug !== (overview?.league.slug ?? slug)

  const isGeneralLoading = generalMutation.isPending || isAuthLoading

  const isPointsDirty = !arePointsEqual(pointsRows, pointsEntries)

  const handleGeneralSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!overview?.league) {
      return
    }

    const trimmedName = generalForm.name.trim()
    const sanitizedSlug = sanitizeSlug(generalForm.slug)

    const nextErrors: GeneralErrors = {}
    if (!trimmedName) {
      nextErrors.name = 'Name is required.'
    }
    if (!sanitizedSlug) {
      nextErrors.slug = 'Slug is required.'
    } else if (!SLUG_PATTERN.test(sanitizedSlug)) {
      nextErrors.slug = 'Use lowercase letters, numbers, and single hyphens.'
    }

    setGeneralErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    if (!isGeneralDirty) {
      showToast({
        title: 'No changes detected',
        description: 'Update the form before saving.',
        variant: 'info',
      })
      return
    }

    const payload: UpdateLeagueGeneralRequest = {
      name: trimmedName,
      slug: sanitizedSlug,
    }

    if (!accessToken) {
      setGeneralForm({
        name: trimmedName,
        slug: sanitizedSlug,
      })
      showToast({
        title: 'League updated (demo)',
        description: 'Bypass mode: changes are stored locally only.',
        variant: 'success',
      })
      if (sanitizedSlug !== slug) {
        void navigate(`/leagues/${sanitizedSlug}/settings`, { replace: true })
      }
      return
    }

    try {
      const updated = await generalMutation.mutateAsync(payload)

      queryClient.setQueryData(['league-overview', slug], (current: unknown) => {
        if (!current || typeof current !== 'object') {
          return current
        }
        const cast = current as LeagueOutletContext['overview']
        if (!cast) {
          return current
        }
        return {
          ...cast,
          league: {
            ...cast.league,
            name: updated.name,
            slug: updated.slug,
          },
        }
      })

      if (updated.slug !== slug) {
        queryClient.setQueryData(['league-overview', updated.slug], (current: unknown) => current)
      }

      await Promise.allSettled([
        queryClient.invalidateQueries({ queryKey: ['league-overview'] }),
        queryClient.invalidateQueries({ queryKey: ['league-drivers'] }),
        queryClient.invalidateQueries({ queryKey: ['league-events'] }),
        queryClient.invalidateQueries({ queryKey: ['leagues'] }),
      ])

      await refetch()

      showToast({
        title: 'Settings saved',
        description: 'League details have been updated.',
        variant: 'success',
      })

      if (updated.slug !== slug) {
        void navigate(`/leagues/${updated.slug}/settings`, { replace: true })
      } else {
        setGeneralForm({
          name: updated.name,
          slug: updated.slug,
        })
      }
    } catch (error) {
      if (error instanceof Error) {
        if (error.message.toLowerCase().includes('slug')) {
          setGeneralErrors((prev) => ({ ...prev, slug: error.message }))
        }
        showToast({
          title: 'Save failed',
          description: error.message,
          variant: 'error',
        })
      } else {
        showToast({
          title: 'Save failed',
          description: 'Unable to update league settings.',
          variant: 'error',
        })
      }
    }
  }

  const handlePointsInputChange = (position: number, value: string) => {
    setPointsRows((current) =>
      current.map((row) => (row.position === position ? { ...row, points: value } : row)),
    )
  }

  const handleResetPoints = () => {
    const reset = resetToDefault()
    setPointsRows(toRows(reset))
    setPointsErrors({})
    showToast({
      title: 'Points reset',
      description: 'Default F1 points scheme applied.',
      variant: 'info',
    })
  }

  const handleSavePoints = async () => {
    const nextErrors: Record<number, string> = {}
    const parsed: PointsSchemeEntry[] = []

    for (const row of pointsRows) {
      const trimmed = row.points.trim()
      if (!trimmed) {
        nextErrors[row.position] = 'Required'
        continue
      }
      const numeric = Number.parseInt(trimmed, 10)
      if (!Number.isFinite(numeric) || numeric < 0) {
        nextErrors[row.position] = 'Must be 0 or greater'
        continue
      }
      parsed.push({ position: row.position, points: numeric })
    }

    if (Object.keys(nextErrors).length > 0) {
      setPointsErrors(nextErrors)
      showToast({
        title: 'Check points values',
        description: 'Please fix validation errors before saving.',
        variant: 'error',
      })
      return
    }

    if (!isPointsDirty) {
      showToast({
        title: 'No changes detected',
        description: 'Adjust the points before saving.',
        variant: 'info',
      })
      return
    }

    setIsPointsSaving(true)
    try {
      const saved = await save(parsed)
      setPointsRows(toRows(saved))
      setPointsErrors({})
      showToast({
        title: 'Points saved',
        description: 'Updates will apply to future results.',
        variant: 'success',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to save points scheme.'
      showToast({
        title: 'Save failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsPointsSaving(false)
    }
  }

  const planLabel = overview?.league.plan ? overview.league.plan.toUpperCase() : 'FREE'
  const bypassBanner = isBypass ? 'Bypass mode active: changes are stored locally.' : undefined
  const discordBypassBanner = isDiscordBypass ? 'Discord demo mode: actions are simulated locally.' : undefined

  const discordStatusLabel = discordStatus.linked
    ? discordStatus.requiresReconnect
      ? 'Reconnect required'
      : 'Connected'
    : 'Not linked'

  const discordStatusTone = discordStatus.linked
    ? discordStatus.requiresReconnect
      ? 'border-amber-500/60 bg-amber-500/10 text-amber-100'
      : 'border-emerald-500/60 bg-emerald-500/10 text-emerald-100'
    : 'border-slate-700/70 bg-slate-900/60 text-slate-300'

  const disableLinkButton = !canManageDiscord || isLinkingDiscord || isDiscordLoading
  const disableUnlinkButton =
    !canManageDiscord ||
    !discordStatus.linked ||
    isDisconnectingDiscord ||
    isDiscordLoading
  const disableTestButton =
    !canManageDiscord ||
    !discordStatus.linked ||
    discordStatus.requiresReconnect ||
    !isProPlan ||
    isTestingDiscord ||
    isDiscordLoading

  const handleLinkDiscord = async () => {
    if (!canManageDiscord) {
      showToast({
        title: 'Insufficient permissions',
        description: 'Only owners or admins can manage the Discord integration.',
        variant: 'error',
      })
      return
    }

    setIsLinkingDiscord(true)
    try {
      const url = await beginLink()
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
      await refreshDiscord()
      await refetch()
      showToast({
        title: 'Link started',
        description: 'Complete the Discord authorization flow and return here when finished.',
        variant: 'info',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to start the Discord linking flow.'
      showToast({
        title: 'Link failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsLinkingDiscord(false)
    }
  }

  const handleDisconnectDiscord = async () => {
    if (!canManageDiscord) {
      showToast({
        title: 'Insufficient permissions',
        description: 'Only owners or admins can manage the Discord integration.',
        variant: 'error',
      })
      return
    }

    setIsDisconnectingDiscord(true)
    try {
      await disconnect()
      await refreshDiscord()
      await refetch()
      showToast({
        title: 'Discord unlinked',
        description: 'You can relink the integration at any time.',
        variant: 'success',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to unlink the Discord integration.'
      showToast({
        title: 'Unlink failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsDisconnectingDiscord(false)
    }
  }

  const handleTestDiscord = async () => {
    if (!canManageDiscord) {
      showToast({
        title: 'Insufficient permissions',
        description: 'Only owners or admins can manage the Discord integration.',
        variant: 'error',
      })
      return
    }
    if (!discordStatus.linked) {
      showToast({
        title: 'Integration required',
        description: 'Link Discord before sending a test announcement.',
        variant: 'error',
      })
      return
    }
    if (!isProPlan) {
      showToast({
        title: 'Upgrade to Pro',
        description: 'Discord announcements are available on the Pro plan.',
        variant: 'error',
      })
      return
    }

    setIsTestingDiscord(true)
    try {
      const message = await sendTest()
      await refreshDiscord()
      showToast({
        title: 'Test sent',
        description: message || 'Check your Discord server for the announcement.',
        variant: 'success',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to send test announcement.'
      showToast({
        title: 'Test failed',
        description: message,
        variant: 'error',
      })
    } finally {
      setIsTestingDiscord(false)
    }
  }

  return (
    <div className="space-y-6">
      <Fragment>
        {bypassBanner ? (
          <div className="rounded-3xl border border-sky-500/40 bg-sky-500/10 p-4 text-sm text-sky-100">
            {bypassBanner}
          </div>
        ) : null}
        {discordBypassBanner ? (
          <div className="rounded-3xl border border-blue-500/40 bg-blue-500/10 p-4 text-sm text-blue-100">
            {discordBypassBanner}
          </div>
        ) : null}
      </Fragment>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="space-y-2">
          <h2 className="text-xl font-semibold text-slate-100">General</h2>
          <p className="text-sm text-slate-400">
            Update how your league appears across GridBoss. Current plan:{' '}
            <span className="font-semibold text-slate-200">{planLabel}</span>
          </p>
        </header>

        <form
          className="mt-6 space-y-5"
          onSubmit={(event) => {
            void handleGeneralSubmit(event)
          }}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-slate-300">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">League name</span>
              <input
                value={generalForm.name}
                onChange={(event) => {
                  setGeneralForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }}
                disabled={!canEditGeneralSettings || isGeneralLoading}
                className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40 disabled:opacity-60"
              />
              {generalErrors.name ? <span className="text-xs text-rose-300">{generalErrors.name}</span> : null}
            </label>

            <label className="space-y-2 text-sm text-slate-300">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">League slug</span>
              <input
                value={generalForm.slug}
                onChange={(event) => {
                  const raw = event.target.value
                  setGeneralForm((current) => ({
                    ...current,
                    slug: sanitizeSlug(raw),
                  }))
                }}
                disabled={!canEditGeneralSettings || isGeneralLoading}
                className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40 disabled:opacity-60"
              />
              {generalErrors.slug ? <span className="text-xs text-rose-300">{generalErrors.slug}</span> : null}
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Slug changes update your league URL. Share the new link with your drivers after saving.
            </p>
            <button
              type="submit"
              disabled={!canEditGeneralSettings || isGeneralLoading}
              className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {isGeneralLoading ? (
                <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
              ) : null}
              Save changes
            </button>
          </div>

          {!canEditGeneralSettings ? (
            <p className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3 text-xs text-slate-400">
              You need owner or admin permissions to modify league details.
            </p>
          ) : null}
        </form>
      </section>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="space-y-2">
          <h2 className="text-xl font-semibold text-slate-100">Points</h2>
          <p className="text-sm text-slate-400">
            Configure base points per finishing position. These apply to future results submissions.
          </p>
        </header>

        {pointsError ? (
          <div className="mt-4 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
            <p className="font-semibold">Unable to load points scheme.</p>
            <p className="mt-1 text-rose-100/80">{pointsError.message}</p>
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-800 text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="px-4 py-3">Position</th>
                    <th className="px-4 py-3">Points</th>
                    <th className="px-4 py-3 text-right">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-100">
                  {pointsRows.map((row) => (
                    <tr key={row.position}>
                      <td className="px-4 py-3">
                        <span className="font-semibold">P{row.position}</span>
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="number"
                          min={0}
                          value={row.points}
                          onChange={(event) => {
                            handlePointsInputChange(row.position, event.target.value)
                          }}
                          disabled={!canEditPointsScheme || isPointsLoading || isPointsSaving}
                          className="w-24 rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40 disabled:opacity-60"
                        />
                        {pointsErrors[row.position] ? (
                          <p className="mt-1 text-xs text-rose-300">{pointsErrors[row.position]}</p>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-slate-500">
                        {DEFAULT_POINTS_SCHEME[row.position - 1]?.points === Number.parseInt(row.points, 10)
                          ? 'Default'
                          : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-500">
                Bonus and penalty points are added during results entry. Reset to default to restore the F1 template.
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleResetPoints}
                  disabled={!canEditPointsScheme || isPointsLoading || isPointsSaving}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Reset to default
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void handleSavePoints()
                  }}
                  disabled={!canEditPointsScheme || isPointsLoading || isPointsSaving}
                  className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                >
                  {isPointsSaving ? (
                    <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                  ) : null}
                  Save points
                </button>
              </div>
            </div>

            {!canEditPointsScheme ? (
              <p className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3 text-xs text-slate-400">
                Only league owners or admins can edit base points.
              </p>
            ) : null}

            {isPointsBypass ? (
              <p className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3 text-xs text-slate-400">
                Demo mode: point changes are stored locally until the API is available.
              </p>
            ) : null}
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 shadow shadow-slate-950/30">
        <header className="space-y-2">
          <h2 className="text-xl font-semibold text-slate-100">Discord integration</h2>
          <p className="text-sm text-slate-400">
            Link your Discord server to announce race results and key updates automatically.
          </p>
        </header>

        {isDiscordLoading ? (
          <div className="mt-6 space-y-3">
            {Array.from({ length: 2 }).map((_, index) => (
              <div
                key={index.toString()}
                className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4"
              >
                <div>
                  <div className="h-4 w-32 rounded bg-slate-800" />
                  <div className="mt-2 h-3 w-48 rounded bg-slate-800" />
                </div>
                <div className="h-8 w-24 rounded-full bg-slate-800" />
              </div>
            ))}
          </div>
        ) : discordError ? (
          <div className="mt-4 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
            <p className="font-semibold">We could not load the Discord integration.</p>
            <p className="mt-1 text-rose-100/80">{discordError.message}</p>
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1">
                  <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${discordStatusTone}`}>
                    {discordStatusLabel}
                  </span>
                  <div className="mt-3 space-y-1 text-sm text-slate-300">
                    <p>
                      <span className="text-slate-500">Guild:</span> {discordStatus.guildName || 'Not connected'}
                    </p>
                    <p>
                      <span className="text-slate-500">Channel:</span> {discordStatus.channelName || 'Not connected'}
                    </p>
                    <p className="text-xs text-slate-500">Last test: {formatTestTimestamp(discordStatus.lastTestedAt)}</p>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      void handleLinkDiscord()
                    }}
                    disabled={disableLinkButton}
                    className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                  >
                    {isLinkingDiscord ? (
                      <span className="inline-flex h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                    ) : null}
                    {discordStatus.linked ? 'Reconnect Discord' : 'Link Discord'}
                  </button>
                  {discordStatus.linked ? (
                    <button
                      type="button"
                      onClick={() => {
                        void handleDisconnectDiscord()
                      }}
                      disabled={disableUnlinkButton}
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isDisconnectingDiscord ? (
                        <span className="inline-flex h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                      ) : null}
                      Unlink
                    </button>
                  ) : null}
                </div>
              </div>
              {discordStatus.requiresReconnect ? (
                <p className="mt-3 rounded-2xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                  Permissions changed or the bot was removed. Reconnect to restore announcements.
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-slate-500">
                {isProPlan
                  ? 'Send a test message to verify the bot has the right channel permissions.'
                  : 'Upgrade to the Pro plan to enable Discord announcements and test messages.'}
              </div>
              <button
                type="button"
                onClick={() => {
                  void handleTestDiscord()
                }}
                disabled={disableTestButton}
                title={isProPlan ? undefined : 'Upgrade to the Pro plan to send test announcements.'}
                className="inline-flex items-center gap-2 rounded-full bg-slate-100/10 px-5 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-100/20 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
              >
                {isTestingDiscord ? (
                  <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" />
                ) : null}
                Send test announcement
              </button>
            </div>

            {!canManageDiscord ? (
              <p className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-3 text-xs text-slate-400">
                Only league owners or admins can manage the Discord integration.
              </p>
            ) : null}
          </div>
        )}
      </section>
    </div>
  )
}













