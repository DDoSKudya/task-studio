<script setup lang="ts">
import {
  CheckIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  AcademicCapIcon,
  PencilSquareIcon,
  QueueListIcon,
  CodeBracketIcon,
  CubeIcon,
  ScaleIcon,
} from '@heroicons/vue/24/outline'
import type { CourseStageEvent, CourseStageName } from '~/composables/useStudio'
import { localizeCourseProgressMessage, localizeCourseWarning, localizeCourseError } from '~/utils/studio'

const props = defineProps<{
  active: boolean
  progress: number
  currentStage: CourseStageName | string
  message: string
  elapsedMs: number
  log: CourseStageEvent[]
  outcomes: string[]
  chapters: Array<{ id?: string; title?: string } | string>
  quizzes: Array<{ id?: unknown; title?: unknown; question?: unknown }>
  tasks: Array<{ id?: unknown; title?: unknown; tests?: unknown }>
  warnings: string[]
  error: string
  done: boolean
  showConsistency?: boolean

  enabledStages?: Array<
    'analyze' | 'theory' | 'polish' | 'quizzes' | 'code' | 'assemble' | 'consistency'
  >

  compact?: boolean
}>()

const { t } = useI18n()

const displayMessage = computed(() => {
  if (props.error) {
    return localizeCourseError(props.error, t)
  }
  return localizeCourseProgressMessage({ message: props.message }, t)
})

const displayWarnings = computed(() =>
  props.warnings.map((item) => localizeCourseWarning(item, t)),
)

const STAGES = computed(() => {
  const all: Array<{ id: CourseStageName; icon: unknown }> = [
    { id: 'consistency', icon: ScaleIcon },
    { id: 'analyze', icon: DocumentTextIcon },
    { id: 'theory', icon: AcademicCapIcon },
    { id: 'polish', icon: PencilSquareIcon },
    { id: 'quizzes', icon: QueueListIcon },
    { id: 'code', icon: CodeBracketIcon },
    { id: 'assemble', icon: CubeIcon },
  ]
  const enabled = new Set<string>(
    props.enabledStages ?? ['analyze', 'theory', 'polish', 'quizzes', 'code', 'assemble'],
  )
  if (props.showConsistency) {
    enabled.add('consistency')
  } else {
    enabled.delete('consistency')
  }
  return all.filter((stage) => enabled.has(stage.id))
})

const visible = computed(() => props.active || props.done || Boolean(props.error))


const activeStep = computed(() => {
  for (let i = props.log.length - 1; i >= 0; i -= 1) {
    const event = props.log[i]
    if (!event || event.stage !== props.currentStage) {
      continue
    }
    if (typeof event.index !== 'number' || typeof event.total !== 'number' || event.total <= 0) {
      continue
    }
    const titleRaw = event.message_params?.title ?? event.detail?.chapter_title
    const title = typeof titleRaw === 'string' ? titleRaw.trim() : ''
    return {
      index: event.index,
      total: event.total,
      title,
    }
  }
  return null
})


const displayProgress = computed(() => {
  if (props.error) {
    return 0
  }
  if (props.done || props.progress >= 0.999 || props.currentStage === 'done') {
    return 1
  }
  const backend = Math.min(1, Math.max(0, props.progress))
  const order = STAGES.value.map((stage) => stage.id)
  if (!order.length) {
    return backend
  }
  const currentIdx = order.indexOf(props.currentStage as CourseStageName)
  if (currentIdx < 0) {
    return backend
  }
  const weight = 1 / order.length
  let estimated = currentIdx * weight
  const step = activeStep.value
  if (step && step.total > 0 && props.currentStage === order[currentIdx]) {
    estimated += Math.min(1, Math.max(0, step.index / step.total)) * weight
  } else {
    estimated += 0.12 * weight
  }
  return Math.min(0.99, Math.max(backend, estimated))
})

const percent = computed(() => Math.round(displayProgress.value * 100))

