<script setup lang="ts">
import {
  DocumentPlusIcon,
  LinkIcon,
  PlusIcon,
  SparklesIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import type { CourseStageEvent, CourseStageName } from '~/composables/useStudio'
import { useElapsedTimer } from '~/composables/useElapsedTimer'
import { extractErrorMessage } from '~/utils/api'
import {
  buildLibraryCoursePayload,
  canStartLibraryBuild,
  emptyLibraryDraft,
  isAbortError,
  libraryEnabledStages,
  localizeCourseError,
  localizeCourseProgressMessage,
  localizeCourseWarning,
  looksLikeHttpUrl,
  packFilenameFromManifest,
  parseConsistencyGateDetail,
  planFillDraft,
  removeLibraryDraft,
  usableLibraryDrafts,
  type LibraryDraftArticle,
} from '~/utils/studio'

const props = withDefaults(
  defineProps<{
    open?: boolean
  }>(),
  { open: true },
)

const emit = defineEmits<{
  close: []
  installed: []
}>()

const { t, te } = useI18n()
const { streamCourseFromArticle, fetchArticleFromUrl, buildPack, validateManifest } = useStudio()
const { uploadPack } = useCatalog()
const toasts = useToasts()

type DraftArticle = LibraryDraftArticle

const title = ref('')
const locale = ref('ru')
const audience = ref('')
const includeTheory = ref(true)
const includeQuizzes = ref(true)
const includeCode = ref(true)
const drafts = ref<DraftArticle[]>([emptyLibraryDraft()])
const activeKey = ref(drafts.value[0].key)
const dragOver = ref(false)
const urlInput = ref('')
const urlFetching = ref(false)
type UrlFetchStage = 'idle' | 'download' | 'extract' | 'ai'
const urlFetchStage = ref<UrlFetchStage>('idle')
const showMarkdown = ref(false)

const running = ref(false)
const done = ref(false)
const error = ref('')
const progress = ref(0)
const stage = ref<CourseStageName | string>('analyze')
const message = ref('')
const { elapsedMs, startTimer, stopTimer } = useElapsedTimer()
const log = ref<CourseStageEvent[]>([])
const outcomes = ref<string[]>([])
const chapters = ref<Array<{ id?: string; title?: string } | string>>([])
const quizzes = ref<Array<{ id?: unknown; title?: unknown; question?: unknown }>>([])
const tasks = ref<Array<{ id?: unknown; title?: unknown; tests?: unknown }>>([])
const warnings = ref<string[]>([])

const gateOpen = ref(false)
const gateDeviations = ref<Array<{ summary: string; sources: string[] }>>([])
const gateSimilarity = ref<number | null>(null)
const gateRelated = ref(true)


const viewMode = ref<'edit' | 'progress'>('edit')

let abortController: AbortController | null = null
let urlAbortController: AbortController | null = null
let urlStageTimers: ReturnType<typeof setTimeout>[] = []
let cancelRequested = false

const urlFetchStageLabel = computed(() => {
  if (!urlFetching.value) {
    return ''
  }
  if (urlFetchStage.value === 'download') {
    return t('libraryCreate.urlStageDownload')
  }
  if (urlFetchStage.value === 'extract') {
    return t('libraryCreate.urlStageExtract')
  }
  if (urlFetchStage.value === 'ai') {
    return t('libraryCreate.urlStageAi')
  }
  return t('libraryCreate.urlFetching')
})

const usableDrafts = computed(() => usableLibraryDrafts(drafts.value))

const canStart = computed(() =>
  canStartLibraryBuild({
    usableCount: usableDrafts.value.length,
    running: running.value,
    urlFetching: urlFetching.value,
    includeTheory: includeTheory.value,
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
  }),
)

const enabledStages = computed(() =>
  libraryEnabledStages({
    includeTheory: includeTheory.value,
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
  }),
)

const showConsistency = computed(
  () => usableDrafts.value.length > 1 || log.value.some((e) => e.stage === 'consistency'),
)

const showForm = computed(() => viewMode.value === 'edit')

const activeDraft = computed(() => {
  const found = drafts.value.find((item) => item.key === activeKey.value)
  return found || drafts.value[0]
})

const filledCount = computed(() => usableDrafts.value.length)

function emptyDraft(): DraftArticle {
  return emptyLibraryDraft()
}

function fillDraft(
  titleText: string,
  content: string,
  sourceUrl = '',
  videos: Array<{ url: string; title?: string | null }> = [],
) {
  const planned = planFillDraft(drafts.value, { titleText, content, sourceUrl, videos })
  if (planned.kind === 'max') {
    toasts.notice(t('libraryCreate.maxArticles'))
    return false
  }
  drafts.value = planned.drafts
  activeKey.value = planned.activeKey
  return true
}

function selectDraft(key: string) {
  activeKey.value = key
}

function addDraft() {
  if (drafts.value.length >= 6) {
    toasts.notice(t('libraryCreate.maxArticles'))
    return
  }
  const next = emptyDraft()
  drafts.value = [...drafts.value, next]
  activeKey.value = next.key
}

function removeDraft(key: string) {
  const next = removeLibraryDraft(drafts.value, key, emptyDraft)
  drafts.value = next.drafts
  if (activeKey.value === key || !drafts.value.some((item) => item.key === activeKey.value)) {
    activeKey.value = next.activeKey
  }
}

function looksLikeUrl(value: string) {
  return looksLikeHttpUrl(value)
}

function clearUrlStageTimers() {
  for (const handle of urlStageTimers) {
    clearTimeout(handle)
  }
  urlStageTimers = []
}

function startUrlStageProgress() {
  clearUrlStageTimers()
  urlFetchStage.value = 'download'

  urlStageTimers.push(
    setTimeout(() => {
      if (urlFetching.value) {
        urlFetchStage.value = 'extract'
      }
    }, 2200),
  )
  urlStageTimers.push(
    setTimeout(() => {
      if (urlFetching.value) {
        urlFetchStage.value = 'ai'
      }
    }, 5500),
  )
}

function stopUrlFetch(opts?: { silent?: boolean }) {
  const wasFetching = urlFetching.value
  urlAbortController?.abort()
  urlAbortController = null
  clearUrlStageTimers()
  urlFetching.value = false
  urlFetchStage.value = 'idle'
  if (wasFetching && !opts?.silent) {
    toasts.notice(t('libraryCreate.urlCancelled'))
  }
}

function stopBuild(opts?: { toast?: boolean }) {
  const wasActive = running.value || gateOpen.value || abortController !== null
  cancelRequested = true
  abortController?.abort()
  abortController = null
  running.value = false
  done.value = false
  error.value = ''
  progress.value = 0
  message.value = ''
  log.value = []
  gateOpen.value = false
  viewMode.value = 'edit'
  stopTimer()
  if (wasActive && opts?.toast !== false) {
    toasts.notice(t('libraryCreate.buildCancelled'))
  }
}

function hardStopAll(opts?: { toast?: boolean }) {
  stopUrlFetch({ silent: true })
  if (running.value || gateOpen.value || abortController) {
    stopBuild({ toast: opts?.toast ?? false })
  }
}

async function addFromUrl() {
  if (urlFetching.value || running.value) {
    toasts.notice(t('libraryCreate.errors.urlBusy'))
    return
  }
  const raw = urlInput.value.trim()
  if (!looksLikeUrl(raw)) {
    toasts.error(t('libraryCreate.errors.urlInvalid'))
    return
  }
  urlAbortController?.abort()
  urlAbortController = new AbortController()
  const signal = urlAbortController.signal
  urlFetching.value = true
  startUrlStageProgress()
  try {
    const article = await fetchArticleFromUrl(raw, { signal })
    if (signal.aborted) {
      return
    }
    const ok = fillDraft(
      article.title || raw,
      article.content,
      article.source_url || raw,
      Array.isArray(article.videos) ? article.videos : [],
    )
    if (ok) {
      urlInput.value = ''
      toasts.success(t('libraryCreate.urlLoaded'))
    }
  } catch (error) {
    if (isAbortError(error, signal)) {
      return
    }
    toasts.error(extractErrorMessage(error) || t('libraryCreate.errors.urlFailed'))
  } finally {
    clearUrlStageTimers()
    if (urlAbortController?.signal === signal) {
      urlAbortController = null
    }
    urlFetching.value = false
    urlFetchStage.value = 'idle'
  }
}

async function ingestFiles(files: File[]) {
  const mdFiles = files.filter(
    (file) =>
      file.name.toLowerCase().endsWith('.md')
      || file.type.includes('markdown')
      || file.type === 'text/plain',
  )
  if (!mdFiles.length) {
    return
  }
  let added = 0
  for (const file of mdFiles) {
    const text = await file.text()
    const name = file.name.replace(/\.md$/i, '')
    if (fillDraft(name, text)) {
      added += 1
    }
  }
  if (added) {
    toasts.notice(t('libraryCreate.filesLoaded', { count: added }))
  }
}

async function onMdFiles(event: Event) {
  const input = event.target as HTMLInputElement
  await ingestFiles(Array.from(input.files || []))
  input.value = ''
}

async function onDrop(event: DragEvent) {
  dragOver.value = false
  if (running.value) {
    return
  }
  event.preventDefault()
  await ingestFiles(Array.from(event.dataTransfer?.files || []))
}

function onDragOver(event: DragEvent) {
  if (running.value) {
    return
  }
  event.preventDefault()
  dragOver.value = true
}

function resetProgress() {
  running.value = true
  done.value = false
  error.value = ''
  progress.value = 0.02
  stage.value = usableDrafts.value.length > 1 ? 'consistency' : 'analyze'
  message.value = t('libraryCreate.working')
  log.value = []
  outcomes.value = []
  chapters.value = []
  quizzes.value = []
  tasks.value = []
  warnings.value = []
  gateOpen.value = false
  viewMode.value = 'progress'
  cancelRequested = false
  abortController?.abort()
  abortController = new AbortController()
  startTimer()
}

function applyEvent(event: CourseStageEvent) {
  log.value = [...log.value, event]
  if (event.type === 'error') {
    progress.value = 0
  } else if (typeof event.progress === 'number') {
    progress.value = Math.max(progress.value, event.progress)
  }
  if (event.stage) {
    stage.value = event.stage
  }
  const localized = localizeCourseProgressMessage(event, t, te)
  if (localized) {
    message.value = localized
  }
  const detail = event.detail || {}
  if (Array.isArray(detail.outcomes)) {
    outcomes.value = detail.outcomes.map(String)
  }
  if (Array.isArray(detail.chapters)) {
    chapters.value = detail.chapters as Array<{ id?: string; title?: string } | string>
  }
  if (Array.isArray(detail.quizzes)) {
    quizzes.value = detail.quizzes as Array<{ id?: unknown; title?: unknown; question?: unknown }>
  }
  if (Array.isArray(detail.tasks)) {
    tasks.value = detail.tasks as Array<{ id?: unknown; title?: unknown; tests?: unknown }>
  }
  if (Array.isArray(detail.warnings)) {
    warnings.value = detail.warnings.map((item) => localizeCourseWarning(String(item), t, te))
  }
}

function buildPayload(ignoreDeviations: boolean) {
  return buildLibraryCoursePayload({
    articles: usableDrafts.value.map((item, index) => ({
      title: item.title.trim() || t('libraryCreate.untitled', { n: index + 1 }),
      content: item.content.trim(),
      videos: item.videos,
    })),
    title: title.value,
    audience: audience.value,
    locale: locale.value,
    ignoreDeviations,
    includeTheory: includeTheory.value,
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
  })
}

async function installManifest(manifest: Record<string, unknown>) {
  const validation = await validateManifest(manifest)
  if (!validation.valid) {
    throw new Error(
      validation.errors.map((e) => `${e.path}: ${e.message}`).join('; ') || 'invalid manifest',
    )
  }
  const blob = await buildPack(manifest, [])
  const file = new File([blob], packFilenameFromManifest(manifest), { type: 'application/zip' })
  await uploadPack(file)
}

async function runGenerate(ignoreDeviations: boolean) {
  if (!canStart.value && !ignoreDeviations) {
    if (!(includeTheory.value || includeQuizzes.value || includeCode.value)) {
      toasts.error(t('libraryCreate.errors.needContent'))
      return
    }
    toasts.error(t('libraryCreate.errors.tooShort'))
    return
  }
  if (usableDrafts.value.length < 1) {
    toasts.error(t('libraryCreate.errors.tooShort'))
    return
  }

  resetProgress()
  try {
    const outcome = await streamCourseFromArticle(
      buildPayload(ignoreDeviations),
      applyEvent,
      { signal: abortController?.signal },
    )
    if (cancelRequested || (outcome.kind === 'error' && outcome.message === 'aborted')) {
      restoreEditAfterCancel()
      return
    }
    if (outcome.kind === 'consistency_gate') {
      const gate = parseConsistencyGateDetail(outcome.event.detail)
      gateDeviations.value = gate.deviations
      gateSimilarity.value = gate.similarity
      gateRelated.value = gate.related
      gateOpen.value = true
      message.value = t('libraryCreate.gateTitle')
      running.value = false
      stopTimer()
      toasts.notice(t('libraryCreate.gateToast'), 8000)
      return
    }
    if (outcome.kind === 'error') {
      if (outcome.message === 'aborted') {
        restoreEditAfterCancel()
        return
      }
      throw new Error(outcome.message)
    }

    message.value = t('libraryCreate.installing')

    progress.value = Math.max(progress.value, 0.92)
    await nextTick()
    await installManifest(outcome.result.manifest)
    if (cancelRequested) {
      restoreEditAfterCancel()
      return
    }
    progress.value = 1
    stage.value = 'done'
    done.value = true
    message.value = t('libraryCreate.installed', {
      title: String(outcome.result.manifest.title || title.value || 'Course'),
    })
    if (outcome.result.meta.warnings?.length) {
      warnings.value = outcome.result.meta.warnings.map((item) =>
        localizeCourseWarning(String(item), t, te),
      )
    }
    await nextTick()
    toasts.success(t('libraryCreate.installedToast'))
    emit('installed')
  } catch (err) {
    if (cancelRequested || (err instanceof DOMException && err.name === 'AbortError')) {
      restoreEditAfterCancel()
      return
    }
    done.value = false
    progress.value = 0
    error.value = localizeCourseError(
      extractErrorMessage(err) || t('libraryCreate.errors.failed'),
      t,
    )
    message.value = error.value
    toasts.error(error.value)
  } finally {
    running.value = false
    stopTimer()
    abortController = null
  }
}

function restoreEditAfterCancel() {
  stopBuild({ toast: true })
}

function onCancelGate() {
  gateOpen.value = false
  viewMode.value = 'edit'
  toasts.notice(t('libraryCreate.gateCancelled'))
}

async function onContinueGate() {
  gateOpen.value = false
  await runGenerate(true)
}

async function requestCancelBuild() {
  if (!running.value && !gateOpen.value) {
    return
  }
  const { confirm } = useConfirm()
  const ok = await confirm({
    title: t('libraryCreate.cancelConfirm'),
    confirmLabel: t('dialog.confirm'),
    cancelLabel: t('dialog.cancel'),
    danger: true,
  })
  if (!ok) {
    return
  }
  stopBuild({ toast: true })
}

async function requestClose() {
  if (urlFetching.value) {
    stopUrlFetch({ silent: false })
    emit('close')
    return
  }
  if (running.value || gateOpen.value) {
    const { confirm } = useConfirm()
    const ok = await confirm({
      title: t('libraryCreate.cancelConfirm'),
      confirmLabel: t('dialog.confirm'),
      cancelLabel: t('dialog.cancel'),
      danger: true,
    })
    if (!ok) {
      return
    }
    stopBuild({ toast: true })
    emit('close')
    return
  }
  emit('close')
}

function onBackdropClick() {
  void requestClose()
}

function onKeydown(event: KeyboardEvent) {
  if (!props.open) {
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    void requestClose()
  }
}

function syncModalChrome(isOpen: boolean) {
  document.body.classList.toggle('lc-modal-open', isOpen)
}

watch(
  () => props.open,
  (isOpen, wasOpen) => {
    syncModalChrome(isOpen)

    if (wasOpen && !isOpen) {
      hardStopAll({ toast: false })
    }
  },
)

onMounted(() => {
  syncModalChrome(props.open)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  hardStopAll({ toast: false })
  stopTimer()
  syncModalChrome(false)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="op-modal">
      <div
        v-if="open"
        class="lc-backdrop"
        role="presentation"
        @click.self="onBackdropClick"
      >
      <div
        class="lc-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="library-create-title"
      >
        <header class="lc-hero">
          <div class="lc-hero-copy">
            <p class="lc-eyebrow">
              <SparklesIcon class="icon-sm" aria-hidden="true" />
              {{ t('libraryCreate.eyebrow') }}
            </p>
            <h2 id="library-create-title">{{ t('libraryCreate.title') }}</h2>
          </div>
          <button
            class="btn-ghost btn-sm btn-icon lc-close"
            type="button"
            :aria-label="t('libraryCreate.close')"
            @click="requestClose"
          >
            <XMarkIcon class="icon-sm" />
          </button>
        </header>

        <div class="lc-body" :class="{ 'is-progress': !showForm }">
          <Transition name="page-cyber" mode="out-in">
          <div v-if="showForm" key="form" class="lc-form-pane">
            <section class="lc-setup" :aria-label="t('libraryCreate.courseTitle')">
              <label class="lc-field lc-field-title">
                <span class="lc-field-label">{{ t('libraryCreate.courseTitle') }}</span>
                <input
                  v-model="title"
                  class="field"
                  type="text"
                  :placeholder="t('libraryCreate.courseTitleHint')"
                >
              </label>
              <label class="lc-field lc-field-audience">
                <span class="lc-field-label">{{ t('libraryCreate.audience') }}</span>
                <input
                  v-model="audience"
                  class="field"
                  type="text"
                  :placeholder="t('libraryCreate.audienceHint')"
                >
              </label>
              <label class="lc-field lc-field-locale">
                <span class="lc-field-label">{{ t('libraryCreate.locale') }}</span>
                <select v-model="locale" class="field">
                  <option value="ru">ru</option>
                  <option value="en">en</option>
                </select>
              </label>
            </section>

            <section class="lc-workspace" :aria-label="t('libraryCreate.ingestTitle')">
              <aside class="lc-rail">
                <div class="lc-rail-head">
                  <span class="lc-rail-title">{{ t('libraryCreate.ingestTitle') }}</span>
                  <span class="lc-rail-count">{{ filledCount }}/6</span>
                </div>
                <div class="lc-rail-list" role="tablist" aria-orientation="vertical">
                  <button
                    v-for="(draft, index) in drafts"
                    :key="draft.key"
                    class="lc-rail-item"
                    :class="{
                      'is-active': draft.key === activeKey,
                      'is-ready': draft.content.trim().length >= 40,
                    }"
                    type="button"
                    role="tab"
                    :aria-selected="draft.key === activeKey"
                    @click="selectDraft(draft.key)"
                  >
                    <span class="lc-rail-index">{{ index + 1 }}</span>
                    <span class="lc-rail-label">
                      {{ draft.title.trim() || t('libraryCreate.articleN', { n: index + 1 }) }}
                    </span>
                    <span
                      v-if="draft.content.trim().length >= 40"
                      class="lc-rail-dot"
                      aria-hidden="true"
                    />
                  </button>
                </div>
                <button
                  class="lc-rail-add"
                  type="button"
                  :disabled="drafts.length >= 6"
                  @click="addDraft"
                >
                  <PlusIcon class="icon-sm" />
                  {{ t('libraryCreate.addArticle') }}
                </button>
              </aside>

              <div class="lc-main">
                <div
                  class="lc-ingest"
                  :class="{ 'is-over': dragOver, 'is-fetching': urlFetching }"
                  @dragenter.prevent="onDragOver"
                  @dragover.prevent="onDragOver"
                  @dragleave.prevent="dragOver = false"
                  @drop.prevent="onDrop"
                >
                  <div class="lc-url-block">
                    <div class="lc-url-row">
                      <span class="lc-url-icon" aria-hidden="true">
                        <LinkIcon class="icon-sm" />
                      </span>
                      <input
                        v-model="urlInput"
                        class="field lc-url-input"
                        type="url"
                        inputmode="url"
                        autocomplete="off"
                        :disabled="urlFetching || running"
                        :placeholder="t('libraryCreate.urlPlaceholder')"
                        :aria-label="t('libraryCreate.urlLabel')"
                        @keydown.enter.prevent="addFromUrl"
                      >
                      <button
                        class="btn-primary btn-sm"
                        type="button"
                        :disabled="urlFetching || running"
                        @click="addFromUrl"
                      >
                        <span
                          v-if="urlFetching"
                          class="loading-spinner loading-spinner-sm"
                          aria-hidden="true"
                        />
                        {{ urlFetching ? t('libraryCreate.urlFetching') : t('libraryCreate.urlAdd') }}
                      </button>
                    </div>
                    <p
                      v-if="urlFetching"
                      class="lc-url-stage"
                      aria-live="polite"
                    >
                      <span class="lc-url-stage-index" aria-hidden="true">
                        {{
                          urlFetchStage === 'download'
                            ? '1/3'
                            : urlFetchStage === 'extract'
                              ? '2/3'
                              : '3/3'
                        }}
                      </span>
                      {{ urlFetchStageLabel }}
                    </p>
                  </div>
                  <div class="lc-ingest-alt">
                    <DocumentPlusIcon class="lc-drop-icon" aria-hidden="true" />
                    <span>{{ t('libraryCreate.dropHint') }}</span>
                    <label class="lc-file-link">
                      {{ t('libraryCreate.pickMd') }}
                      <input
                        class="sr-only"
                        type="file"
                        accept=".md,text/markdown,text/plain"
                        multiple
                        @change="onMdFiles"
                      >
                    </label>
                  </div>
                </div>

                <div v-if="activeDraft" class="lc-editor">
                  <div class="lc-editor-toolbar">
                    <input
                      v-model="activeDraft.title"
                      class="field lc-editor-title"
                      type="text"
                      :placeholder="t('libraryCreate.articleTitle')"
                    >
                    <button
                      class="btn-ghost btn-sm btn-icon"
                      type="button"
                      :aria-label="t('libraryCreate.removeArticle')"
                      @click="removeDraft(activeDraft.key)"
                    >
                      <TrashIcon class="icon-sm" />
                    </button>
                  </div>

                  <p v-if="activeDraft.sourceUrl" class="lc-source-url">
                    <LinkIcon class="icon-sm" />
                    <a :href="activeDraft.sourceUrl" target="_blank" rel="noopener noreferrer">
                      {{ activeDraft.sourceUrl }}
                    </a>
                  </p>

                  <div
                    v-if="!activeDraft.content.trim() && !showMarkdown"
                    class="lc-editor-empty"
                  >
                    <p class="lc-editor-empty-title">{{ t('libraryCreate.sourceEmptyTitle') }}</p>
                    <p class="lc-editor-empty-meta">{{ t('libraryCreate.sourceEmptyMeta') }}</p>
                  </div>

                  <template v-else>
                    <div class="lc-editor-bar">
                      <button
                        class="btn-ghost btn-sm lc-md-toggle"
                        type="button"
                        @click="showMarkdown = !showMarkdown"
                      >
                        {{ showMarkdown ? t('libraryCreate.hideMarkdown') : t('libraryCreate.showMarkdown') }}
                      </button>
                      <span class="lc-editor-hint">
                        {{ t('libraryCreate.charCount', { count: activeDraft.content.trim().length }) }}
                      </span>
                    </div>
                    <textarea
                      v-if="showMarkdown"
                      v-model="activeDraft.content"
                      class="lc-editor-area"
                      rows="11"
                      spellcheck="false"
                      :placeholder="t('libraryCreate.articlePlaceholder')"
                    />
                    <p v-else class="lc-editor-summary">
                      {{ t('libraryCreate.sourceReadyMeta') }}
                    </p>
                  </template>
                </div>
              </div>
            </section>
          </div>
          <div v-else key="progress" class="lc-progress-pane">
            <div
              v-if="gateOpen"
              class="lc-gate-panel"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="library-create-gate-title"
            >
              <h3 id="library-create-gate-title">{{ t('libraryCreate.gateTitle') }}</h3>
              <p class="lc-gate-lead">
                {{
                  gateRelated
                    ? t('libraryCreate.gateRelated', {
                        similarity: gateSimilarity == null ? '—' : Math.round(gateSimilarity * 100),
                      })
                    : t('libraryCreate.gateUnrelated')
                }}
              </p>
              <div v-if="gateDeviations.length" class="lc-gate-body">
                <ul class="lc-gate-list">
                  <li v-for="(item, i) in gateDeviations" :key="`d-${i}`">
                    <strong>{{ item.summary }}</strong>
                    <span v-if="item.sources?.length"> — {{ item.sources.join(', ') }}</span>
                  </li>
                </ul>
              </div>
            </div>
            <CourseBuildProgress
              v-else
              :active="running"
              :done="done"
              :error="error"
              :progress="progress"
              :current-stage="stage"
              :message="message"
              :elapsed-ms="elapsedMs"
              :log="log"
              :outcomes="outcomes"
              :chapters="chapters"
              :quizzes="quizzes"
              :tasks="tasks"
              :warnings="warnings"
              :show-consistency="showConsistency"
              :enabled-stages="enabledStages"
              compact
            />
          </div>
          </Transition>
        </div>

        <footer class="lc-footer" :class="{ 'is-progress-actions': !showForm }">
          <div v-if="showForm" class="lc-footer-start">
            <p class="lc-footer-meta">
              {{ t('libraryCreate.sourceCount', { count: filledCount, max: 6 }) }}
            </p>
            <div class="lc-stages" role="group" :aria-label="t('libraryCreate.stagesLabel')">
              <span class="lc-stages-legend">{{ t('libraryCreate.stagesLabel') }}</span>
              <button
                class="lc-stage-chip"
                type="button"
                :aria-pressed="includeTheory"
                :class="{ 'is-on': includeTheory }"
                @click="includeTheory = !includeTheory"
              >
                {{ t('libraryCreate.includeTheory') }}
              </button>
              <button
                class="lc-stage-chip"
                type="button"
                :aria-pressed="includeQuizzes"
                :class="{ 'is-on': includeQuizzes }"
                @click="includeQuizzes = !includeQuizzes"
              >
                {{ t('libraryCreate.includeQuizzes') }}
              </button>
              <button
                class="lc-stage-chip"
                type="button"
                :aria-pressed="includeCode"
                :class="{ 'is-on': includeCode }"
                @click="includeCode = !includeCode"
              >
                {{ t('libraryCreate.includeCode') }}
              </button>
            </div>
          </div>
          <p v-else-if="gateOpen" class="lc-footer-status">
            {{ t('libraryCreate.gateFooterHint') }}
          </p>
          <p v-else-if="running" class="lc-footer-status">
            {{ t('libraryCreate.working') }}
          </p>
          <div class="lc-footer-actions">
            <button
              v-if="showForm"
              class="btn-primary"
              type="button"
              :disabled="!canStart"
              @click="runGenerate(false)"
            >
              <SparklesIcon class="icon-sm" />
              {{ t('libraryCreate.build') }}
            </button>
            <template v-else-if="gateOpen">
              <button class="btn-secondary" type="button" @click="onCancelGate">
                {{ t('libraryCreate.gateCancel') }}
              </button>
              <button
                class="btn-primary"
                type="button"
                :disabled="running"
                @click="onContinueGate"
              >
                {{ t('libraryCreate.gateContinue') }}
              </button>
            </template>
            <button
              v-else-if="running"
              class="btn-secondary"
              type="button"
              @click="requestCancelBuild"
            >
              {{ t('libraryCreate.cancel') }}
            </button>
            <button
              v-else
              class="btn-primary"
              type="button"
              @click="emit('close')"
            >
              {{ t('libraryCreate.done') }}
            </button>
          </div>
        </footer>
      </div>
      </div>
    </Transition>
  </Teleport>
</template>
