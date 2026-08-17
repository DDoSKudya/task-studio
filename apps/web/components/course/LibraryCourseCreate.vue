<script setup lang="ts">
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CodeBracketIcon,
  DocumentPlusIcon,
  LinkIcon,
  PlusIcon,
  QuestionMarkCircleIcon,
  SparklesIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import type { CourseStageEvent, CourseStageName } from '~/composables/studio/useStudio'
import { useElapsedTimer } from '~/composables/session/useElapsedTimer'
import { extractErrorMessage } from '~/utils/api'
import {
  buildLibraryCoursePayload,
  buildResumeCoursePayload,
  canStartLibraryBuild,
  emptyLibraryDraft,
  hydrateLibraryFormFromRequest,
  isAbortError,
  libraryEnabledStages,
  libraryContentMixKey,
  localizeCourseError,
  localizeCourseProgressMessage,
  localizeCourseWarning,
  extractHttpUrls,
  packFilenameFromManifest,
  parseCodeSuitabilityGateDetail,
  planFillDraft,
  practiceLadderSummary,
  removeLibraryDraft,
  usableLibraryDrafts,
  LIBRARY_MAX_ARTICLES,
  LIBRARY_MIN_CONTENT_LEN,
  type CodeSuitabilityAction,
  type CourseDepth,
  type CourseLayout,
  type LibraryDraftArticle,
} from '~/utils/studio'

const props = withDefaults(
  defineProps<{
    open?: boolean
    resumeBuildId?: string | null
  }>(),
  { open: true, resumeBuildId: null },
)

const emit = defineEmits<{
  close: []
  installed: []
  'update:resumeBuildId': [value: string | null]
}>()

const { t, te } = useI18n()
const { streamCourseFromArticle, fetchArticleFromUrl, buildPack, validateManifest, discardCourseBuild, getCourseBuild } =
  useStudio()
const { uploadPack } = useCatalog()
const toasts = useToasts()

type DraftArticle = LibraryDraftArticle

const title = ref('')
const locale = ref('ru')
const audience = ref('')
const includeQuizzes = ref(true)
const includeCode = ref(true)
const courseDepth = ref<CourseDepth>('standard')
const courseLayout = ref<CourseLayout>('by_topic')
const quizCount = ref(4)
const practiceCount = ref(3)
const drafts = ref<DraftArticle[]>([emptyLibraryDraft()])
const activeKey = ref(drafts.value[0]!.key)
const dragOver = ref(false)
const urlInput = ref('')
const urlFetching = ref(false)
const urlBatchDone = ref(0)
const urlBatchTotal = ref(0)
const urlBatchOk = ref(0)
const urlBatchFail = ref(0)
const urlBatchCurrent = ref(0)
const urlFailedLinks = ref<string[]>([])
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

const codeGateOpen = ref(false)
const codeGateScore = ref<number | null>(null)
const codeGateProfile = ref<string | null>(null)
const pendingCodeAction = ref<CodeSuitabilityAction | null>(null)

const viewMode = ref<'edit' | 'progress'>('edit')
const activeBuildId = ref<string | null>(null)
const formStep = ref<'sources' | 'options'>('sources')

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

const urlBatchStatusLine = computed(() => {
  if (!urlFetching.value) {
    return ''
  }
  if (urlBatchTotal.value > 1) {
    return t('libraryCreate.urlBatchStatus', {
      ok: urlBatchOk.value,
      fail: urlBatchFail.value,
      current: urlBatchCurrent.value,
      total: urlBatchTotal.value,
    })
  }
  const step =
    urlFetchStage.value === 'download'
      ? '1/3'
      : urlFetchStage.value === 'extract'
        ? '2/3'
        : '3/3'
  return step
})

function dismissFailedUrls() {
  urlFailedLinks.value = []
}

function resetUrlBatchCounters() {
  urlBatchDone.value = 0
  urlBatchTotal.value = 0
  urlBatchOk.value = 0
  urlBatchFail.value = 0
  urlBatchCurrent.value = 0
}

const usableDrafts = computed(() => usableLibraryDrafts(drafts.value))

const canStart = computed(() =>
  canStartLibraryBuild({
    usableCount: usableDrafts.value.length,
    running: running.value,
    urlFetching: urlFetching.value,
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
  }),
)

