<script setup lang="ts">
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ArrowRightIcon,
  CheckIcon,
  ChevronLeftIcon,
  ForwardIcon,
  PlayIcon,
} from '@heroicons/vue/24/outline'

import type { OutlineTopic, StepNavTarget } from '~/composables/useSessions'
import { useSessionGradeSubmit } from '~/composables/useSessionGradeSubmit'
import {
  canAdvanceToNext,
  expectedChoiceIndex,
  hasRichStudyBody as contentHasRichStudyBody,
  isCurrentLesson as matchCurrentLesson,
  isLessonDone as lessonIsDone,
  isStepPassedLocally,
  isTopicComplete,
  labInstructionsFromContent,
  moduleDoneCount,
  outlineTopicsCompleted,
  quizChoicesFromContent,
  quizQuestionFromContent,
  resolveStepVideoPoster,
  resolveStepVideoSrc,
  sessionFeedbackMessage,
  stepKindMark,
  stepNeedsPassToAdvance,
  taskRubricFromContent,
} from '~/utils/session'

const route = useRoute()
const { t, te } = useI18n()

function lessonKindMark(kind: string) {
  return stepKindMark(kind, t, te)
}
const config = useRuntimeConfig()
const { settings, fetchMe } = useAuth()
const { getSession, getStep, navigate, skipStudy, submit } = useSessions()

const sessionId = computed(() => String(route.params.id))
const session = ref<Awaited<ReturnType<typeof getSession>> | null>(null)
const step = ref<Awaited<ReturnType<typeof getStep>> | null>(null)
const pending = ref(true)
const codeSource = ref('')
const quizChoice = ref<number | null>(null)
const quizReveal = ref<{ passed: boolean; expectedIndex: number | null } | null>(null)

watch(quizChoice, () => {
  // Allow retry after a wrong answer without revealing the key.
  if (quizReveal.value && !quizReveal.value.passed) {
    quizReveal.value = null
  }
})
const codeReveal = ref<{ passed: boolean; feedback: string | null; gradable: boolean } | null>(null)
const taskText = ref('')
const taskReveal = ref<{ passed: boolean; feedback: string | null; gradable: boolean } | null>(null)
const toasts = useToasts()
const loadFailed = ref(false)
const { warmupCursor } = useTutor()
const warmedSessions = new Set<string>()

const mediaBase = computed(() => String(config.public.apiBase).replace(/\/$/, ''))

function kickoffCursorWarmup(id: string) {
  if (warmedSessions.has(id)) {
    return
  }
  warmedSessions.add(id)

  void warmupCursor(id).catch(() => {
    warmedSessions.delete(id)
  })
}

watch(codeSource, () => {
  if (codeReveal.value) {
    codeReveal.value = null
  }
})

watch(taskText, () => {
  if (taskReveal.value) {
    taskReveal.value = null
  }
})

async function reload() {
  session.value = await getSession(sessionId.value)
  step.value = await getStep(sessionId.value)
  if (step.value?.editor?.template && !codeSource.value) {
    codeSource.value = step.value.editor.template
  }
}

const { actionPending, notifyResult, runGradeSubmit } = useSessionGradeSubmit({
  t,
  toasts,
  reload,
  sessionStatus: () => session.value?.status,
})

onMounted(async () => {
  try {
    await fetchMe()
    await reload()
    kickoffCursorWarmup(sessionId.value)
  } catch {
    loadFailed.value = true
    toasts.error(t('session.errors.loadFailed'))
  } finally {
    pending.value = false
  }
})

async function goToTarget(
  target: StepNavTarget | null | undefined,
  options: { completeCurrent?: boolean } = {},
) {
  if (!target) {
    return
  }
  actionPending.value = true
  try {
    await navigate(sessionId.value, {
      topic: target.topic,
      phase: target.phase,
      step: target.step,
      complete_current: Boolean(options.completeCurrent),
    })
    codeSource.value = ''
    quizChoice.value = null
    quizReveal.value = null
    codeReveal.value = null
    taskText.value = ''
    taskReveal.value = null
    await reload()
  } catch (error: unknown) {
    const statusCode =
      typeof error === 'object' && error !== null && 'statusCode' in error
        ? Number((error as { statusCode: number }).statusCode)
        : 0
    if (statusCode === 403) {
      toasts.error(t('session.passToContinue'))
    } else {
      toasts.error(t('session.errors.actionFailed'))
    }
  } finally {
    actionPending.value = false
  }
}

