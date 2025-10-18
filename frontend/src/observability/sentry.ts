import * as Sentry from '@sentry/react'

const env = import.meta.env as Record<string, string | undefined>
const rawDsn = env.VITE_SENTRY_DSN
const dsn = typeof rawDsn === 'string' && rawDsn.length > 0 ? rawDsn : undefined

if (dsn) {
  const rawSampleRate = env.VITE_SENTRY_TRACES_SAMPLE_RATE
  const parsedSampleRate = rawSampleRate ? Number(rawSampleRate) : 0
  const tracesSampleRate = Number.isFinite(parsedSampleRate) ? parsedSampleRate : 0

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    tracesSampleRate,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({ maskAllText: false, blockAllMedia: false }),
    ],
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
  })
}
