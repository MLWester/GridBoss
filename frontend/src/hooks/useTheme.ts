import { useContext } from 'react'
import { ThemeContext } from '../providers/theme/context'

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}

export type { ThemeMode, ResolvedTheme, ThemeContextValue } from '../providers/theme/types'