async function goNext() {
  await goToTarget(step.value?.next_step, { completeCurrent: true })
}

async function goPrev() {
  await goToTarget(step.value?.prev_step)
}

async function onSkipStudy() {
  actionPending.value = true
  try {
    await skipStudy(sessionId.value)
    codeSource.value = ''
    await reload()
  } catch {
    toasts.error(t('session.errors.actionFailed'))
  } finally {
    actionPending.value = false
  }
}

async function onSubmitQuiz() {
  if (quizChoice.value === null) {
    return
  }
  await runGradeSubmit(async () => {
    const result = await submit(sessionId.value, { choice_index: quizChoice.value })
    quizReveal.value = {
      passed: result.passed,
      expectedIndex: expectedChoiceIndex(result.details),
    }
    notifyResult(result)
  })
}

async function onSubmitCode() {
  await runGradeSubmit(async () => {
    const result = await submit(sessionId.value, { source: codeSource.value })
    codeReveal.value = {
      passed: result.passed,
      feedback: sessionFeedbackMessage(result, t),
      gradable: result.details?.gradable !== false,
    }
    notifyResult(result)
  })
}

async function onSubmitTask() {
  await runGradeSubmit(async () => {
    const result = await submit(sessionId.value, { text: taskText.value })
    taskReveal.value = {
      passed: result.passed,
      feedback: sessionFeedbackMessage(result, t),
      gradable: result.details?.gradable !== false,
    }
    notifyResult(result)
  })
}

const editorLanguage = computed(() => {
  const runtime = step.value?.editor?.runtime
  return typeof runtime === 'string' ? runtime : 'python'
})

const codeTemplate = computed(() => {
  const template = step.value?.editor?.template
  return typeof template === 'string' ? template : ''
})

const taskRubric = computed(() => taskRubricFromContent(step.value?.content ?? null))

function resetCodeTemplate() {
  if (actionPending.value) {
    return
  }
  codeSource.value = codeTemplate.value
  codeReveal.value = null
}

const videoSrc = computed(() => resolveStepVideoSrc(step.value?.content ?? null, mediaBase.value))

const videoPoster = computed(() =>
  resolveStepVideoPoster(step.value?.content ?? null, mediaBase.value),
)

const quizQuestion = computed(() => quizQuestionFromContent(step.value?.content ?? null))
const quizChoices = computed(() => quizChoicesFromContent(step.value?.content ?? null))
const hasRichStudyBody = computed(() => contentHasRichStudyBody(step.value?.content ?? null))
const labInstructions = computed(() =>
  labInstructionsFromContent(step.value?.content ?? null, hasRichStudyBody.value),
)
const stepContent = computed(() => step.value?.content ?? null)

const pageTitle = computed(() => session.value?.pack_title ?? t('session.loading'))
useAppPageTitle(pageTitle)
const phaseLabel = computed(() => {
  const phase = step.value?.phase
  if (!phase) {
    return undefined
  }
  const key = `session.phase.${phase}`
  return te(key) ? t(key) : phase
})
const kindLabel = computed(() => {
  const kind = step.value?.kind
  if (!kind) {
    return ''
  }
  const key = `session.kind.${kind}`
  return te(key) ? t(key) : kind
})

const isStudyStep = computed(
  () => session.value?.current_phase === 'study' && (step.value?.kind === 'theory' || step.value?.kind === 'video'),
)

const outline = computed((): OutlineTopic[] => session.value?.outline ?? [])

const phaseProgress = computed(() => session.value?.phase_progress ?? [])

