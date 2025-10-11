import type { ReactNode } from 'react'

interface FullScreenStateProps {
  icon?: ReactNode
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export function FullScreenState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: FullScreenStateProps): JSX.Element {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
      <div className="flex max-w-md flex-col items-center gap-4">
        {icon && <div className="text-4xl text-sky-400">{icon}</div>}
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description ? (
            <p className="text-sm text-slate-400">{description}</p>
          ) : null}
        </div>
        {actionLabel && onAction ? (
          <button
            type="button"
            onClick={onAction}
            className="rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 shadow-md transition hover:bg-sky-400"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
    </div>
  )
}
