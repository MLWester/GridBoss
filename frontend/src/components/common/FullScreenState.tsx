import type { ReactElement, ReactNode } from 'react'

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
}: FullScreenStateProps): ReactElement {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-app px-6 text-center text-text transition-colors">
      <div className="flex max-w-md flex-col items-center gap-4">
        {icon && <div className="text-4xl text-accent">{icon}</div>}
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description ? (
            <p className="text-sm text-muted">{description}</p>
          ) : null}
        </div>
        {actionLabel && onAction ? (
          <button
            type="button"
            onClick={onAction}
            className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-accent-contrast shadow-soft transition hover:brightness-110"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
    </div>
  )
}
