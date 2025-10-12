import { useCallback, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import type { MutationStatus } from '@tanstack/react-query'
import { createLeague } from '../api/leagues'
import { ApiError } from '../api/auth'
import { useLeagues } from '../hooks/useLeagues'
import { useAuth } from '../hooks/useAuth'
import type { CreateLeagueRequest, LeagueSummary } from '../types/leagues'
import type { LeagueRole } from '../types/auth'

function slugify(source: string): string {
  return source
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '')
    .slice(0, 50)
}

const PlusIcon = (): ReactElement => (
  <svg
    className="h-4 w-4"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m-7-7h14" />
  </svg>
)

const RefreshIcon = (): ReactElement => (
  <svg
    className="h-4 w-4"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M4 4v6h6M20 20v-6h-6M5 19a9 9 0 0 0 9 3 9 9 0 0 0 6.36-15.36L20 4M4 20l1.64-1.64"
    />
  </svg>
)

function SkeletonCard(): ReactElement {
  return (
    <div className="animate-pulse rounded-2xl border border-slate-800/70 bg-slate-900/40 p-4">
      <div className="h-5 w-32 rounded bg-slate-800" />
      <div className="mt-3 h-4 w-24 rounded bg-slate-800" />
      <div className="mt-6 flex gap-2">
        <div className="h-6 w-16 rounded-full bg-slate-800" />
        <div className="h-6 w-20 rounded-full bg-slate-800" />
      </div>
    </div>
  )
}

function RoleBadge({ role }: { role: LeagueRole | null }): ReactElement {
  if (!role) {
    return (
      <span className="rounded-full border border-slate-700/70 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Member
      </span>
    )
  }

  const tone =
    role === 'OWNER'
      ? 'text-amber-300 border-amber-400/40'
      : role === 'ADMIN'
        ? 'text-sky-300 border-sky-400/40'
        : role === 'STEWARD'
          ? 'text-emerald-300 border-emerald-400/40'
          : 'text-slate-200 border-slate-500/40'

  return (
    <span
      className={`rounded-full border px-3 py-0.5 text-xs font-semibold uppercase tracking-wide ${tone}`}
    >
      {role.toLowerCase()}
    </span>
  )
}

interface CreateDialogProps {
  open: boolean
  onOpenChange: (value: boolean) => void
  onSubmit: (payload: CreateLeagueRequest) => Promise<void>
  status: MutationStatus
  errorMessage: string | null
  isBypass: boolean
}

