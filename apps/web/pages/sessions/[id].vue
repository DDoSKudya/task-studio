<script setup lang="ts">
const route = useRoute()
const { t } = useI18n()
const { getSession, getStep, navigate, skipStudy, submit } = useSessions()

const sessionId = computed(() => String(route.params.id))
const session = ref<Awaited<ReturnType<typeof getSession>> | null>(null)
const step = ref<Awaited<ReturnType<typeof getStep>> | null>(null)
const pending = ref(true)
const actionPending = ref(false)
const errorMessage = ref('')
const feedback = ref('')
const codeSource = ref('')
const quizChoice = ref<number | null>(null)

async function reload() {
  session.value = await getSession(sessionId.value)
  step.value = await getStep(sessionId.value)
  if (step.value?.editor?.template && !codeSource.value) {
    codeSource.value = step.value.editor.template
  }
}

onMounted(async () => {
  try {
    await reload()
  } catch {
    errorMessage.value = t('session.errors.loadFailed')
  } finally {
    pending.value = false
  }
})

async function goToPractice() {
  if (!session.value || !step.value?.transitions.practice) {
    return
  }
  actionPending.value = true
  errorMessage.value = ''
  try {
    await navigate(sessionId.value, {
      topic: session.value.current_topic_id,
      phase: 'practice',
      step: step.value.transitions.practice,
    })
    codeSource.value = ''
    quizChoice.value = null
    feedback.value = ''
    await reload()
  } catch {
    errorMessage.value = t('session.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function goToAssess() {
  if (!session.value || !step.value?.transitions.assess) {
    return
  }
  actionPending.value = true
  errorMessage.value = ''
  try {
    await navigate(sessionId.value, {
      topic: session.value.current_topic_id,
      phase: 'assess',
      step: step.value.transitions.assess,
    })
    quizChoice.value = null
    feedback.value = ''
    await reload()
  } catch {
    errorMessage.value = t('session.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onSkipStudy() {
  actionPending.value = true
  errorMessage.value = ''
  try {
    await skipStudy(sessionId.value)
    codeSource.value = ''
    await reload()
  } catch {
    errorMessage.value = t('session.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onSubmitCode() {
  actionPending.value = true
  errorMessage.value = ''
  feedback.value = ''
  try {
    const result = await submit(sessionId.value, { source: codeSource.value })
    feedback.value = result.passed
      ? t('session.feedback.passed')
      : result.feedback ?? t('session.feedback.failed')
    await reload()
    if (result.passed) {
      await goToAssess()
    }
  } catch {
    errorMessage.value = t('session.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onSubmitQuiz() {
  if (quizChoice.value === null) {
    return
  }
  actionPending.value = true
  errorMessage.value = ''
  feedback.value = ''
  try {
    const result = await submit(sessionId.value, { choice_index: quizChoice.value })
    feedback.value = result.passed
      ? t('session.feedback.passed')
      : result.feedback ?? t('session.feedback.failed')
    await reload()
  } catch {
    errorMessage.value = t('session.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

const theoryContent = computed(() => {
  const content = step.value?.content.content
  return typeof content === 'string' ? content : ''
})

const quizQuestion = computed(() => {
  const question = step.value?.content.question
  return typeof question === 'string' ? question : ''
})

const quizChoices = computed(() => {
  const choices = step.value?.content.choices
  return Array.isArray(choices)
    ? choices.filter((item): item is string => typeof item === 'string')
    : []
})
</script>

<template>
  <UContainer class="py-8 space-y-6">
    <NuxtLink
      class="text-sm text-primary"
      to="/catalog"
    >
      {{ t('session.back') }}
    </NuxtLink>

    <p
      v-if="pending"
      class="text-sm text-muted"
    >
      {{ t('session.loading') }}
    </p>

    <p
      v-else-if="errorMessage"
      class="text-sm text-red-600"
    >
      {{ errorMessage }}
    </p>

    <template v-else-if="session && step">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">
          {{ session.pack_title }}
        </h1>
        <p class="text-sm text-muted">
          {{ step.topic_id }} · {{ step.phase }} · {{ step.step_id }}
        </p>
      </div>

      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ step.title }}
          </h2>
        </template>

        <div
          v-if="step.kind === 'theory'"
          class="space-y-4"
        >
          <p class="text-sm whitespace-pre-wrap">
            {{ theoryContent }}
          </p>
          <div class="flex flex-wrap gap-2">
            <UButton
              :loading="actionPending"
              @click="goToPractice"
            >
              {{ t('session.continuePractice') }}
            </UButton>
            <UButton
              v-if="session.policies.skip_study_allowed"
              variant="outline"
              :loading="actionPending"
              @click="onSkipStudy"
            >
              {{ t('session.skipStudy') }}
            </UButton>
          </div>
        </div>

        <div
          v-else-if="step.kind === 'code'"
          class="space-y-4"
        >
          <ClientOnly>
            <SessionCodeEditor
              v-model="codeSource"
              language="python"
            />
          </ClientOnly>
          <UButton
            :loading="actionPending"
            @click="onSubmitCode"
          >
            {{ t('session.runCode') }}
          </UButton>
        </div>

        <div
          v-else-if="step.kind === 'quiz'"
          class="space-y-4"
        >
          <SessionQuiz
            v-model="quizChoice"
            :question="quizQuestion"
            :choices="quizChoices"
            :disabled="actionPending"
          />
          <UButton
            :loading="actionPending"
            :disabled="quizChoice === null"
            @click="onSubmitQuiz"
          >
            {{ t('session.submitAnswer') }}
          </UButton>
        </div>
      </UCard>

      <p
        v-if="feedback"
        class="text-sm"
        :class="feedback === t('session.feedback.passed') ? 'text-green-600' : 'text-red-600'"
      >
        {{ feedback }}
      </p>

      <p
        v-if="session.status === 'completed'"
        class="text-sm text-green-700"
      >
        {{ t('session.completed') }}
      </p>
    </template>
  </UContainer>
</template>