const enabledStages = computed(() =>
  libraryEnabledStages({
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
    layout: courseLayout.value,
  }),
)

const contentMixKey = computed(() =>
  libraryContentMixKey({
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
  }),
)

const progressStageLabels = computed(() => {
  if (courseLayout.value !== 'by_topic') {
    return {}
  }
  return {
    theory: t(`libraryCreate.roadmap.${contentMixKey.value}`),
  }
})

const layoutOptions = computed(() =>
  [
    {
      id: 'by_topic' as const,
      label: t('libraryCreate.layoutByTopic'),
      hint: t(`libraryCreate.layoutHint.byTopic.${contentMixKey.value}`),
    },
    {
      id: 'phased' as const,
      label: t('libraryCreate.layoutPhased'),
      hint: t(`libraryCreate.layoutHint.phased.${contentMixKey.value}`),
    },
  ],
)

const showForm = computed(() => viewMode.value === 'edit')
const showSourcesStep = computed(() => showForm.value && formStep.value === 'sources')
const showOptionsStep = computed(() => showForm.value && formStep.value === 'options')

const footerPhase = computed(() => {
  if (showSourcesStep.value) {
    return 'sources'
  }
  if (showOptionsStep.value) {
    return 'options'
  }
  if (codeGateOpen.value) {
    return 'code-gate'
  }
  if (running.value) {
    return 'running'
  }
  return 'done'
})

const activeDraft = computed(
  () => drafts.value.find((item) => item.key === activeKey.value) ?? drafts.value[0] ?? null,
)

const filledCount = computed(() => usableDrafts.value.length)
const maxArticles = LIBRARY_MAX_ARTICLES

const canGoNext = computed(
  () => filledCount.value >= 1 && !urlFetching.value && !running.value,
)

const depthOptions = computed(() =>
  (
    [
      { id: 'light' as const, label: t('libraryCreate.depthLight') },
      { id: 'standard' as const, label: t('libraryCreate.depthStandard') },
      { id: 'deep' as const, label: t('libraryCreate.depthDeep') },
    ] as const
  ),
)

const practiceMixHint = computed(() => {
  if (!includeCode.value || practiceCount.value <= 0) {
    return courseLayout.value === 'by_topic'
      ? t('libraryCreate.practiceCountPerTopicHint')
      : t('libraryCreate.practiceCountTotalHint')
  }
  return practiceLadderSummary(practiceCount.value, {
    easy: {
      one: t('libraryCreate.practiceLevelEasyOne'),
      many: t('libraryCreate.practiceLevelEasyMany'),
    },
    medium: {
      one: t('libraryCreate.practiceLevelMediumOne'),
      many: t('libraryCreate.practiceLevelMediumMany'),
    },
    hard: {
      one: t('libraryCreate.practiceLevelHardOne'),
      many: t('libraryCreate.practiceLevelHardMany'),
    },
  })
})

const quizCountLabel = computed(() =>
  courseLayout.value === 'by_topic'
    ? t('libraryCreate.quizCountPerTopic')
    : t('libraryCreate.quizCountTotal'),
)

const practiceCountLabel = computed(() =>
  courseLayout.value === 'by_topic'
    ? t('libraryCreate.practiceCountPerTopic')
    : t('libraryCreate.practiceCountTotal'),
)

const quizCountHint = computed(() =>
  courseLayout.value === 'by_topic'
    ? t('libraryCreate.quizCountPerTopicHint')
    : t('libraryCreate.quizCountTotalHint'),
)

function isDraftReady(draft: DraftArticle) {
  return draft.content.trim().length >= LIBRARY_MIN_CONTENT_LEN
}

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
    toasts.notice(t('libraryCreate.maxArticles', { max: maxArticles }))
    return false
  }
  drafts.value = planned.drafts
  activeKey.value = planned.activeKey
  showMarkdown.value = false
  return true
}

function selectDraft(key: string) {
  activeKey.value = key
  showMarkdown.value = false
}

function addDraft() {
  if (drafts.value.length >= maxArticles) {
    toasts.notice(t('libraryCreate.maxArticles', { max: maxArticles }))
    return
  }
  const next = emptyDraft()
  drafts.value = [...drafts.value, next]
  activeKey.value = next.key
  showMarkdown.value = true
}