const topicsCompleted = computed(() =>
  outlineTopicsCompleted(
    outline.value,
    phaseProgress.value,
    passedStepIds.value,
    completedStepIds.value,
  ),
)

const passedStepIds = computed(() => new Set(session.value?.passed_step_ids ?? []))
const completedStepIds = computed(() => new Set(session.value?.completed_step_ids ?? []))

const requirePassToAdvance = computed(
  () => session.value?.policies.require_pass_to_advance !== false,
)

const currentStepPassed = computed(() =>
  isStepPassedLocally({
    stepId: step.value?.step_id,
    kind: step.value?.kind,
    passedStepIds: passedStepIds.value,
    quizReveal: quizReveal.value,
    codeReveal: codeReveal.value,
    taskReveal: taskReveal.value,
  }),
)

const needsPassToAdvance = computed(() =>
  stepNeedsPassToAdvance(requirePassToAdvance.value, step.value?.kind),
)

const canGoNext = computed(() =>
  canAdvanceToNext({
    hasNext: Boolean(step.value?.next_step),
    needsPass: needsPassToAdvance.value,
    passed: currentStepPassed.value,
  }),
)

const tutorMode = computed(() => step.value?.tutor?.mode ?? 'chat')
const showAssistant = computed(
  () => Boolean(step.value?.tutor?.enabled || session.value?.policies.tutor_enabled),
)

function topicComplete(topic: OutlineTopic) {
  return isTopicComplete(
    topic,
    phaseProgress.value,
    passedStepIds.value,
    completedStepIds.value,
  )
}

function moduleDone(topic: OutlineTopic) {
  return moduleDoneCount(topic, passedStepIds.value, completedStepIds.value)
}

function isLessonDone(lesson: OutlineTopic['steps'][number]) {
  return lessonIsDone(lesson, passedStepIds.value, completedStepIds.value)
}

function isCurrentLesson(topicId: string, stepId: string) {
  return matchCurrentLesson(
    session.value?.current_topic_id,
    session.value?.current_step_id,
    topicId,
    stepId,
  )
}
</script>

