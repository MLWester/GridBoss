import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactElement, ReactNode } from 'react'
import {
  ToastContext,
  type ToastInput,
  type ToastVariant,
} from './ToastContext'

interface ToastRecord extends ToastInput {
  id: number
}

function getVariantStyles(variant: ToastVariant = 'info'): string {
  if (variant === 'success') {
    return 'border-success/50 bg-success/10 text-text'
  }

  if (variant === 'error') {
    return 'border-danger/50 bg-danger/10 text-text'
  }

  return 'border-accent/40 bg-surface/90 text-text'
}

export function ToastProvider({
  children,
}: {
  children: ReactNode
}): ReactElement {
  const [toasts, setToasts] = useState<ToastRecord[]>([])
  const timers = useRef<Map<number, number>>(new Map())

  const removeToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      window.clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const showToast = useCallback(
    (toast: ToastInput) => {
      const id = Date.now() + Math.random()
      const record: ToastRecord = {
        id,
        title: toast.title,
        description: toast.description,
        variant: toast.variant ?? 'info',
        duration: toast.duration,
      }

      setToasts((current) => [...current, record])

      const timeout = window.setTimeout(() => {
        removeToast(id)
      }, toast.duration ?? 5000)

      timers.current.set(id, timeout)
    },
    [removeToast],
  )

  useEffect(
    () => () => {
      for (const timeoutId of timers.current.values()) {
        window.clearTimeout(timeoutId)
      }
      timers.current.clear()
    },
    [],
  )

  const contextValue = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-80 max-w-[calc(100vw-3rem)] flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto overflow-hidden rounded-2xl border px-4 py-3 shadow-elevated backdrop-blur-sm transition-colors ${getVariantStyles(
              toast.variant,
            )}`}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <p className="text-sm font-semibold">{toast.title}</p>
                {toast.description ? (
                  <p className="mt-1 text-xs text-muted">{toast.description}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => {
                  removeToast(toast.id)
                }}
                className="border-border/60 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted transition hover:border-accent hover:text-accent"
              >
                Close
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
