<script setup lang="ts">
import { ArrowRightOnRectangleIcon } from '@heroicons/vue/24/outline'
import type { CourseStageEvent, CourseStageName } from '~/composables/useStudio'
import { localizeCourseProgressMessage, localizeCourseWarning } from '~/utils/studio'

const { t, te } = useI18n()
const { user, fetchMe, logout } = useAuth()
const { validateManifest, buildPack, suggestFragment, streamCourseFromArticle } = useStudio()
const { uploadPack } = useCatalog()
const router = useRouter()

const pending = ref(true)
const actionPending = ref(false)
const errorMessage = ref('')
const validationMessage = ref('')
const uploadMessage = ref('')
const suggestPrompt = ref('')
const articleText = ref('')
const articleTitle = ref('')
const articleAudience = ref('')
const articleLocale = ref('ru')

const courseRunning = ref(false)
const courseDone = ref(false)
const courseError = ref('')
const courseProgress = ref(0)
const courseStage = ref<CourseStageName | string>('analyze')
const courseMessage = ref('')
const courseElapsedMs = ref(0)
const courseLog = ref<CourseStageEvent[]>([])
const courseOutcomes = ref<string[]>([])
const courseChapters = ref<Array<{ id?: string; title?: string } | string>>([])
const courseQuizzes = ref<Array<{ id?: unknown; title?: unknown; question?: unknown }>>([])
const courseTasks = ref<Array<{ id?: unknown; title?: unknown; tests?: unknown }>>([])
const courseWarnings = ref<string[]>([])

let courseTimer: ReturnType<typeof setInterval> | null = null
let courseStartedAt = 0

const manifestText = ref(`{
  "schema_version": 1,
  "id": "my-pack",
  "version": "1.0.0",
  "title": "My Pack",
  "locale": "ru",
  "source": { "type": "local" },
  "defaults": {
    "runtime": "python",
    "runtime_version": "3.12"
  },
  "topics": [
    {
      "id": "topic-1",
      "title": "Intro",
      "phases": {
        "study": { "steps": ["theory-1"] },
        "practice": { "steps": ["code-1"] },
        "assess": { "steps": ["quiz-1"] }
      }
    }
  ],
  "steps": {
    "theory-1": {
      "kind": "theory",
      "title": "Welcome",
      "content": "Replace this with theory or generate a course from an article."
    },
    "code-1": {
      "kind": "code",
      "title": "First task",
      "runtime": "python",
      "runtime_version": "3.12",
      "template": "def solve(x: int) -> int:\\n    return x\\n",
      "tests": [{ "input": [1], "output": 1 }]
    },
    "quiz-1": {
      "kind": "quiz",
      "title": "Check",
      "question": "What is 1 + 1?",
      "choices": ["1", "2", "3", "4"],
      "answer": 1
    }
  },
  "policies": {
    "skip_study_allowed": true,
    "assess_without_practice": false,
    "assess": { "max_attempts": 3, "autocomplete": false },
    "tutor_enabled": true
  }
}`)

onMounted(async () => {
  try {
    await fetchMe()
  } catch {
    await router.push('/login')
    return
  } finally {
    pending.value = false
  }
})

onBeforeUnmount(() => {
  stopCourseTimer()
})

function parseManifest(): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(manifestText.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('not object')
    }
    return parsed as Record<string, unknown>
  } catch {
    throw createError({ statusCode: 422, message: t('editor.errors.invalidJson') })
  }
}

function startCourseTimer() {
  stopCourseTimer()
  courseStartedAt = Date.now()
  courseElapsedMs.value = 0
  courseTimer = setInterval(() => {
    courseElapsedMs.value = Date.now() - courseStartedAt
  }, 250)
}

function stopCourseTimer() {
  if (courseTimer) {
    clearInterval(courseTimer)
    courseTimer = null
  }
}

function resetCourseProgress() {
  courseRunning.value = true
  courseDone.value = false
  courseError.value = ''
  courseProgress.value = 0.02
  courseStage.value = 'analyze'
  courseMessage.value = t('editor.courseWorking')
  courseLog.value = []
  courseOutcomes.value = []
  courseChapters.value = []
  courseQuizzes.value = []
  courseTasks.value = []
  courseWarnings.value = []
  startCourseTimer()
}

