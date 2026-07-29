<script setup lang="ts">
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  AcademicCapIcon,
  QuestionMarkCircleIcon,
  CodeBracketIcon,
  CubeIcon,
} from '@heroicons/vue/24/outline'
import type { CourseStageEvent, CourseStageName } from '~/composables/useStudio'

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
}>()

const { t } = useI18n()

const visible = computed(() => props.active || props.done || Boolean(props.error))

const STAGES: Array<{ id: CourseStageName; icon: unknown }> = [
  { id: 'analyze', icon: DocumentTextIcon },
  { id: 'theory', icon: AcademicCapIcon },
  { id: 'quizzes', icon: QuestionMarkCircleIcon },
  { id: 'code', icon: CodeBracketIcon },
  { id: 'assemble', icon: CubeIcon },
]

const percent = computed(() => {
  if (props.error) {
    return 0
  }
  return Math.round(Math.min(100, Math.max(0, props.progress * 100)))
})

const elapsedLabel = computed(() => {
  const totalSec = Math.floor(props.elapsedMs / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
})

const stageStates = computed(() => {
  const map: Record<string, 'pending' | 'running' | 'done' | 'error'> = {}
  for (const stage of STAGES) {
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
  const order = STAGES.map((s) => s.id)
  const currentIdx = order.indexOf(props.currentStage as CourseStageName)
  const idx = order.indexOf(id)
  if (idx < 0) {
    return 'pending'
  }
  if (props.currentStage === id) {
    const last = [...props.log].reverse().find((e) => e.stage === id)
    if (last?.status === 'done') {
      return 'done'
    }
    return 'running'
  }
  if (currentIdx > idx) {
    return 'done'
  }
  return 'pending'
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
      <div>
        <h3 class="course-progress-title">
          {{ error ? t('editor.progressFailed') : done ? t('editor.progressDone') : t('editor.progressTitle') }}
        </h3>
        <p class="course-progress-message">{{ error || message }}</p>
      </div>
      <div class="course-progress-meta">
        <span class="course-progress-percent">{{ percent }}%</span>
        <span class="course-progress-elapsed">{{ elapsedLabel }}</span>
      </div>
    </header>

    <div
      class="course-progress-bar"
      role="progressbar"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div class="course-progress-bar-fill" :style="{ width: `${percent}%` }" />
    </div>

    <ol class="course-progress-stages">
      <li
        v-for="stage in STAGES"
        :key="stage.id"
        class="course-progress-stage"
        :data-state="stageStates[stage.id]"
      >
        <span class="course-progress-stage-icon" aria-hidden="true">
          <CheckCircleIcon v-if="stageStates[stage.id] === 'done'" class="icon-sm" />
          <ExclamationTriangleIcon v-else-if="stageStates[stage.id] === 'error'" class="icon-sm" />
          <component :is="stage.icon" v-else class="icon-sm" />
        </span>
        <span class="course-progress-stage-label">{{ t(`editor.stages.${stage.id}`) }}</span>
        <span v-if="stageStates[stage.id] === 'running'" class="course-progress-pulse" aria-hidden="true" />
      </li>
    </ol>

    <div class="course-progress-grid">
      <div v-if="outcomes.length" class="course-progress-card">
        <h4>{{ t('editor.progressOutcomes') }}</h4>
        <ul>
          <li v-for="(item, i) in outcomes" :key="`o-${i}`">{{ item }}</li>
        </ul>
      </div>
      <div v-if="chapters.length" class="course-progress-card">
        <h4>{{ t('editor.progressChapters') }}</h4>
        <ul>
          <li v-for="(item, i) in chapters" :key="`c-${i}`">{{ chapterLabel(item) }}</li>
        </ul>
      </div>
      <div v-if="quizzes.length" class="course-progress-card">
        <h4>{{ t('editor.progressQuizzes') }}</h4>
        <ul>
          <li v-for="(item, i) in quizzes" :key="`q-${i}`">
            {{ String(item.title || item.id || `quiz-${i + 1}`) }}
            <span v-if="item.question" class="course-progress-sub">{{ String(item.question) }}</span>
          </li>
        </ul>
      </div>
      <div v-if="tasks.length" class="course-progress-card">
        <h4>{{ t('editor.progressTasks') }}</h4>
        <ul>
          <li v-for="(item, i) in tasks" :key="`t-${i}`">
            {{ String(item.title || item.id || `task-${i + 1}`) }}
            <span v-if="item.tests != null" class="course-progress-sub">
              {{ t('editor.progressTests', { count: Number(item.tests) || 0 }) }}
            </span>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="warnings.length" class="course-progress-warnings">
      <h4>{{ t('editor.courseWarnings') }}</h4>
      <ul>
        <li v-for="(item, i) in warnings" :key="`w-${i}`">{{ item }}</li>
      </ul>
    </div>

    <details v-if="log.length" class="course-progress-log">
      <summary>{{ t('editor.progressLog') }} ({{ log.length }})</summary>
      <ul>
        <li v-for="(event, i) in log" :key="`l-${i}`">
          <span class="course-progress-log-stage">{{ event.stage }}</span>
          <span class="course-progress-log-status">{{ event.status }}</span>
          <span>{{ event.message }}</span>
          <span v-if="event.index && event.total" class="course-progress-sub">
            {{ event.index }}/{{ event.total }}
          </span>
        </li>
      </ul>
    </details>
  </section>
</template>
