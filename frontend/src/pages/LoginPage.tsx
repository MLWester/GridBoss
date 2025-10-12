import { useEffect } from 'react'
import type { ReactElement } from 'react'
import { useLocation, useNavigate, type Location } from 'react-router-dom'
import { API_URL } from '../lib/env'
import { useAuth } from '../hooks/useAuth'

export function LoginPage(): ReactElement {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      const state = (location.state as { from?: Location } | null) ?? null
      const redirect = state?.from?.pathname ?? '/'
      void navigate(redirect, { replace: true })
    }
  }, [isAuthenticated, isLoading, location, navigate])

  const handleLogin = () => {
    window.location.href = `${API_URL}/auth/discord/start`
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <div className="w-full max-w-md space-y-6 rounded-3xl border border-slate-800 bg-slate-900/40 p-8 text-center shadow-lg shadow-slate-950/40">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-400">
            GridBoss
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">
            Sign in with Discord
          </h1>
          <p className="text-sm text-slate-400">
            Authenticate via Discord to access your leagues, manage results, and
            prepare for the full GridBoss rollout.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogin}
          className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-sky-500 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            aria-hidden="true"
            className="h-5 w-5"
          >
            <path
              fill="currentColor"
              d="M20.317 4.369A19.791 19.791 0 0 0 16.558 3a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.743 0c-.164-.401-.41-.875-.622-1.25a.077.077 0 0 0-.079-.037 19.736 19.736 0 0 0-3.758 1.369.07.07 0 0 0-.032.027C2.18 9.045 1.29 13.58 1.665 18.061a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.99 3.03.077.077 0 0 0 .084-.027c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.105 12.94 12.94 0 0 1-1.872-.892.078.078 0 0 1-.008-.13c.125-.094.25-.19.37-.29a.074.074 0 0 1 .077-.01c3.926 1.8 8.18 1.8 12.062 0a.073.073 0 0 1 .078.009c.12.1.245.197.37.291a.078.078 0 0 1-.006.129 12.64 12.64 0 0 1-1.873.891.077.077 0 0 0-.04.106c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.86 19.86 0 0 0 6.002-3.03.077.077 0 0 0 .03-.056c.5-5.177-.838-9.674-3.548-13.666a.061.061 0 0 0-.03-.03ZM8.02 15.33c-1.182 0-2.155-1.085-2.155-2.419c0-1.333.955-2.419 2.155-2.419c1.21 0 2.174 1.096 2.155 2.42c0 1.333-.955 2.418-2.155 2.418Zm7.974 0c-1.182 0-2.155-1.085-2.155-2.419c0-1.333.955-2.419 2.155-2.419c1.21 0 2.174 1.096 2.155 2.42c0 1.333-.945 2.418-2.155 2.418Z"
            />
          </svg>
          Continue with Discord
        </button>
        <p className="text-xs text-slate-200">
          You will be redirected to Discord to authorise the GridBoss app. Once
          complete you&apos;ll return here with your session ready to go.
        </p>
      </div>
    </main>
  )
}
