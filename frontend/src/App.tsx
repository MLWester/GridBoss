function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="max-w-2xl space-y-6 px-6 py-12 text-center">
        <p className="text-sm uppercase tracking-[0.3em] text-sky-400">
          GridBoss
        </p>
        <h1 className="text-4xl font-semibold sm:text-5xl">
          Sim racing leagues, managed with style.
        </h1>
        <p className="text-slate-300">
          Build rosters, schedule events, capture results, and announce winners
          without leaving the GridBoss hub. This placeholder shell will evolve
          into the authenticated app experience within upcoming PBIs.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button className="rounded-full bg-sky-500 px-6 py-2 text-sm font-medium text-slate-950 shadow-sm transition hover:bg-sky-400">
            Launch Dashboard
          </button>
          <button className="rounded-full border border-slate-600 px-6 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-400">
            View Master Spec
          </button>
        </div>
      </div>
    </main>
  )
}

export default App
