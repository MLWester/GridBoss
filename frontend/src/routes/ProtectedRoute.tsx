import type { ReactElement } from 'react'
import { Navigate, useLocation, type Location } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { FullScreenState } from '../components/common/FullScreenState'

const SpinnerIcon = (
  <svg
    className="h-12 w-12 animate-spin text-sky-300"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    aria-hidden="true"
  >
    <circle className="opacity-30" cx="12" cy="12" r="9" />
    <path d="M21 12a9 9 0 0 0-9-9" strokeLinecap="round" />
  </svg>
)

const AlertIcon = (
  <svg
    className="h-12 w-12 text-amber-300"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    aria-hidden="true"
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01" />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M10.29 3.86 1.82 18.18A1 1 0 0 0 2.68 19.7h18.64a1 1 0 0 0 .86-1.52L13.71 3.86a1 1 0 0 0-1.72 0Z"
    />
  </svg>
)

interface ProtectedRouteProps {
  children: ReactElement
}

export function ProtectedRoute({ children }: ProtectedRouteProps): JSX.Element {
  const { isAuthenticated, isLoading, error, refreshProfile } = useAuth()
  const location = useLocation<{ from?: Location }>()

  if (isLoading) {
    return (
      <FullScreenState
        icon={SpinnerIcon}
        title="Warming up the garage"
        description="Hold tight while we check your credentials and prep the control center."
      />
    )
  }

  if (error) {
    return (
      <FullScreenState
        icon={AlertIcon}
        title="Unable to reach the pit wall"
        description={error}
        actionLabel="Try again"
        onAction={() => {
          void refreshProfile()
        }}
      />
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