function applyCourseEvent(event: CourseStageEvent) {
  courseLog.value = [...courseLog.value, event]
  if (typeof event.progress === 'number') {
    courseProgress.value = Math.max(courseProgress.value, event.progress)
  }
  if (event.stage) {
    courseStage.value = event.stage
  }
  const localized = localizeCourseProgressMessage(event, t, te, 'editor.messages')
  if (localized) {
    courseMessage.value = localized
  }

  const detail = event.detail || {}
  if (Array.isArray(detail.outcomes)) {
    courseOutcomes.value = detail.outcomes.map(String)
  }
  if (Array.isArray(detail.chapters)) {
    courseChapters.value = detail.chapters as Array<{ id?: string; title?: string } | string>
  }
  if (Array.isArray(detail.quizzes)) {
    courseQuizzes.value = detail.quizzes as Array<{ id?: unknown; title?: unknown; question?: unknown }>
  }
  if (Array.isArray(detail.tasks)) {
    courseTasks.value = detail.tasks as Array<{ id?: unknown; title?: unknown; tests?: unknown }>
  }
  if (Array.isArray(detail.warnings)) {
    courseWarnings.value = detail.warnings.map((item: unknown) =>
      localizeCourseWarning(String(item), t, te, 'editor.warningsMap'),
    )
  }

  if (event.type === 'done' && event.meta) {
    if (event.meta.outcomes?.length) {
      courseOutcomes.value = event.meta.outcomes
    }
    if (event.meta.chapters?.length) {
      courseChapters.value = event.meta.chapters
    }
    if (event.meta.warnings?.length) {
      courseWarnings.value = event.meta.warnings
    }
  }

  if (event.type === 'error') {
    courseError.value = event.message || t('editor.errors.courseFailed')
    courseStage.value = 'failed'
  }
}

