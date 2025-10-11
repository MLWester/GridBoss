import type { ReactElement } from 'react'

interface PlaceholderProps {
  title: string
  description: string
}

function Placeholder({ title, description }: PlaceholderProps): ReactElement {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center gap-3 text-center text-slate-300">
      <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
      <p className="max-w-xl text-sm text-slate-400">{description}</p>
      <span className="rounded-full border border-slate-700/70 px-3 py-1 text-xs uppercase tracking-wide text-slate-400">
        Coming soon
      </span>
    </div>
  )
}

export function LeagueDriversPlaceholder(): ReactElement {
  return (
    <Placeholder
      title="Drivers management is on the grid"
      description="Upcoming PBIs will add roster management, invitations, and quick-edit capabilities."
    />
  )
}

export function LeagueTeamsPlaceholder(): ReactElement {
  return (
    <Placeholder
      title="Teams workspace"
      description="Configure team line-ups, assign livery presets, and manage driver transfers once the feature lands."
    />
  )
}

export function LeagueEventsPlaceholder(): ReactElement {
  return (
    <Placeholder
      title="Events timeline"
      description="Create, reorder, and manage race weekends with timezone support in the events module coming soon."
    />
  )
}

export function LeagueStandingsPlaceholder(): ReactElement {
  return (
    <Placeholder
      title="Standings board"
      description="Season standings with tie-break insights and sharing tools will appear here after results PBIs ship."
    />
  )
}

export function LeagueSettingsPlaceholder(): ReactElement {
  return (
    <Placeholder
      title="League settings"
      description="Plan upgrades, points configuration, and Discord controls will live here as the console expands."
    />
  )
}