const elapsedLabel = computed(() => {
  const totalSec = Math.floor(props.elapsedMs / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
})

const stageStates = computed(() => {
  const map: Record<string, 'pending' | 'running' | 'done' | 'error'> = {}
  for (const stage of STAGES.value) {
    map[stage.id] = resolveStageState(stage.id)
  }
  return map
})

function resolveStageState(id: CourseStageName): 'pending' | 'running' | 'done' | 'error' {
  if (props.error && props.currentStage === id) {
    return 'error'
  }
  if (props.done && !props.error) {
    return 'done'
  }
  const order = STAGES.value.map((s) => s.id)
  const currentIdx = order.indexOf(props.currentStage as CourseStageName)
  const idx = order.indexOf(id)
  if (idx < 0) {
    return 'pending'
  }
  if (props.currentStage === id) {
    const last = [...props.log].reverse().find((e) => e.stage === id)
    if (last?.status === 'done' || last?.status === 'needs_confirmation') {
      return last.status === 'needs_confirmation' ? 'running' : 'done'
    }
    return 'running'
  }
  if (currentIdx > idx) {
    return 'done'
  }
  return 'pending'
}

function stageFillPercent(
  state: 'pending' | 'running' | 'done' | 'error' | undefined,
  stageId: string,
): string {
  if (state === 'done' || state === 'error') {
    return '100%'
  }
  if (state === 'running') {
    const step = activeStep.value
    if (step && props.currentStage === stageId && step.total > 0) {
      const ratio = Math.min(1, Math.max(0, step.index / step.total))
      return `${Math.round(ratio * 100)}%`
    }

    return '22%'
  }
  return '0%'
}

function chapterLabel(item: { id?: string; title?: string } | string): string {
  if (typeof item === 'string') {
    return item
  }
  return item.title || item.id || '—'
}
</script>

<template>
  <section
    v-if="visible"
    class="course-progress"
    :class="{
      'is-running': active && !done && !error,
      'is-done': done && !error,
      'is-error': Boolean(error),
    }"
    aria-live="polite"
  >
    <header class="course-progress-header">
      <div class="course-progress-copy">
        <h3 class="course-progress-title">
          {{ error ? t('courseBuild.progressFailed') : done ? t('courseBuild.progressDone') : t('courseBuild.progressTitle') }}
        </h3>
        <p class="course-progress-message">{{ displayMessage }}</p>
        <div
          v-if="activeStep && active && !done && !error"
          class="course-progress-step"
        >
          <span class="course-progress-step-count">
            {{ activeStep.index }}
            <span class="course-progress-step-sep" aria-hidden="true">/</span>
            {{ activeStep.total }}
          </span>
          <span v-if="activeStep.title" class="course-progress-step-title">
            {{ activeStep.title }}
          </span>
        </div>
      </div>
      <div class="course-progress-meta">
        <span class="course-progress-percent">{{ percent }}%</span>
        <span class="course-progress-elapsed">{{ elapsedLabel }}</span>
      </div>
    </header>

    <div class="course-progress-bar" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
      <div class="course-progress-bar-fill" :style="{ width: `${percent}%` }" />
    </div>

    <ol class="course-progress-stages" :data-count="STAGES.length">
      <li
        v-for="stage in STAGES"
        :key="stage.id"
        class="course-progress-stage"
        :data-state="stageStates[stage.id]"
      >
        <span
          class="course-progress-stage-fill"
          aria-hidden="true"
          :style="{ width: stageFillPercent(stageStates[stage.id], stage.id) }"
        />
        <span class="course-progress-stage-icon" aria-hidden="true">
          <CheckIcon v-if="stageStates[stage.id] === 'done'" class="icon-sm" />
          <ExclamationTriangleIcon v-else-if="stageStates[stage.id] === 'error'" class="icon-sm" />
          <component :is="stage.icon" v-else class="icon-sm" />
        </span>
        <span class="course-progress-stage-label">{{ t(`courseBuild.stages.${stage.id}`) }}</span>
        <span
          v-if="stageStates[stage.id] === 'running' && activeStep && currentStage === stage.id"
          class="course-progress-stage-count"
          aria-hidden="true"
        >
          {{ activeStep.index }}/{{ activeStep.total }}
        </span>
        <span v-if="stageStates[stage.id] === 'running'" class="course-progress-pulse" aria-hidden="true" />
      </li>
    </ol>

    <template v-if="!compact || done || error">
      <div v-if="!compact" class="course-progress-grid">
        <div v-if="outcomes.length" class="course-progress-card">
          <h4>{{ t('courseBuild.progressOutcomes') }}</h4>
          <ul>
            <li v-for="(item, i) in outcomes" :key="`o-${i}`">{{ item }}</li>
          </ul>
        </div>
        <div v-if="chapters.length" class="course-progress-card">
          <h4>{{ t('courseBuild.progressChapters') }}</h4>
          <ul>
            <li v-for="(item, i) in chapters" :key="`c-${i}`">{{ chapterLabel(item) }}</li>
          </ul>
        </div>
        <div v-if="quizzes.length" class="course-progress-card">
          <h4>{{ t('courseBuild.progressQuizzes') }}</h4>
          <ul>
            <li v-for="(item, i) in quizzes" :key="`q-${i}`">
              {{ String(item.title || item.id || `quiz-${i + 1}`) }}
            </li>
          </ul>
        </div>
        <div v-if="tasks.length" class="course-progress-card">
          <h4>{{ t('courseBuild.progressTasks') }}</h4>
          <ul>
            <li v-for="(item, i) in tasks" :key="`t-${i}`">
              {{ String(item.title || item.id || `task-${i + 1}`) }}
              <span v-if="item.tests != null" class="course-progress-sub">
                {{ t('courseBuild.progressTests', { count: Number(item.tests) || 0 }) }}
              </span>
            </li>
          </ul>
        </div>
      </div>

      <div v-if="displayWarnings.length" class="course-progress-warnings">
        <h4>{{ t('courseBuild.warnings') }}</h4>
        <ul>
          <li v-for="(item, i) in displayWarnings" :key="`w-${i}`">{{ item }}</li>
        </ul>
      </div>
    </template>
  </section>
</template>