<template>
  <PageShell :title="pageTitle" :meta="phaseLabel" fill preserve-title-case>
    <div class="session-topbar">
      <NuxtLink class="link-back" to="/catalog">
        <ChevronLeftIcon class="icon-sm" />
        {{ t('session.back') }}
      </NuxtLink>
    </div>

    <div v-if="pending" class="loading-state">
      <span class="loading-spinner" aria-hidden="true" />
      <span>{{ t('session.loading') }}</span>
    </div>

    <div v-else-if="loadFailed" class="empty-state">
      <p class="empty-state-title">{{ t('session.errors.loadFailed') }}</p>
    </div>

    <div
      v-else-if="session && step"
      class="session-workspace"
      data-program
      :data-assistant="showAssistant || undefined"
    >
      <aside class="session-syllabus" :aria-label="t('session.program')">
        <h2 class="session-syllabus-title">
          {{ t('session.program') }}
          <span v-if="outline.length" class="session-syllabus-progress">
            {{ topicsCompleted }} / {{ outline.length }}
          </span>
        </h2>
        <div class="stepik-program session-program">
          <article
            v-for="topic in outline"
            :key="topic.topic_id"
            class="stepik-module"
            :data-current="topic.topic_id === session.current_topic_id || undefined"
          >
            <header class="stepik-module-header">
              <h3 class="stepik-module-title">
                {{ topic.index }}. {{ topic.title }}
              </h3>
              <span class="stepik-module-progress" :aria-label="topicComplete(topic) ? t('session.topicDone') : undefined">
                <span
                  class="stepik-progress-dot"
                  :data-done="topicComplete(topic) || undefined"
                  aria-hidden="true"
                />
                {{ moduleDone(topic) }} / {{ topic.steps.length }}
              </span>
            </header>
            <ul class="stepik-lesson-list">
              <li
                v-for="lesson in topic.steps"
                :key="lesson.step_id"
                class="stepik-lesson"
                :data-current="isCurrentLesson(topic.topic_id, lesson.step_id) || undefined"
                :data-done="isLessonDone(lesson) || undefined"
              >
                <button
                  class="stepik-lesson-button"
                  type="button"
                  :disabled="actionPending"
                  @click="goToTarget({ topic: lesson.topic_id, phase: lesson.phase, step: lesson.step_id })"
                >
                  <span class="stepik-lesson-mark" aria-hidden="true">
                    {{ lessonKindMark(lesson.kind) }}
                  </span>
                  <span class="stepik-lesson-title">
                    {{ lesson.index_label }} {{ lesson.title }}
                  </span>
                </button>
              </li>
            </ul>
          </article>
        </div>
        </aside>

      <section class="session-main">
        <div class="session-lesson-host">
          <Transition name="page-cyber" mode="out-in">
        <article
          :key="step.step_id"
          class="session-lesson"
          :class="[
            `session-lesson-${step.kind}`,
            step.kind === 'video' ? 'session-lesson-video' : '',
            step.kind === 'code' ? 'session-lesson-code' : '',
          ]"
        >
          <header class="session-lesson-header">
            <span class="session-kind-badge">{{ kindLabel }}</span>
            <h2 class="session-lesson-title">{{ step.title }}</h2>
          </header>

          <div class="session-lesson-body">
            <div v-if="step.kind === 'theory'" class="session-step-stack">
              <SessionStudyBody :content="stepContent" />
            </div>

            <div v-else-if="step.kind === 'video'" class="session-step-stack session-step-video">
              <SessionVideoPlayer
                v-if="videoSrc"
                :src="videoSrc"
                :title="step.title"
                :poster="videoPoster || undefined"
              />
              <p v-else class="session-inline-meta">{{ t('session.videoUnavailable') }}</p>
              <SessionStudyBody :content="stepContent" :title="step.title" compact />
            </div>

            <div v-else-if="step.kind === 'code'" class="session-step-stack session-step-code">
              <div class="session-code-statement">
                <SessionStudyBody :content="stepContent" />
              </div>
              <div
                class="session-code-shell"
                :data-result="
                  codeReveal
                    ? codeReveal.gradable === false
                      ? 'ungradable'
                      : codeReveal.passed
                        ? 'pass'
                        : 'fail'
                    : undefined
                "
              >
                <div class="session-code-toolbar">
                  <span class="session-code-lang">{{ editorLanguage }}</span>
                  <button
                    class="btn-ghost btn-sm session-code-reset"
                    type="button"
                    :disabled="actionPending || !codeTemplate"
                    :title="t('session.resetCode')"
                    @click="resetCodeTemplate"
                  >
                    <ArrowPathIcon class="icon-sm" />
                    {{ t('session.resetCode') }}
                  </button>
                </div>
                <div class="session-code-editor-host">
                  <ClientOnly>
                    <SessionCodeEditor
                      v-model="codeSource"
                      :language="editorLanguage"
                      :session-id="sessionId"
                      :phase="session.current_phase"
                      :pack-autocomplete="session.policies.assess_autocomplete"
                      :lsp-id="step.editor?.lsp"
                      :editor-settings="settings"
                    />
                  </ClientOnly>
                </div>
                <p
                  v-if="codeReveal"
                  class="session-feedback"
                  :class="
                    codeReveal.gradable === false
                      ? 'session-feedback-meta'
                      : codeReveal.passed
                        ? 'session-feedback-pass'
                        : 'session-feedback-fail'
                  "
                >
                  {{ codeReveal.feedback }}
                </p>
              </div>
            </div>

            <div v-else-if="step.kind === 'lab'" class="session-step-stack">
              <SessionStudyBody :content="stepContent" />
              <SessionLabPanel
                :session-id="sessionId"
                :instructions="labInstructions"
                :disabled="actionPending"
                @completed="reload"
              />
            </div>

            <div v-else-if="step.kind === 'quiz'" class="session-step-stack">
              <SessionStudyBody v-if="hasRichStudyBody" :content="stepContent" />
              <SessionQuiz
                v-model="quizChoice"
                :question="hasRichStudyBody ? '' : quizQuestion"
                :choices="quizChoices"
                :disabled="actionPending"
                :reveal="quizReveal"
              />
              <p v-if="!quizChoices.length" class="session-inline-meta">
                {{ t('session.quizOptionsUnavailable') }}
              </p>
            </div>

            <div v-else-if="step.kind === 'task'" class="session-step-stack session-step-task">
              <SessionStudyBody :content="stepContent" />
              <p v-if="taskRubric" class="session-inline-meta session-task-rubric">
                {{ taskRubric }}
              </p>
              <label class="session-task-label" :for="`task-answer-${step.step_id}`">
                {{ t('session.taskAnswer') }}
              </label>
              <textarea
                :id="`task-answer-${step.step_id}`"
                v-model="taskText"
                class="session-task-input"
                rows="10"
                :disabled="actionPending"
                :placeholder="t('session.taskPlaceholder')"
              />
              <p
                v-if="taskReveal"
                class="session-feedback"
                :class="
                  taskReveal.gradable === false
                    ? 'session-feedback-meta'
                    : taskReveal.passed
                      ? 'session-feedback-pass'
                      : 'session-feedback-fail'
                "
              >
                {{ taskReveal.feedback }}
              </p>
            </div>
          </div>
        </article>
          </Transition>
        </div>

        <footer class="session-actionbar">
          <div class="session-actionbar-row">
            <button
              class="session-nav-btn session-nav-btn-ghost"
              type="button"
              :disabled="actionPending || !step.prev_step"
              @click="goPrev"
            >
              <ArrowLeftIcon class="icon-sm session-nav-icon" />
              {{ t('session.prevStep') }}
            </button>

            <div class="session-actionbar-center">
              <button
                v-if="isStudyStep && session.policies.skip_study_allowed"
                class="session-nav-btn session-nav-btn-ghost"
                type="button"
                :disabled="actionPending"
                @click="onSkipStudy"
              >
                <ForwardIcon class="icon-sm session-nav-icon" />
                {{ t('session.skipStudy') }}
              </button>
              <button
                v-if="step.kind === 'quiz'"
                class="session-nav-btn session-nav-btn-primary"
                type="button"
                :disabled="actionPending || quizChoice === null || !quizChoices.length || quizReveal?.passed === true"
                @click="onSubmitQuiz"
              >
                <CheckIcon class="icon-sm session-nav-icon" />
                {{ t('session.submitAnswer') }}
              </button>
              <button
                v-else-if="step.kind === 'code'"
                class="session-nav-btn session-nav-btn-primary"
                type="button"
                :disabled="actionPending"
                @click="onSubmitCode"
              >
                <PlayIcon class="icon-sm session-nav-icon" />
                {{ t('session.runCode') }}
              </button>
              <button
                v-else-if="step.kind === 'task'"
                class="session-nav-btn session-nav-btn-primary"
                type="button"
                :disabled="actionPending || !taskText.trim()"
                @click="onSubmitTask"
              >
                <CheckIcon class="icon-sm session-nav-icon" />
                {{ t('session.submitAnswer') }}
              </button>
            </div>

            <button
              class="session-nav-btn session-nav-btn-primary"
              type="button"
              :disabled="actionPending || !canGoNext"
              :title="needsPassToAdvance && !currentStepPassed ? t('session.passToContinue') : undefined"
              @click="goNext"
            >
              {{ t('session.nextStep') }}
              <ArrowRightIcon class="icon-sm session-nav-icon" />
            </button>
          </div>
        </footer>
      </section>

      <aside
        v-if="showAssistant"
        class="session-assistant"
        :aria-label="t('tutor.dockTitle')"
      >
        <SessionTutorPanel
          :session-id="sessionId"
          :step-id="step.step_id"
          :step-kind="step.kind"
          :mode="tutorMode"
          docked
        />
      </aside>
    </div>
  </PageShell>
</template>
