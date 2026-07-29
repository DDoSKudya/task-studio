import { expectedChoiceIndex, sessionFeedbackMessage } from '~/utils/session'

type TranslateFn = (key: string, params?: Record<string, unknown>) => string

type ToastApi = {
  success: (message: string) => void
  error: (message: string) => void
}

type GradeResult = {
  passed: boolean
  feedback?: string | null
  details?: Record<string, unknown>
}

export function useSessionGradeSubmit(options: {
  t: TranslateFn
  toasts: ToastApi
  reload: () => Promise<void>
  sessionStatus: () => string | undefined
}) {
  const actionPending = ref(false)

  function notifyResult(result: GradeResult) {
    const message = sessionFeedbackMessage(result, options.t)
    if (result.passed) {
      options.toasts.success(message)
    } else {
      options.toasts.error(message)
    }
  }

  async function runGradeSubmit(action: () => Promise<void>) {
    actionPending.value = true
    try {
      await action()
      await options.reload()
      if (options.sessionStatus() === 'completed') {
        options.toasts.success(options.t('session.completed'))
      }
    } catch {
      options.toasts.error(options.t('session.errors.actionFailed'))
    } finally {
      actionPending.value = false
    }
  }

  return {
    actionPending,
    expectedChoiceIndex,
    notifyResult,
    runGradeSubmit,
    sessionFeedbackMessage,
  }
}
