import type { ReactElement } from 'react'
import type { ThemeMode } from '../../hooks/useTheme'
import { useTheme } from '../../hooks/useTheme'

type Option = {
  key: ThemeMode
  label: string
  icon: ReactElement
}

const options: Option[] = [
  {
    key: 'light',
    label: 'Light theme',
    icon: (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-4 w-4"
      >
        <path d="M12 4.75V6.5" />
        <path d="M12 17.5v1.75" />
        <path d="M5.75 12H4" />
        <path d="M20 12h-1.75" />
        <path d="m7.5 7.5-1.25-1.25" />
        <path d="m17.75 17.75-1.25-1.25" />
        <path d="m6.25 17.75 1.25-1.25" />
        <path d="m16.5 7.5 1.25-1.25" />
        <circle cx="12" cy="12" r="4" />
      </svg>
    ),
  },
  {
    key: 'dark',
    label: 'Dark theme',
    icon: (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-4 w-4"
      >
        <path d="M20 12.5A8.5 8.5 0 0 1 11.5 4 6.5 6.5 0 1 0 20 12.5Z" />
      </svg>
    ),
  },
  {
    key: 'system',
    label: 'System theme',
    icon: (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-4 w-4"
      >
        <rect x="3.5" y="4.5" width="17" height="13" rx="2" />
        <path d="M8 20h8" />
      </svg>
    ),
  },
]

export function ThemeToggle(): ReactElement {
  const { theme, resolvedTheme, setTheme } = useTheme()

  return (
    <div
      role="group"
      aria-label="Theme"
      className="border-border/60 bg-surface/80 inline-flex items-center gap-1 rounded-full border p-1 shadow-soft backdrop-blur-sm transition-colors"
    >
      {options.map((option) => {
        const isActive =
          option.key === theme ||
          (theme === 'system' && option.key === resolvedTheme)
        return (
          <button
            key={option.key}
            type="button"
            onClick={() => {
              setTheme(option.key)
            }}
            className={[
              'inline-flex items-center gap-2 rounded-full px-2.5 py-1.5 text-xs font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-contrast shadow-elevated'
                : 'text-muted hover:bg-surface-muted/70 hover:text-text',
            ].join(' ')}
            aria-pressed={isActive}
            aria-label={option.label}
          >
            {option.icon}
            <span className="hidden capitalize sm:inline">{option.key}</span>
          </button>
        )
      })}
    </div>
  )
}

