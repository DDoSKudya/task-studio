export type ToastKind = 'success' | 'error' | 'notice'

export type ToastItem = {
  id: number
  kind: ToastKind
  message: string
}

const DEFAULT_TTL_MS = 4200

export function useToasts() {
  const toasts = useState<ToastItem[]>('app-toasts', () => [])

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }

  function push(kind: ToastKind, message: string, ttlMs = DEFAULT_TTL_MS) {
    const text = message.trim()
    if (!text) {
      return
    }
    const id = Date.now() + Math.floor(Math.random() * 1000)
    toasts.value = [...toasts.value, { id, kind, message: text }]
    if (import.meta.client && ttlMs > 0) {
      window.setTimeout(() => dismiss(id), ttlMs)
    }
  }

  return {
    toasts,
    dismiss,
    success: (message: string, ttlMs?: number) => push('success', message, ttlMs),
    error: (message: string, ttlMs?: number) => push('error', message, ttlMs),
    notice: (message: string, ttlMs?: number) => push('notice', message, ttlMs),
  }
}
