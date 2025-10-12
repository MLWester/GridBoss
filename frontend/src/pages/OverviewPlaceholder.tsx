import type { ReactElement } from 'react'

export function OverviewPlaceholder(): ReactElement {
  return (
    <section className="grid gap-6 rounded-3xl border border-slate-800 bg-slate-900/40 p-6 shadow-lg shadow-slate-950/40">
      <h2 className="text-xl font-semibold tracking-tight">
        GridBoss roadmap in motion
      </h2>
      <p className="text-sm text-slate-400">
        Protected areas of the console will populate with dashboards, league
        management, and standings modules as subsequent PBIs land. For now,
        authentication is wired so the app can recognise you, maintain a
        session, and prepare to query the API with React Query powered data
        hooks.
      </p>
      <div className="grid gap-3 rounded-2xl border border-slate-800/80 bg-slate-950/60 p-4 text-left">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
          Next up
        </p>
        <ul className="space-y-2 text-sm text-slate-300">
          <li>• Dashboard league overview and quick actions</li>
          <li>• League and roster management tabs</li>
          <li>
            • Deeper integration with billing, Discord, and results pipelines
          </li>
        </ul>
      </div>
    </section>
  )
}
