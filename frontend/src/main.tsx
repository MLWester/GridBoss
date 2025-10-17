import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import { AuthProvider } from './providers/AuthProvider'
import { ToastProvider } from './providers/ToastProvider'
import { ThemeProvider } from './providers/ThemeProvider'
import App from './App'

const container = document.getElementById('root')

if (!container) {
  throw new Error('Root element not found')
}

const queryClient = new QueryClient()

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
