<script setup lang="ts">
const props = defineProps<{
  sessionId: string
  instructions: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  completed: []
}>()

const { t } = useI18n()
const { submit, getAttempt } = useSessions()
const toasts = useToasts()

const running = ref(false)
const statusText = ref('')

let pollTimer: ReturnType<typeof setInterval> | null = null

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onBeforeUnmount(stopPolling)

async function pollAttempts(attemptId: string) {
  const attempt = await getAttempt(props.sessionId, attemptId)
  if (!attempt?.result) {
    return
  }
  const result = attempt.result as { status?: string; passed?: boolean; feedback?: string; score?: number }
  if (result.status === 'pending') {
    statusText.value = t('session.lab.running')
    return
  }
  stopPolling()
  running.value = false
  if (result.passed) {
    toasts.success(t('session.feedback.passed'))
    emit('completed')
  } else {
    toasts.error(result.feedback ?? t('session.feedback.failed'))
  }
  statusText.value = ''
}

async function onRunLab() {
  running.value = true
  statusText.value = t('session.lab.starting')
  try {
    const result = await submit(props.sessionId, {})
    if (result.status === 'pending') {
      statusText.value = t('session.lab.running')
      pollTimer = setInterval(() => {
        void pollAttempts(result.attempt_id)
      }, 2000)
      await pollAttempts(result.attempt_id)
    } else {
      running.value = false
      if (result.passed) {
        toasts.success(t('session.feedback.passed'))
        emit('completed')
      } else {
        toasts.error(result.feedback ?? t('session.feedback.failed'))
      }
    }
  } catch {
    stopPolling()
    running.value = false
    statusText.value = ''
    toasts.error(t('session.errors.actionFailed'))
  }
}
</script>

<template>
  <div style="display: flex; flex-direction: column; gap: 1rem">
    <p style="white-space: pre-wrap; font-size: 0.875rem; line-height: 1.55">{{ instructions }}</p>
    <button class="btn-primary" type="button" :disabled="disabled || running" @click="onRunLab">
      {{ running ? t('session.lab.running') : t('session.lab.run') }}
    </button>
    <p v-if="statusText" class="data-list-meta">{{ statusText }}</p>
  </div>
</template>