function removeDraft(key: string) {
  const next = removeLibraryDraft(drafts.value, key)
  if (!next.drafts.length) {
    const only = emptyDraft()
    drafts.value = [only]
    activeKey.value = only.key
    showMarkdown.value = false
    return
  }
  drafts.value = next.drafts
  activeKey.value = next.activeKey
}

function goNext() {
  if (!canGoNext.value) {
    return
  }
  formStep.value = 'options'
}

function goBack() {
  formStep.value = 'sources'
}

function clampQuizCount() {
  if (!Number.isFinite(quizCount.value) || quizCount.value < 1) {
    quizCount.value = 1
  } else if (quizCount.value > 100) {
    quizCount.value = 100
  }
}

function bumpQuiz(delta: number) {
  quizCount.value += delta
  clampQuizCount()
}

function bumpPractice(delta: number) {
  practiceCount.value += delta
  clampPracticeCount()
}

function clampPracticeCount() {
  if (!Number.isFinite(practiceCount.value) || practiceCount.value < 0) {
    practiceCount.value = 0
  } else if (practiceCount.value > 12) {
    practiceCount.value = 12
  }
}

function onQuizCountInput() {
  clampQuizCount()
}

function onPracticeCountInput() {
  clampPracticeCount()
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
  resetUrlBatchCounters()
  if (wasFetching && !opts?.silent) {
    toasts.notice(t('libraryCreate.urlCancelled'))
  }
}

function stopBuild(opts?: { toast?: boolean }) {
  const wasActive = running.value || codeGateOpen.value || abortController !== null
  cancelRequested = true
  abortController?.abort()
  abortController = null
  running.value = false
  done.value = false
  error.value = ''
  progress.value = 0
  message.value = ''
  log.value = []
  codeGateOpen.value = false
  viewMode.value = 'edit'
  formStep.value = 'sources'
  stopTimer()
  if (wasActive && opts?.toast !== false) {
    toasts.notice(t('libraryCreate.buildCancelled'))
  }
}

function hardStopAll(opts?: { toast?: boolean }) {
  stopUrlFetch({ silent: true })
  if (running.value || codeGateOpen.value || abortController) {
    stopBuild({ toast: opts?.toast ?? false })
  }
}

