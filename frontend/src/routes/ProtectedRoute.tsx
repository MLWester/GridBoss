import type { ReactElement } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { FullScreenState } from '../components/common/FullScreenState'

interface ProtectedRouteProps {
  children: ReactElement
}

export function ProtectedRoute({ children }: ProtectedRouteProps): JSX.Element {
  const { isAuthenticated, isLoading, error, refreshProfile } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <FullScreenState
        icon={
          <span className="inline-block h-12 w-12 animate-spin rounded-full border-2 border-slate-700 border-t-sky-400" />
        }
        title="Warming up the garage"
        description="Hold tight while we check your credentials and prep the control center."
      />
    )
  }

  if (error) {
    return (
      <FullScreenState
        icon={<span className="text-4xl">⚠️</span>}
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
