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
const { submit, listAttempts } = useSessions()

const running = ref(false)
const statusText = ref('')
const feedback = ref('')

let pollTimer: ReturnType<typeof setInterval> | null = null

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onBeforeUnmount(stopPolling)

async function pollAttempts(attemptId: string) {
  const attempts = await listAttempts(props.sessionId)
  const attempt = attempts.find((row) => row.id === attemptId)
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
    feedback.value = t('session.feedback.passed')
    emit('completed')
  } else {
    feedback.value = result.feedback ?? t('session.feedback.failed')
  }
  statusText.value = ''
}

async function onRunLab() {
  running.value = true
  feedback.value = ''
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
      feedback.value = result.passed
        ? t('session.feedback.passed')
        : result.feedback ?? t('session.feedback.failed')
      if (result.passed) {
        emit('completed')
      }
    }
  } catch {
    stopPolling()
    running.value = false
    statusText.value = ''
    feedback.value = t('session.errors.actionFailed')
  }
}
</script>

<template>
  <div class="space-y-4">
    <p class="text-sm whitespace-pre-wrap">
      {{ instructions }}
    </p>
    <UButton
      :loading="running"
      :disabled="disabled || running"
      @click="onRunLab"
    >
      {{ t('session.lab.run') }}
    </UButton>
    <p v-if="statusText" class="text-sm text-muted">
      {{ statusText }}
    </p>
    <p
      v-if="feedback"
      class="text-sm"
      :class="feedback === t('session.feedback.passed') ? 'text-green-600' : 'text-red-600'"
    >
      {{ feedback }}
    </p>
  </div>
</template>
