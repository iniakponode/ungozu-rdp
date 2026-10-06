'use client'

import * as React from 'react'

type Theme = 'light' | 'dark'

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: 'light' | 'dark' | 'system'
  enableSystem?: boolean
  attribute?: string
  disableTransitionOnChange?: boolean
}

type ThemeContextValue = {
  theme: Theme
  setTheme: (theme: Theme) => void
  mounted: boolean
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null)

function resolveTheme(defaultTheme: ThemeProviderProps['defaultTheme'], enableSystem: boolean) {
  const storedTheme = window.localStorage.getItem('theme')
  if (storedTheme === 'light' || storedTheme === 'dark') {
    return storedTheme
  }

  if ((defaultTheme === 'system' || !defaultTheme) && enableSystem) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  return defaultTheme === 'dark' ? 'dark' : 'light'
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  enableSystem = true,
  attribute = 'class',
}: ThemeProviderProps) {
  const [theme, setTheme] = React.useState<Theme>('light')
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    const initialTheme = resolveTheme(defaultTheme, enableSystem)
    setTheme(initialTheme)
    setMounted(true)
  }, [defaultTheme, enableSystem])

  React.useEffect(() => {
    if (!mounted) {
      return
    }

    const root = document.documentElement
    if (attribute === 'class') {
      root.classList.toggle('dark', theme === 'dark')
    } else {
      root.setAttribute(attribute, theme)
    }

    window.localStorage.setItem('theme', theme)
  }, [attribute, mounted, theme])

  const value = React.useMemo(() => ({ theme, setTheme, mounted }), [theme, mounted])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = React.useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
