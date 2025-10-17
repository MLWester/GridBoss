import {
  type ReactElement,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { ThemeContext } from './theme/context'
import type { ResolvedTheme, ThemeContextValue, ThemeMode } from './theme/types'

const STORAGE_KEY = 'gridboss-theme'
const TRANSITION_CLASS = 'theme-transition'

const getMedia = (): MediaQueryList | null => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return null
  }
  return window.matchMedia('(prefers-color-scheme: dark)')
}

const resolveTheme = (mode: ThemeMode): ResolvedTheme => {
  if (mode === 'light' || mode === 'dark') {
    return mode
  }
  const media = getMedia()
  return media?.matches ? 'dark' : 'light'
}

const applyTheme = (mode: ThemeMode, enableTransition = false): ResolvedTheme => {
  const root = document.documentElement
  const resolved = resolveTheme(mode)
  root.setAttribute('data-theme', resolved)
  root.setAttribute('data-user-theme', mode)
  root.style.colorScheme = resolved

  if (enableTransition) {
    root.classList.add(TRANSITION_CLASS)
    window.setTimeout(() => {
      root.classList.remove(TRANSITION_CLASS)
    }, 180)
  }

  return resolved
}

const getInitialTheme = (): ThemeMode => {
  if (typeof document === 'undefined') {
    return 'system'
  }
  const datasetTheme = document.documentElement.getAttribute('data-user-theme')
  if (datasetTheme === 'light' || datasetTheme === 'dark' || datasetTheme === 'system') {
    return datasetTheme
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored
    }
  } catch {
    // ignore storage errors
  }
  return 'system'
}

export function ThemeProvider({ children }: { children: ReactNode }): ReactElement {
  const initialThemeRef = useRef<ThemeMode | null>(null)
  if (initialThemeRef.current === null) {
    initialThemeRef.current = getInitialTheme()
  }
  const initialTheme = initialThemeRef.current

  const [theme, setThemeState] = useState<ThemeMode>(initialTheme)
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    resolveTheme(initialTheme),
  )
  const mediaRef = useRef<MediaQueryList | null>(null)

  const updateTheme = useCallback(
    (next: ThemeMode) => {
      setThemeState(next)
      try {
        localStorage.setItem(STORAGE_KEY, next)
      } catch {
        // ignore write errors (protected storage etc)
      }
      const resolved = applyTheme(next, true)
      setResolvedTheme(resolved)
    },
    [setThemeState],
  )

  useEffect(() => {
    setResolvedTheme(applyTheme(initialTheme))
  }, [initialTheme])

  useEffect(() => {
    mediaRef.current = getMedia()
    const media = mediaRef.current
    if (!media) {
      return
    }
    const handleChange = () => {
      setResolvedTheme(applyTheme(theme))
    }
    if (theme === 'system') {
      media.addEventListener('change', handleChange)
    }
    return () => {
      media.removeEventListener('change', handleChange)
    }
  }, [theme])

  const contextValue: ThemeContextValue = {
    theme,
    resolvedTheme,
    setTheme: updateTheme,
  }

  return <ThemeContext.Provider value={contextValue}>{children}</ThemeContext.Provider>
}
