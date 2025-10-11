import { useContext } from 'react'
import { AuthContext } from '../providers/AuthContext'

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  const { profile, ...rest } = context
  return {
    ...rest,
    profile,
    user: profile?.user ?? null,
    memberships: profile?.memberships ?? [],
    billingPlan: profile?.billingPlan ?? null,
  }
}
