import { createContext } from 'react'

export type ToastVariant = 'info' | 'success' | 'error'

export interface ToastInput {
  title: string
  description?: string
  variant?: ToastVariant
  duration?: number
}

export interface ToastContextValue {
  showToast: (toast: ToastInput) => void
}

export const ToastContext = createContext<ToastContextValue | undefined>(undefined)
