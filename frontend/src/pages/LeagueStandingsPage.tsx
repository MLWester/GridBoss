import { useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import { useAuth } from '../hooks/useAuth'
import { useLeagueStandings } from '../hooks/useLeagueStandings'
import { useToast } from '../hooks/useToast'
import type { LeagueRole } from '../types/auth'

function canManageStandings(role: LeagueRole | null): boolean {
  return role === 'OWNER' || role === 'ADMIN'
}

function classNames(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

function podiumTone(position: number): string | null {
  if (position === 1) return 'bg-amber-500/15 border-amber-400/40'
  if (position === 2) return 'bg-slate-500/15 border-slate-300/30'
  if (position === 3) return 'bg-amber-800/15 border-amber-700/40'
  return null
}

function formatBestFinish(value: number | null): string {
  if (value == null) {
    return 'n/a'
  }
  return value.toString()
}

function computeSharesUrl(slug: string, seasonId: string | null): string {
  const url = new URL(window.location.href)
  url.pathname = `/leagues/${slug}/standings`
  if (seasonId) {
    url.searchParams.set('seasonId', seasonId)
  }
  return url.toString()
}

function useShareLink(): (link: string) => Promise<boolean> {
  return async (link: string) => {
    try {
      if (typeof navigator.share === 'function') {
        await navigator.share({ url: link, title: 'GridBoss Standings' })
        return true
      }
      if (
        'clipboard' in navigator &&
        typeof navigator.clipboard.writeText === 'function'
      ) {
        await navigator.clipboard.writeText(link)
        return true
      }
    } catch (error) {
      console.error('Failed to share', error)
      return false
    }
    return false
  }
}

export function LeagueStandingsPage(): ReactElement {
  const { slug = '' } = useParams<{ slug: string }>()
  const { overview } = useOutletContext<LeagueOutletContext>()
  const { memberships, isLoading: isAuthLoading } = useAuth()
  const { showToast } = useToast()
  const shareLink = useShareLink()

  const membership = useMemo(
    () => memberships.find((item) => item.league_slug === slug) ?? null,
    [memberships, slug],
  )

  const role: LeagueRole | null =
    membership?.role ?? overview?.league.role ?? null
  const canRefresh = canManageStandings(role)

  const {
    seasons,
    selectedSeasonId,
    setSelectedSeasonId,
    standings,
    isLoading,
    isFetching,
    error,
    refresh,
    isBypass,
  } = useLeagueStandings(slug)

  const [shareState, setShareState] = useState<'idle' | 'success' | 'error'>(
    'idle',
  )

  const tieLookup = useMemo(() => {
    const lookup = new Set<number>()
    for (let i = 1; i < standings.length; i += 1) {
      if (standings[i].points === standings[i - 1].points) {
        lookup.add(i - 1)
        lookup.add(i)
      }
    }
    return lookup
  }, [standings])

  const handleShare = async () => {
    if (!selectedSeasonId) {
      return
    }
    const link = computeSharesUrl(slug, selectedSeasonId)
    const ok = await shareLink(link)
    if (ok) {
      setShareState('success')
      showToast({
        title: 'Link ready',
        description: 'Standings link copied. Share it with your drivers!',
        variant: 'success',
      })
      setTimeout(() => {
        setShareState('idle')
      }, 3000)
    } else {
      setShareState('error')
      showToast({
        title: 'Unable to share',
        description:
          'Copy the browser URL manually and share it while we patch this up.',
        variant: 'error',
      })
    }
  }

  if (isAuthLoading || isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index.toString()}
            className="grid grid-cols-[auto_1fr_0.5fr_0.5fr_0.5fr] items-center gap-3 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-4 shadow shadow-slate-950/30"
          >
            <div className="h-4 w-8 rounded bg-slate-800" />
            <div className="h-4 w-full rounded bg-slate-800" />
            <div className="h-4 w-12 rounded bg-slate-800" />
            <div className="h-4 w-12 rounded bg-slate-800" />
            <div className="h-4 w-12 rounded bg-slate-800" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-100">
        <p className="font-semibold">We could not load standings.</p>
        <p className="mt-1 text-rose-100/80">{error.message}</p>
        <button
          type="button"
          onClick={() => {
            void refresh()
          }}
          className="mt-4 inline-flex items-center gap-2 rounded-full border border-rose-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-rose-100 transition hover:border-rose-200"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!selectedSeasonId || seasons.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-300">
        <p>
          No seasons found yet. Activate a season to start tracking standings.
        </p>
      </div>
    )
  }

  const shareLabel =
    shareState === 'success'
      ? 'Link copied'
      : shareState === 'error'
        ? 'Share failed'
        : 'Share standings'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">Standings</h2>
          <p className="text-sm text-slate-400">
            Points tally updates when results land.{' '}
            {isBypass
              ? 'Showing sample data while bypass mode is active.'
              : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedSeasonId}
            onChange={(event) => {
              setSelectedSeasonId(event.target.value)
            }}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/70 focus:ring-2 focus:ring-sky-500/40"
          >
            {seasons.map((season) => (
              <option key={season.id} value={season.id}>
                {season.name}
                {season.isActive ? ' • Active' : ''}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => {
              void refresh()
            }}
            disabled={isFetching || !canRefresh}
            className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 transition hover:border-sky-500 hover:text-sky-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={() => {
              void handleShare()
            }}
            className={classNames(
              'inline-flex items-center gap-2 rounded-full border border-sky-500/60 px-4 py-2 text-xs font-semibold uppercase tracking-wide transition hover:border-sky-400 hover:text-sky-100',
              shareState === 'success'
                ? 'bg-sky-500/10 text-sky-100'
                : 'text-sky-200',
            )}
          >
            {shareLabel}
          </button>
        </div>
      </div>

      {standings.length === 0 ? (
        <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-300">
          <p>
            No results yet for this season. Once events finish, standings will
            appear here.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-3xl border border-slate-800/70 bg-slate-900/60">
          <table className="min-w-full divide-y divide-slate-800 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Pos</th>
                <th className="px-4 py-3">Driver</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3 text-right">Points</th>
                <th className="px-4 py-3 text-right">Wins</th>
                <th className="px-4 py-3 text-right">Best finish</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-100">
              {standings.map((entry, index) => {
                const podiumClass = podiumTone(index + 1)
                const isTie = tieLookup.has(index)
                return (
                  <tr
                    key={entry.driverId}
                    className={classNames(
                      'transition hover:bg-slate-800/40',
                      podiumClass ?? '',
                    )}
                  >
                    <td className="px-4 py-3 text-sm font-semibold text-slate-200">
                      {index + 1}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold">{entry.driverName}</div>
                      <div className="text-xs text-slate-400">
                        {entry.podiums != null
                          ? `${entry.podiums.toString()} podium${entry.podiums === 1 ? '' : 's'}`
                          : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {entry.teamName ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-50">
                      {isTie
                        ? `=${entry.points.toString()}`
                        : entry.points.toString()}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300">
                      {entry.wins.toString()}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300">
                      {formatBestFinish(entry.bestFinish)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-4 text-xs text-slate-400">
        <p>
          Tie-breakers use wins first and the best finishing position second.
          Standings auto-refresh whenever results are posted; use Refresh if you
          think the worker queue is catching up slowly.
        </p>
      </div>
    </div>
  )
}
