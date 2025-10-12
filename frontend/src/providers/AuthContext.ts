import { createContext } from 'react'
import type { MeResponse } from '../types/auth'

export interface AuthContextValue {
  profile: MeResponse | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean
  isBypassAuth: boolean
  accessToken: string | null
  refreshProfile: () => Promise<void>
  logout: () => Promise<void>
  setAccessToken: (token: string | null) => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
)