function CreateLeagueDialog({
  open,
  onOpenChange,
  onSubmit,
  status,
  errorMessage,
  isBypass,
}: CreateDialogProps): ReactElement | null {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [slugEdited, setSlugEdited] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  if (!open) {
    return null
  }

  const handleNameChange = (value: string) => {
    setName(value)
    if (!slugEdited) {
      setSlug(slugify(value))
    }
  }

  const reset = () => {
    setName('')
    setSlug('')
    setSlugEdited(false)
    setFormError(null)
  }

  const close = () => {
    onOpenChange(false)
    reset()
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)

    const trimmedName = name.trim()
    const trimmedSlug = slug.trim()

    if (!trimmedName) {
      setFormError('Name is required.')
      return
    }

    if (!trimmedSlug) {
      setFormError('Slug is required.')
      return
    }

    try {
      await onSubmit({ name: trimmedName, slug: trimmedSlug })
      close()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setFormError('This slug is already taken. Try another one.')
      } else if (err instanceof Error) {
        setFormError(err.message)
      } else {
        setFormError('Something went wrong while creating the league.')
      }
    }
  }

  const actionLabel =
    status === 'pending'
      ? 'Creating�'
      : isBypass
        ? 'Simulate League'
        : 'Create League'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-lg rounded-3xl border border-slate-800/70 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/60">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">
              Create a new league
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {isBypass
                ? 'Bypass mode is active, so this will simulate a league for preview purposes.'
                : 'Provide a unique slug used for your league URL. Slugs can include letters, numbers, and hyphens.'}
            </p>
          </div>
          <button
            type="button"
            onClick={close}
            className="rounded-full border border-slate-700/70 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:border-slate-500 hover:text-slate-100"
          >
            Cancel
          </button>
        </div>

        <form
          onSubmit={(event) => {
            void handleSubmit(event)
          }}
          className="mt-6 space-y-5"
        >
          <label className="block text-sm">
            <span className="text-slate-200">League name</span>
            <input
              value={name}
              onChange={(event) => {
                handleNameChange(event.target.value)
              }}
              type="text"
              className="mt-2 w-full rounded-2xl border border-slate-700/70 bg-slate-950 px-4 py-2 text-slate-100 outline-none focus:border-sky-500/70"
              placeholder="Sim Racing League"
              required
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-200">Slug</span>
            <input
              value={slug}
              onChange={(event) => {
                setSlug(event.target.value.toLowerCase())
                setSlugEdited(true)
              }}
              type="text"
              className="mt-2 w-full rounded-2xl border border-slate-700/70 bg-slate-950 px-4 py-2 text-slate-100 outline-none focus:border-sky-500/70"
              placeholder="sim-racing-league"
              required
            />
          </label>

          {(formError || errorMessage) && (
            <p className="text-sm text-rose-300">{formError ?? errorMessage}</p>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="submit"
              disabled={status === 'pending'}
              className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {actionLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function DashboardPage(): ReactElement {
  const { leagues, isLoading, error, refetch, addLocalLeague } = useLeagues()
  const { refreshProfile, isBypassAuth, accessToken, billingPlan } = useAuth()
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const planLabel = useMemo(
    () => billingPlan?.plan ?? 'FREE',
    [billingPlan?.plan],
  )

  const computeDriverLimit = useCallback(() => {
    if (billingPlan?.plan === 'ELITE') return 9999
    if (billingPlan?.plan === 'PRO') return 100
    return 20
  }, [billingPlan?.plan])

  const mutation = useMutation<LeagueSummary, Error, CreateLeagueRequest>({
    mutationFn: async (payload) => {
      if (!accessToken) {
        const mockLeague: LeagueSummary = {
          id: `${payload.slug}-${String(Date.now())}`,
          name: payload.name,
          slug: payload.slug,
          plan: billingPlan?.plan ?? 'FREE',
          driverLimit: computeDriverLimit(),
          role: 'OWNER',
        }
        addLocalLeague(mockLeague)
        return mockLeague
      }

      const created = await createLeague(accessToken, payload)
      return created
    },
    onSuccess: async () => {
      if (accessToken) {
        await Promise.allSettled([refetch(), refreshProfile()])
      } else {
        await refetch()
      }
      setIsDialogOpen(false)
    },
  })

  const handleCreate = async (payload: CreateLeagueRequest) => {
    await mutation.mutateAsync(payload)
  }

  const renderLeagues = () => {
    if (isLoading) {
      return (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <SkeletonCard key={index} />
          ))}
        </div>
      )
    }

    if (error) {
      return (
        <div className="rounded-3xl border border-rose-500/40 bg-rose-500/5 p-6 text-sm text-rose-200">
          <p className="font-semibold">We could not load your leagues.</p>
          <p className="mt-2 text-rose-100/80">{error.message}</p>
          <button
            type="button"
            onClick={() => {
              void refetch()
            }}
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-rose-400/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-rose-100 transition hover:border-rose-200"
          >
            <RefreshIcon /> Retry
          </button>
        </div>
      )
    }

    if (leagues.length === 0) {
      return (
        <div className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6 text-sm text-slate-200">
          <p className="text-slate-100">No leagues yet</p>
          <p className="mt-2 text-slate-400">
            Create your first league to unlock the management dashboard, drivers
            roster, and standings workspace.
          </p>
          <button
            type="button"
            onClick={() => {
              setIsDialogOpen(true)
            }}
            className="mt-4 inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
          >
            <PlusIcon /> Create league
          </button>
        </div>
      )
    }

    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {leagues.map((league) => (
          <Link
            key={league.id}
            to={`/leagues/${league.slug}`}
            className="block rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 shadow shadow-slate-950/40 transition hover:border-sky-500/60 hover:text-sky-100"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-lg font-semibold text-slate-100">
                  {league.name}
                </p>
                <p className="text-xs text-slate-400">slug: {league.slug}</p>
              </div>
              <RoleBadge role={league.role ?? null} />
            </div>
            <dl className="mt-4 space-y-2 text-xs text-slate-400">
              <div className="flex items-center justify-between">
                <dt>Plan</dt>
                <dd className="text-slate-200">{league.plan ?? planLabel}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Driver limit</dt>
                <dd className="text-slate-200">
                  {league.driverLimit ?? 'n/a'}
                </dd>
              </div>
            </dl>
          </Link>
        ))}
      </div>
    )
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">
            Your leagues
          </h2>
          <p className="text-sm text-slate-400">
            Manage your organisations from this hub. Create new leagues or jump
            into rosters once upcoming modules land.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsDialogOpen(true)
          }}
          className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
        >
          <PlusIcon /> Create league
        </button>
      </div>

      {renderLeagues()}

      <CreateLeagueDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        onSubmit={handleCreate}
        status={mutation.status}
        errorMessage={
          mutation.isError
            ? mutation.error instanceof Error
              ? mutation.error.message
              : 'Failed to create league'
            : null
        }
        isBypass={isBypassAuth}
      />
    </section>
  )
}
