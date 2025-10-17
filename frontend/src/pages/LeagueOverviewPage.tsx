import { useEffect, useMemo, useRef } from 'react'
import type { ReactElement } from 'react'
import { useOutletContext } from 'react-router-dom'
import type { LeagueOutletContext } from '../components/layout/LeagueLayout'
import { useToast } from '../hooks/useToast'
import { renderSafeMarkdown } from '../utils/markdown'

function SectionCard({
  children,
}: {
  children: React.ReactNode
}): ReactElement {
  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/30">
      {children}
    </div>
  )
}

function formatDateTime(value: string | undefined | null): string {
  if (!value) {
    return 'TBD'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'TBD'
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date)
}

function isDiscordEligible(plan: string | null | undefined): boolean {
  if (!plan) {
    return false
  }
  const normalized = plan.toUpperCase()
  return normalized === 'PRO' || normalized === 'ELITE'
}

export function LeagueOverviewPage(): ReactElement {
  const { overview, isLoading, error, refetch } =
    useOutletContext<LeagueOutletContext>()
  const { showToast } = useToast()
  const errorNotifiedRef = useRef<string | null>(null)

  const nextEvent = overview?.nextEvent || null
  const recentResult = overview?.recentResult || null
  const plan = overview?.league.plan || null
  const planLabel = plan ? plan : 'FREE'
  const canLinkDiscord = isDiscordEligible(plan)
  const showDiscordCta = !overview?.discordLinked && canLinkDiscord

  const podium = useMemo(
    () => recentResult?.podium ?? [],
    [recentResult?.podium],
  )

  const descriptionHtml = useMemo(
    () => renderSafeMarkdown(overview?.league.description ?? null),
    [overview?.league.description],
  )

  useEffect(() => {
    if (error) {
      const message = error.message || 'Unexpected error'
      if (errorNotifiedRef.current !== message) {
        showToast({
          title: 'Failed to load league overview',
          description: message,
          variant: 'error',
        })
        errorNotifiedRef.current = message
      }
    } else {
      errorNotifiedRef.current = null
    }
  }, [error, showToast])

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard>
          <div className="h-5 w-32 animate-pulse rounded bg-slate-800" />
          <div className="mt-3 h-4 w-48 animate-pulse rounded bg-slate-800" />
        </SectionCard>
        <SectionCard>
          <div className="h-5 w-32 animate-pulse rounded bg-slate-800" />
          <div className="mt-3 h-4 w-48 animate-pulse rounded bg-slate-800" />
        </SectionCard>
        <SectionCard>
          <div className="h-5 w-32 animate-pulse rounded bg-slate-800" />
          <div className="mt-3 h-24 animate-pulse rounded bg-slate-800" />
        </SectionCard>
      </div>
    )
  }

  if (error) {
    return (
      <SectionCard>
        <p className="text-sm text-rose-100">
          We could not load the league overview.{' '}
          <span className="text-xs text-rose-300">{error.message}</span>
        </p>
        <button
          type="button"
          onClick={() => {
            void refetch()
          }}
          className="mt-4 inline-flex items-center gap-2 rounded-full border border-rose-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-rose-100 transition hover:border-rose-200"
        >
          Retry
        </button>
      </SectionCard>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
      <div className="space-y-4">
        {descriptionHtml ? (
          <SectionCard>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              About this league
            </p>
            <div
              className="[a]:underline [a]:text-sky-300 mt-3 space-y-3 text-sm leading-relaxed text-slate-200"
              dangerouslySetInnerHTML={{ __html: descriptionHtml }}
            />
          </SectionCard>
        ) : null}

        <SectionCard>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Next event
          </p>
          {nextEvent ? (
            <div>
              <p className="mt-2 text-lg font-semibold text-slate-100">
                {nextEvent.name}
              </p>
              <p className="text-sm text-slate-400">{nextEvent.track}</p>
              <p className="mt-3 text-xs text-slate-300">
                Lights out: {formatDateTime(nextEvent.startTime)}
              </p>
              <span className="mt-4 inline-flex items-center rounded-full border border-sky-400/60 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-sky-200">
                {nextEvent.status.toLowerCase()}
              </span>
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-400">
              No upcoming event is scheduled yet.
            </p>
          )}
        </SectionCard>

        <SectionCard>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Last result
          </p>
          {recentResult ? (
            <div>
              <p className="mt-2 text-lg font-semibold text-slate-100">
                {recentResult.event.name}
              </p>
              <p className="text-sm text-slate-400">
                {recentResult.event.track}
              </p>
              <p className="mt-3 text-xs text-slate-300">
                Completed: {formatDateTime(recentResult.event.startTime)}
              </p>
              {podium.length > 0 ? (
                <ul className="mt-4 space-y-2 text-sm text-slate-200">
                  {podium.slice(0, 3).map((entry) => (
                    <li
                      key={entry.position}
                      className="flex items-center gap-3"
                    >
                      <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-700/70 text-xs font-semibold text-slate-300">
                        {entry.position}
                      </span>
                      <div>
                        <p className="font-semibold text-slate-100">
                          {entry.driverName}
                        </p>
                        {entry.teamName ? (
                          <p className="text-xs text-slate-400">
                            {entry.teamName}
                          </p>
                        ) : null}
                      </div>
                      {entry.points != null ? (
                        <span className="ml-auto text-xs text-slate-300">
                          {entry.points} pts
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-slate-400">
                  Podium details will populate here once the steward posts
                  official results.
                </p>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-400">
              Race results will appear here once events are completed.
            </p>
          )}
        </SectionCard>
      </div>

      <div className="space-y-4">
        <SectionCard>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Discord integration
          </p>
          {overview?.discordLinked ? (
            <p className="mt-3 text-sm text-emerald-200">
              Discord is linked. Announcements and race control messages are
              ready to go.
            </p>
          ) : showDiscordCta ? (
            <div className="mt-3 space-y-3 text-sm text-slate-300">
              <p>
                Connect your Discord server to send race summaries and schedule
                notifications.
              </p>
              <button
                type="button"
                className="inline-flex items-center rounded-full border border-sky-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-sky-200 transition hover:border-sky-200"
              >
                Link Discord (coming soon)
              </button>
            </div>
          ) : (
            <div className="mt-3 space-y-3 text-sm text-slate-300">
              <p>
                Discord linking unlocks on the Pro plan. Upgrade when billing
                launches to automate results recaps and race announcements.
              </p>
              <p className="text-xs text-slate-500">
                Current plan: {planLabel}
              </p>
            </div>
          )}
        </SectionCard>

        <SectionCard>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Quick tips
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-300">
            <li>Use the Drivers tab to manage rosters and assign roles.</li>
            <li>Track upcoming and completed races in the Events tab.</li>
            <li>Configure points, billing, and integrations under Settings.</li>
          </ul>
        </SectionCard>
      </div>
    </div>
  )
}