async function addFromUrl() {
  if (urlFetching.value || running.value) {
    toasts.notice(t('libraryCreate.errors.urlBusy'))
    return
  }
  const raw = urlInput.value.trim()
  const remaining = Math.max(0, maxArticles - drafts.value.filter((item) => item.content.trim()).length)
  const urls = extractHttpUrls(raw, Math.max(1, remaining || 20))
  if (!urls.length) {
    toasts.error(t('libraryCreate.errors.urlInvalid'))
    return
  }
  if (remaining <= 0) {
    toasts.notice(t('libraryCreate.maxArticles', { max: maxArticles }))
    return
  }
  const queue = urls.slice(0, remaining)
  const batchMode = queue.length > 1
  urlAbortController?.abort()
  urlAbortController = new AbortController()
  const signal = urlAbortController.signal
  urlFailedLinks.value = []
  urlFetching.value = true
  urlBatchTotal.value = queue.length
  urlBatchDone.value = 0
  urlBatchOk.value = 0
  urlBatchFail.value = 0
  urlBatchCurrent.value = 0
  let added = 0
  let failed = 0
  const failedUrls: string[] = []
  try {
    for (let i = 0; i < queue.length; i += 1) {
      const link = queue[i]!
      if (signal.aborted) {
        break
      }
      urlBatchCurrent.value = i + 1
      startUrlStageProgress()
      try {
        const article = await fetchArticleFromUrl(link, { signal })
        if (signal.aborted) {
          break
        }
        const ok = fillDraft(
          article.title || link,
          article.content,
          article.source_url || link,
          Array.isArray(article.videos) ? article.videos : [],
        )
        if (ok) {
          added += 1
          urlBatchOk.value = added
        } else {
          failed += 1
          urlBatchFail.value = failed
          failedUrls.push(link)
          break
        }
      } catch (error) {
        if (isAbortError(error, signal)) {
          break
        }
        failed += 1
        urlBatchFail.value = failed
        failedUrls.push(link)
        if (!batchMode) {
          toasts.error(
            localizeCourseError(
              extractErrorMessage(error) || t('libraryCreate.errors.urlFailed'),
              t,
            ) || t('libraryCreate.errors.urlFailedOne', { url: link }),
          )
        }
      } finally {
        urlBatchDone.value += 1
        clearUrlStageTimers()
      }
    }
    if (!signal.aborted) {
      urlInput.value = ''
      urlFailedLinks.value = failedUrls
      if (added > 0 && failed === 0) {
        toasts.success(
          added === 1
            ? t('libraryCreate.urlLoaded')
            : t('libraryCreate.urlLoadedMany', { count: added }),
        )
      } else if (added > 0) {
        toasts.notice(t('libraryCreate.urlLoadedPartial', { ok: added, fail: failed }))
      } else if (failed > 0 && batchMode) {
        toasts.error(t('libraryCreate.urlLoadedNone', { fail: failed }))
      }
    }
  } finally {
    clearUrlStageTimers()
    if (urlAbortController?.signal === signal) {
      urlAbortController = null
    }
    urlFetching.value = false
    urlFetchStage.value = 'idle'
    resetUrlBatchCounters()
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
  stage.value = 'analyze'
  message.value = t('libraryCreate.working')
  log.value = []
  outcomes.value = []
  chapters.value = []
  quizzes.value = []
  tasks.value = []
  warnings.value = []
  viewMode.value = 'progress'
  cancelRequested = false
  abortController?.abort()
  abortController = new AbortController()
  startTimer()
}

function applyEvent(event: CourseStageEvent) {
  log.value = [...log.value, event]
  const eventBuildId =
    (typeof event.build_id === 'string' && event.build_id) ||
    (typeof event.detail?.build_id === 'string' ? String(event.detail.build_id) : '')
  if (eventBuildId) {
    activeBuildId.value = eventBuildId
  }
  if (event.type !== 'error' && typeof event.progress === 'number') {
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

function buildPayload(
  codeSuitabilityAction?: CodeSuitabilityAction | null,
  buildId?: string | null,
) {
  return buildLibraryCoursePayload({
    articles: usableDrafts.value.map((item, index) => ({
      title: item.title.trim() || t('libraryCreate.untitled', { n: index + 1 }),
      content: item.content.trim(),
      videos: item.videos,
    })),
    title: title.value,
    audience: audience.value,
    locale: locale.value,
    courseDepth: courseDepth.value,
    layout: courseLayout.value,
    quizCount: quizCount.value,
    practiceCount: practiceCount.value,
    includeQuizzes: includeQuizzes.value,
    includeCode: includeCode.value,
    codeSuitabilityAction: codeSuitabilityAction ?? null,
    buildId: buildId ?? activeBuildId.value,
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

async function onCodeGateChoice(action: CodeSuitabilityAction) {
  codeGateOpen.value = false
  pendingCodeAction.value = action
  await runGenerate(action, {
    resumeOnly: Boolean(activeBuildId.value),
  })
}

async function runGenerate(
  codeSuitabilityAction?: CodeSuitabilityAction | null,
  options?: { resumeOnly?: boolean },
) {
  const resumeOnly = Boolean(options?.resumeOnly && activeBuildId.value)
  if (!resumeOnly) {
    if (!canStart.value) {
      toasts.error(t('libraryCreate.errors.tooShort'))
      return
    }
    if (usableDrafts.value.length < 1) {
      toasts.error(t('libraryCreate.errors.tooShort'))
      return
    }
    activeBuildId.value = null
  }

  resetProgress()
  try {
    const payload = resumeOnly
      ? buildResumeCoursePayload({
          buildId: String(activeBuildId.value),
          codeSuitabilityAction: codeSuitabilityAction ?? pendingCodeAction.value,
        })
      : buildPayload(codeSuitabilityAction ?? pendingCodeAction.value)

    const outcome = await streamCourseFromArticle(
      payload,
      applyEvent,
      { signal: abortController?.signal },
    )
    if (cancelRequested || (outcome.kind === 'error' && outcome.message === 'aborted')) {
      restoreEditAfterCancel()
      return
    }
    if (outcome.kind === 'code_suitability_gate') {
      const gate = parseCodeSuitabilityGateDetail(outcome.event.detail)
      codeGateScore.value = gate.score
      codeGateProfile.value = gate.profile
      codeGateOpen.value = true
      message.value = t('libraryCreate.codeGateTitle')
      running.value = false
      stopTimer()
      toasts.notice(t('libraryCreate.codeGateToast'), 8000)
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
    if (activeBuildId.value) {
      try {
        await discardCourseBuild(activeBuildId.value)
      } catch {
        void 0
      }
      activeBuildId.value = null
      emit('update:resumeBuildId', null)
    }
    progress.value = 1
    stage.value = 'done'
    done.value = true
    const courseTitle = String(outcome.result.manifest.title || title.value || 'Course')
    warnings.value = (outcome.result.meta.warnings ?? []).map((item) =>
      localizeCourseWarning(String(item), t, te),
    )
    message.value = t('libraryCreate.installed', { title: courseTitle })
    await nextTick()
    toasts.success(t('libraryCreate.installedToast'))
    emit('installed')
  } catch (err) {
    if (cancelRequested || (err instanceof DOMException && err.name === 'AbortError')) {
      restoreEditAfterCancel()
      return
    }
    done.value = false
    error.value = localizeCourseError(
      extractErrorMessage(err) || t('libraryCreate.errors.failed'),
      t,
    )
    message.value = activeBuildId.value
      ? t('libraryCreate.buildSavedHint', { message: error.value })
      : error.value
    toasts.error(error.value)
  } finally {
    running.value = false
    stopTimer()
    abortController = null
  }
}

async function applySavedBuild(buildId: string) {
  const detail = await getCourseBuild(buildId)
  const hydrated = hydrateLibraryFormFromRequest(detail.request ?? {})
  drafts.value = hydrated.drafts
  activeKey.value = hydrated.activeKey
  title.value = hydrated.title
  audience.value = hydrated.audience
  locale.value = hydrated.locale
  includeQuizzes.value = hydrated.includeQuizzes
  includeCode.value = hydrated.includeCode
  courseDepth.value = hydrated.courseDepth
  courseLayout.value = hydrated.layout
  if (hydrated.quizCount != null) {
    quizCount.value = hydrated.quizCount
  }
  if (hydrated.practiceCount != null) {
    practiceCount.value = hydrated.practiceCount
  }
  pendingCodeAction.value = hydrated.pendingCodeAction
  activeBuildId.value = buildId
}

async function resumeActiveBuild() {
  const buildId = activeBuildId.value || props.resumeBuildId
  if (!buildId) {
    return
  }
  error.value = ''
  try {
    await applySavedBuild(buildId)
  } catch (err) {
    toasts.error(
      extractErrorMessage(err) || t('libraryCreate.errors.failed'),
    )
    return
  }
  await runGenerate(pendingCodeAction.value, { resumeOnly: true })
}

function restoreEditAfterCancel() {
  stopBuild({ toast: true })
}

function onCancelGate() {
  codeGateOpen.value = false
  viewMode.value = 'edit'
  formStep.value = 'options'
  toasts.notice(t('libraryCreate.gateCancelled'))
}

async function requestCancelBuild() {
  if (!running.value && !codeGateOpen.value) {
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
  if (running.value || codeGateOpen.value) {
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
      formStep.value = 'sources'
      activeBuildId.value = null
    }
    if (isOpen && props.resumeBuildId) {
      activeBuildId.value = props.resumeBuildId
      void resumeActiveBuild()
    }
  },
)

watch(
  () => props.resumeBuildId,
  (buildId) => {
    if (props.open && buildId && buildId !== activeBuildId.value && !running.value) {
      activeBuildId.value = buildId
      void resumeActiveBuild()
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
        :class="{
          'is-progress': !showForm,
          'is-options': showOptionsStep,
          'is-sources': showSourcesStep,
        }"
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
          <div class="lc-body-slot">
          <Transition name="page-cyber" mode="out-in">
          <div v-if="showSourcesStep" key="sources" class="lc-form-pane">
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
                  <option value="ru">{{ t('libraryCreate.localeRu') }}</option>
                  <option value="en">{{ t('libraryCreate.localeEn') }}</option>
                </select>
              </label>
            </section>

            <section class="lc-workspace" :aria-label="t('libraryCreate.ingestTitle')">
              <aside class="lc-rail">
                <div class="lc-rail-head">
                  <span class="lc-rail-title">{{ t('libraryCreate.ingestTitle') }}</span>
                  <span class="lc-rail-count">{{ filledCount }}/{{ maxArticles }}</span>
                </div>
                <div class="lc-rail-list" role="tablist" aria-orientation="vertical">
                  <button
                    v-for="(draft, index) in drafts"
                    :key="draft.key"
                    class="lc-rail-item"
                    :class="{
                      'is-active': draft.key === activeKey,
                      'is-ready': isDraftReady(draft),
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
                      v-if="isDraftReady(draft)"
                      class="lc-rail-dot"
                      aria-hidden="true"
                    />
                  </button>
                </div>
                <button
                  class="lc-rail-add"
                  type="button"
                  :disabled="drafts.length >= maxArticles || running"
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
                    <div class="lc-url-row lc-url-row-multi">
                      <span class="lc-url-icon" aria-hidden="true">
                        <LinkIcon class="icon-sm" />
                      </span>
                      <textarea
                        v-model="urlInput"
                        class="field lc-url-input lc-url-textarea"
                        rows="2"
                        autocomplete="off"
                        spellcheck="false"
                        :disabled="urlFetching || running"
                        :placeholder="t('libraryCreate.urlPlaceholderMulti')"
                        :aria-label="t('libraryCreate.urlLabel')"
                        @keydown.meta.enter.prevent="addFromUrl"
                        @keydown.ctrl.enter.prevent="addFromUrl"
                      />
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
                        {{
                          urlFetching
                            ? t('libraryCreate.urlFetching')
                            : t('libraryCreate.urlAdd')
                        }}
                      </button>
                    </div>
                    <p v-if="!urlFetching" class="lc-url-hint">{{ t('libraryCreate.urlMultiHint') }}</p>
                    <p
                      v-if="urlFetching"
                      class="lc-url-stage"
                      aria-live="polite"
                    >
                      <span class="lc-url-stage-index" aria-hidden="true">
                        {{ urlBatchStatusLine }}
                      </span>
                      <span class="lc-url-stage-msg">{{ urlFetchStageLabel }}</span>
                    </p>
                    <div
                      v-if="urlFailedLinks.length && !urlFetching"
                      class="lc-url-failed"
                      role="status"
                    >
                      <div class="lc-url-failed-head">
                        <span>{{ t('libraryCreate.urlFailedListTitle', { count: urlFailedLinks.length }) }}</span>
                        <button
                          class="lc-url-failed-dismiss"
                          type="button"
                          @click="dismissFailedUrls"
                        >
                          {{ t('libraryCreate.urlFailedDismiss') }}
                        </button>
                      </div>
                      <ul class="lc-url-failed-list">
                        <li v-for="link in urlFailedLinks" :key="link" :title="link">
                          {{ link }}
                        </li>
                      </ul>
                    </div>
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
                    <p class="lc-editor-empty-title">{{ t('libraryCreate.sourceEditorEmptyTitle') }}</p>
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
                      rows="4"
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

          <div v-else-if="showOptionsStep" key="options" class="lc-form-pane lc-options-pane">
            <section class="lc-options" :aria-label="t('libraryCreate.stepOptions')">
              <header class="lc-options-hero">
                <div class="lc-options-hero-copy">
                  <p class="lc-options-kicker">{{ t('libraryCreate.stepOptions') }}</p>
                  <h3 class="lc-options-title">{{ t('libraryCreate.optionsTitle') }}</h3>
                </div>
                <p class="lc-options-meta">
                  {{ t('libraryCreate.optionsSourcesReady', filledCount) }}
                </p>
              </header>

              <div class="lc-options-board">
                <div class="lc-panel lc-panel-modules">
                  <div class="lc-panel-head">
                    <h4 class="lc-options-label">{{ t('libraryCreate.stagesLabel') }}</h4>
                  </div>
                  <div class="lc-chip-row" role="group" :aria-label="t('libraryCreate.stagesLabel')">
                      <button
                        class="lc-chip"
                        type="button"
                        :aria-pressed="includeQuizzes"
                        :class="{ 'is-on': includeQuizzes }"
                        @click="includeQuizzes = !includeQuizzes"
                      >
                      <span class="lc-chip-glyph" aria-hidden="true">
                        <QuestionMarkCircleIcon class="lc-chip-icon" />
                      </span>
                      <span class="lc-chip-copy">
                        <span class="lc-chip-name">{{ t('libraryCreate.includeQuizzes') }}</span>
                        <span class="lc-chip-hint">{{ t('libraryCreate.moduleHintQuizzes') }}</span>
                      </span>
                    </button>
                      <button
                        class="lc-chip"
                        type="button"
                        :aria-pressed="includeCode"
                        :class="{ 'is-on': includeCode }"
                        @click="includeCode = !includeCode"
                      >
                      <span class="lc-chip-glyph" aria-hidden="true">
                        <CodeBracketIcon class="lc-chip-icon" />
                      </span>
                      <span class="lc-chip-copy">
                        <span class="lc-chip-name">{{ t('libraryCreate.includeCode') }}</span>
                        <span class="lc-chip-hint">{{ t('libraryCreate.moduleHintCode') }}</span>
                      </span>
                    </button>
                  </div>
                </div>

                <div class="lc-panel lc-panel-layout">
                  <div class="lc-options-row">
                    <div class="lc-panel-head">
                      <h4 class="lc-options-label">{{ t('libraryCreate.courseLayout') }}</h4>
                    </div>
                    <div
                      class="lc-segment lc-segment-2"
                      role="radiogroup"
                      :aria-label="t('libraryCreate.courseLayout')"
                    >
                      <button
                        v-for="option in layoutOptions"
                        :key="option.id"
                        class="lc-segment-item"
                        type="button"
                        role="radio"
                        :aria-checked="courseLayout === option.id"
                        :class="{ 'is-on': courseLayout === option.id }"
                        @click="courseLayout = option.id"
                      >
                        <span class="lc-segment-name">{{ option.label }}</span>
                        <span class="lc-segment-hint">{{ option.hint }}</span>
                      </button>
                    </div>
                  </div>

                  <div class="lc-options-row lc-options-depth">
                    <div class="lc-panel-head">
                      <h4 class="lc-options-label">{{ t('libraryCreate.courseDepth') }}</h4>
                    </div>
                    <div
                      class="lc-depth"
                      role="radiogroup"
                      :aria-label="t('libraryCreate.courseDepth')"
                    >
                      <button
                        v-for="option in depthOptions"
                        :key="option.id"
                        class="lc-depth-card"
                        type="button"
                        role="radio"
                        :aria-checked="courseDepth === option.id"
                        :class="{ 'is-on': courseDepth === option.id }"
                        @click="courseDepth = option.id"
                      >
                        <span class="lc-depth-name">{{ option.label }}</span>
                      </button>
                    </div>
                  </div>
                </div>

                <div class="lc-panel lc-panel-side">
                  <div class="lc-options-row lc-options-scale">
                    <div class="lc-panel-head">
                      <h4 class="lc-options-label">{{ t('libraryCreate.scaleLabel') }}</h4>
                    </div>
                    <div class="lc-scale-grid">
                      <div class="lc-scale-item" :class="{ 'is-off': !includeQuizzes }">
                        <div class="lc-scale-copy">
                          <span class="lc-scale-name">{{ quizCountLabel }}</span>
                          <span class="lc-scale-hint">{{ quizCountHint }}</span>
                        </div>
                        <div class="lc-stepper">
                          <button
                            class="lc-stepper-btn"
                            type="button"
                            :disabled="!includeQuizzes || quizCount <= 1"
                            @click="bumpQuiz(-1)"
                          >
                            −
                          </button>
                          <input
                            v-model.number="quizCount"
                            class="lc-stepper-input"
                            type="number"
                            min="1"
                            max="100"
                            :disabled="!includeQuizzes"
                            @blur="onQuizCountInput"
                          >
                          <button
                            class="lc-stepper-btn"
                            type="button"
                            :disabled="!includeQuizzes || quizCount >= 100"
                            @click="bumpQuiz(1)"
                          >
                            +
                          </button>
                        </div>
                      </div>

                      <div class="lc-scale-item" :class="{ 'is-off': !includeCode }">
                        <div class="lc-scale-copy">
                          <span class="lc-scale-name">{{ practiceCountLabel }}</span>
                          <span class="lc-scale-hint">{{ practiceMixHint }}</span>
                        </div>
                        <div class="lc-stepper">
                          <button
                            class="lc-stepper-btn"
                            type="button"
                            :disabled="!includeCode || practiceCount <= 0"
                            @click="bumpPractice(-1)"
                          >
                            −
                          </button>
                          <input
                            v-model.number="practiceCount"
                            class="lc-stepper-input"
                            type="number"
                            min="0"
                            max="12"
                            :disabled="!includeCode"
                            @blur="onPracticeCountInput"
                          >
                          <button
                            class="lc-stepper-btn"
                            type="button"
                            :disabled="!includeCode || practiceCount >= 12"
                            @click="bumpPractice(1)"
                          >
                            +
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div v-else key="progress" class="lc-progress-pane">
            <div
              v-if="codeGateOpen"
              class="lc-gate-panel"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="library-create-code-gate-title"
            >
              <h3 id="library-create-code-gate-title">{{ t('libraryCreate.codeGateTitle') }}</h3>
              <p class="lc-gate-lead">
                {{
                  t('libraryCreate.codeGateLead', {
                    score: codeGateScore == null ? '—' : Math.round(codeGateScore * 100),
                    profile: codeGateProfile || 'general',
                  })
                }}
              </p>
              <div class="lc-gate-actions">
                <button type="button" class="btn btn-secondary" @click="onCodeGateChoice('keep_code')">
                  {{ t('libraryCreate.codeGateKeep') }}
                </button>
                <button type="button" class="btn btn-secondary" @click="onCodeGateChoice('open_tasks')">
                  {{ t('libraryCreate.codeGateOpen') }}
                </button>
                <button type="button" class="btn btn-ghost" @click="onCodeGateChoice('no_practice')">
                  {{ t('libraryCreate.codeGateSkip') }}
                </button>
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
              :enabled-stages="enabledStages"
              :stage-labels="progressStageLabels"
              compact
            />
          </div>
          </Transition>
          </div>
        </div>

        <footer class="lc-footer" :class="{ 'is-progress-actions': !showForm }">
          <Transition name="page-cyber" mode="out-in">
            <div :key="footerPhase" class="lc-footer-inner">
              <div v-if="showOptionsStep" class="lc-footer-start">
                <p class="lc-footer-meta">{{ t('libraryCreate.optionsFooterHint') }}</p>
              </div>
              <p v-else-if="codeGateOpen" class="lc-footer-status">
                {{ t('libraryCreate.codeGateToast') }}
              </p>
              <p v-else-if="running" class="lc-footer-status">
                {{ t('libraryCreate.working') }}
              </p>
              <div class="lc-footer-actions">
                <template v-if="showSourcesStep">
                  <button
                    class="btn-primary"
                    type="button"
                    :disabled="!canGoNext"
                    @click="goNext"
                  >
                    {{ t('libraryCreate.next') }}
                    <ArrowRightIcon class="icon-sm" />
                  </button>
                </template>
                <template v-else-if="showOptionsStep">
                  <button class="btn-secondary" type="button" @click="goBack">
                    <ArrowLeftIcon class="icon-sm" />
                    {{ t('libraryCreate.back') }}
                  </button>
                  <button
                    class="btn-primary"
                    type="button"
                    :disabled="!canStart"
                    @click="runGenerate()"
                  >
                    <SparklesIcon class="icon-sm" />
                    {{ t('libraryCreate.build') }}
                  </button>
                </template>
                <template v-else-if="codeGateOpen">
                  <button class="btn-secondary" type="button" @click="onCancelGate">
                    {{ t('libraryCreate.gateCancel') }}
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
                <template v-else-if="error && activeBuildId">
                  <button class="btn-secondary" type="button" @click="emit('close')">
                    {{ t('libraryCreate.close') }}
                  </button>
                  <button class="btn-primary" type="button" @click="resumeActiveBuild">
                    {{ t('libraryCreate.resumeBuild') }}
                  </button>
                </template>
                <button
                  v-else
                  class="btn-primary"
                  type="button"
                  @click="emit('close')"
                >
                  {{ t('libraryCreate.done') }}
                </button>
              </div>
            </div>
          </Transition>
        </footer>
      </div>
      </div>
    </Transition>
  </Teleport>
</template>
