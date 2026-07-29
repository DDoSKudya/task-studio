export type ConfirmOptions = {
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
}

type ConfirmState = ConfirmOptions & {
  open: boolean
  resolve: ((value: boolean) => void) | null
}

const state = reactive<ConfirmState>({
  open: false,
  title: '',
  message: '',
  confirmLabel: undefined,
  cancelLabel: undefined,
  danger: false,
  resolve: null,
})

export function useConfirm() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    if (state.open && state.resolve) {
      state.resolve(false)
    }
    return new Promise((resolve) => {
      state.title = options.title
      state.message = options.message ?? ''
      state.confirmLabel = options.confirmLabel
      state.cancelLabel = options.cancelLabel
      state.danger = options.danger ?? false
      state.resolve = resolve
      state.open = true
    })
  }

  function settle(value: boolean) {
    const resolve = state.resolve
    state.open = false
    state.resolve = null
    resolve?.(value)
  }

  return {
    state: readonly(state),
    confirm,
    settle,
  }
}