async function onValidate() {
  actionPending.value = true
  errorMessage.value = ''
  validationMessage.value = ''
  try {
    const manifest = parseManifest()
    const result = await validateManifest(manifest)
    if (result.valid) {
      validationMessage.value = t('editor.valid')
    } else {
      validationMessage.value = result.errors.map((issue) => `${issue.path}: ${issue.message}`).join('\n')
    }
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onBuild() {
  actionPending.value = true
  errorMessage.value = ''
  try {
    const manifest = parseManifest()
    const blob = await buildPack(manifest, [])
    const slug = typeof manifest.id === 'string' ? manifest.id : 'pack'
    const version = typeof manifest.version === 'string' ? manifest.version : '1.0.0'
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${slug}-${version}.studio-pack`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onUpload() {
  actionPending.value = true
  errorMessage.value = ''
  uploadMessage.value = ''
  try {
    const manifest = parseManifest()
    const blob = await buildPack(manifest, [])
    const slug = typeof manifest.id === 'string' ? manifest.id : 'pack'
    const version = typeof manifest.version === 'string' ? manifest.version : '1.0.0'
    const file = new File([blob], `${slug}-${version}.studio-pack`, { type: 'application/zip' })
    const response = await uploadPack(file)
    uploadMessage.value = t('editor.uploaded', { title: response.title, version: response.version })
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onSuggest() {
  if (!suggestPrompt.value.trim()) {
    return
  }
  actionPending.value = true
  errorMessage.value = ''
  try {
    const manifest = parseManifest()
    const result = await suggestFragment({
      context: 'pack authoring',
      step_kind: 'theory',
      prompt: suggestPrompt.value,
      manifest_fragment: manifest,
    })
    manifestText.value = JSON.stringify(result.suggestion, null, 2)
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onCourseFromArticle() {
  if (articleText.value.trim().length < 80) {
    errorMessage.value = t('editor.errors.articleTooShort')
    return
  }
  actionPending.value = true
  errorMessage.value = ''
  resetCourseProgress()
  try {
    const result = await streamCourseFromArticle(
      {
        article: articleText.value,
        title: articleTitle.value.trim() || null,
        audience: articleAudience.value.trim() || null,
        locale: articleLocale.value || 'ru',
        runtime: 'python',
        runtime_version: '3.12',
        quiz_count: 6,
        code_count: 3,
      },
      applyCourseEvent,
    )
    manifestText.value = JSON.stringify(result.manifest, null, 2)
    courseProgress.value = 1
    courseStage.value = 'done'
    courseDone.value = true
    courseMessage.value = t('editor.courseReady', {
      chapters: result.meta.chapters.join(', ') || '—',
    })
    if (result.meta.outcomes.length) {
      courseOutcomes.value = result.meta.outcomes
    }
    if (result.meta.chapters.length) {
      courseChapters.value = result.meta.chapters
    }
    if (result.meta.warnings.length) {
      courseWarnings.value = result.meta.warnings
    }
  } catch (err) {
    courseDone.value = false
    const detail =
      err && typeof err === 'object' && 'message' in err
        ? String((err as { message?: string }).message || '')
        : ''
    courseError.value = detail || t('editor.errors.courseFailed')
    courseMessage.value = courseError.value
    errorMessage.value = courseError.value
  } finally {
    courseRunning.value = false
    stopCourseTimer()
    courseElapsedMs.value = Date.now() - courseStartedAt
    actionPending.value = false
  }
}

function onArticleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    articleText.value = String(reader.result || '')
    if (!articleTitle.value) {
      articleTitle.value = file.name.replace(/\.md$/i, '')
    }
  }
  reader.readAsText(file)
}

async function onLogout() {
  await logout()
  await router.push('/login')
}
</script>

<template>
  <PageShell :title="t('app.title')" :meta="t('app.subtitle')">
    <template #actions>
      <ClientOnly>
        <div v-if="user" style="display: flex; align-items: center; gap: 0.625rem">
          <span class="data-list-meta">{{ user.email }}</span>
          <button class="btn-secondary btn-sm" type="button" @click="onLogout">
            <ArrowRightOnRectangleIcon class="icon-sm" />
            {{ t('auth.logout') }}
          </button>
        </div>
      </ClientOnly>
    </template>

    <div v-if="pending" class="loading-state">
      <span class="loading-spinner" aria-hidden="true" />
      <span>{{ t('editor.loading') }}</span>
    </div>

    <template v-else>
      <div class="form-panel">
        <div class="form-panel-header">
          <h2 class="form-panel-title">{{ t('editor.fromArticle') }}</h2>
          <p class="form-panel-meta">{{ t('editor.fromArticleMeta') }}</p>
        </div>
        <div class="form-panel-body">
          <div style="display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr))">
            <label class="form-field">
              <span class="form-label">{{ t('editor.articleTitle') }}</span>
              <input v-model="articleTitle" class="field" type="text">
            </label>
            <label class="form-field">
              <span class="form-label">{{ t('editor.articleAudience') }}</span>
              <input v-model="articleAudience" class="field" type="text" :placeholder="t('editor.articleAudienceHint')">
            </label>
            <label class="form-field">
              <span class="form-label">{{ t('editor.articleLocale') }}</span>
              <select v-model="articleLocale" class="field">
                <option value="ru">ru</option>
                <option value="en">en</option>
              </select>
            </label>
            <label class="form-field">
              <span class="form-label">{{ t('editor.articleFile') }}</span>
              <input class="field" type="file" accept=".md,text/markdown,text/plain" @change="onArticleFile">
            </label>
          </div>
          <label class="form-field" style="margin-top: 0.75rem; display: block">
            <span class="form-label">{{ t('editor.articleBody') }}</span>
            <textarea
              v-model="articleText"
              class="editor-textarea"
              rows="12"
              spellcheck="false"
              :placeholder="t('editor.articlePlaceholder')"
            />
          </label>
          <button
            class="btn-primary"
            type="button"
            style="margin-top: 0.75rem"
            :disabled="actionPending"
            @click="onCourseFromArticle"
          >
            {{ actionPending && courseRunning ? t('editor.buildCourseRunning') : t('editor.buildCourse') }}
          </button>

          <ClientOnly>
            <CourseBuildProgress
              :active="courseRunning"
              :done="courseDone"
              :error="courseError"
              :progress="courseProgress"
              :current-stage="courseStage"
              :message="courseMessage"
              :elapsed-ms="courseElapsedMs"
              :log="courseLog"
              :outcomes="courseOutcomes"
              :chapters="courseChapters"
              :quizzes="courseQuizzes"
              :tasks="courseTasks"
              :warnings="courseWarnings"
            />
          </ClientOnly>
        </div>
      </div>

      <div class="form-panel" style="margin-top: 1rem">
        <div class="form-panel-header">
          <h2 class="form-panel-title">{{ t('editor.manifest') }}</h2>
        </div>
        <div class="form-panel-body">
          <textarea v-model="manifestText" class="editor-textarea" rows="24" spellcheck="false" />
          <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem">
            <button class="btn-primary" type="button" :disabled="actionPending" @click="onValidate">
              {{ t('editor.validate') }}
            </button>
            <button class="btn-secondary" type="button" :disabled="actionPending" @click="onBuild">
              {{ t('editor.build') }}
            </button>
            <button class="btn-ghost" type="button" :disabled="actionPending" @click="onUpload">
              {{ t('editor.upload') }}
            </button>
          </div>
        </div>
      </div>

      <div class="form-panel" style="margin-top: 1rem">
        <div class="form-panel-header">
          <h2 class="form-panel-title">{{ t('editor.suggest') }}</h2>
        </div>
        <div class="form-panel-body">
          <label class="form-field">
            <span class="form-label">{{ t('editor.suggestPrompt') }}</span>
            <input v-model="suggestPrompt" class="field" type="text">
          </label>
          <button class="btn-primary" type="button" style="margin-top: 0.75rem" :disabled="actionPending" @click="onSuggest">
            {{ t('editor.suggest') }}
          </button>
        </div>
      </div>

      <p v-if="validationMessage" class="alert-notice" style="margin-top: 1rem; white-space: pre-wrap">
        {{ validationMessage }}
      </p>
      <p v-if="uploadMessage" class="alert-notice" style="margin-top: 1rem">
        {{ uploadMessage }}
      </p>
      <p v-if="errorMessage && !courseError" class="alert-error" style="margin-top: 1rem">
        {{ errorMessage }}
      </p>
    </template>
  </PageShell>
</template>
