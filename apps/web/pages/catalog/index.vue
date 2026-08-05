<script setup lang="ts">
import {
  AcademicCapIcon,
  BookOpenIcon,
  CloudArrowDownIcon,
  CodeBracketIcon,
  CubeIcon,
  KeyIcon,
  MagnifyingGlassIcon,
  SignalIcon,
  SparklesIcon,
  TagIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'

import type {
  ExternalCourseSummary,
  PlatformCatalogBlock,
  SearchHit,
} from '~/composables/useSearch'
import type { PackSummary } from '~/composables/useCatalog'
import { useCatalogDownloads } from '~/composables/useCatalogDownloads'
import {
  relativeTime,
  sortSessionsByActivity,
} from '~/utils/session'
import { extractErrorMessage } from '~/utils/api'
import {
  buildCatalogCourseRows,
  buildLibrarySourceRails,
  canDownloadExternalCourse,
  canRedownloadPack,
  cardInitial as cardInitialGlyph,
  catalogOpenSourceAction,
  catalogQueryForTab,
  catalogTabFromQuery,
  courseCardMeta,
  courseDownloadKey as packDownloadKey,
  courseKey,
  emptyPackLearning,
  filterLibraryPacks,
  filterLibraryPacksBySource,
  groupCatalogCourseRows,
  indexSessionsForPacks,
  inferDisplayTags,
  isActivePackLearning,
  isBrokenPack,
  LIBRARY_SOURCE_LOCAL,
  libraryCardSubtitleText,
  matchSessionForPack,
  packContentTags,
  packLearningFromProgress,
  packPrimaryHref,
  platformHintText,
  settingsLinkForPlatform,
  stepikCardAction,
  stepikCourseUrl,
  type PackLearningSnapshot,
} from '~/utils/catalog'

type PackLearning = PackLearningSnapshot

const route = useRoute()
const router = useRouter()
const { t, te, locale } = useI18n()
useAppPageTitle(computed(() => t('nav.catalog')))
const { search, discoverCourses } = useSearch()
const { listPacks, deletePack } = useCatalog()
const { listCourseBuilds, discardCourseBuild } = useStudio()
const { listPackProgress } = useSessions()
const discoverCache = useDiscoverCache()
const toasts = useToasts()

const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const platformFilter = ref(typeof route.query.platform === 'string' ? route.query.platform : '')
const librarySourceFilter = ref('')
const tagFilter = ref('')
const activeTab = ref<'library' | 'external'>(catalogTabFromQuery(route.query.tab))

const workspaceTab = ref<'library' | 'external'>(activeTab.value)
// Snapshot state used inside Transition leaves/enters.
// `activeTab` changes immediately on click, but Transition leave/enter should keep
// the old DOM stable until the leave animation finishes.
const paneTab = ref<'library' | 'external'>(activeTab.value)
const showCourseCreate = ref(false)
const resumeBuildId = ref<string | null>(null)
const courseBuilds = ref<
  Array<{
    build_id: string
    title: string
    status: string
    stage: string
    progress: number
    message: string
    chapter_total: number
    chapters_done: number
    error?: string | null
    updated_at: string
  }>
>([])

function onCatalogPaneAfterLeave() {
  paneTab.value = activeTab.value
  if (activeTab.value === 'external') {
    workspaceTab.value = 'external'
  }
}

function onCatalogPaneAfterEnter() {
  if (activeTab.value === 'external') {
    workspaceTab.value = 'external'
  }
}

function onSourcesRailAfterLeave() {
  if (activeTab.value === 'library') {
    workspaceTab.value = 'library'
  }
}

function onLibraryRailAfterLeave() {
  if (activeTab.value === 'external') {
    workspaceTab.value = 'external'
  }
}

const platforms = ref<PlatformCatalogBlock[]>([])
const catalog = ref<ExternalCourseSummary[]>([])
const meiliHits = ref<SearchHit[]>([])
const packs = ref<PackSummary[]>([])
const packLearning = ref<Record<string, PackLearning>>({})
const pending = ref(false)
const catalogPending = ref(false)
const searched = ref(false)

const filteredPacks = computed(() => {
  if (paneTab.value !== 'library') {
    return packs.value
  }
  let result = filterLibraryPacks(packs.value, query.value)
  if (librarySourceFilter.value) {
    result = filterLibraryPacksBySource(result, librarySourceFilter.value)
  }
  return result
})

const librarySourceRails = computed(() =>
  buildLibrarySourceRails(packs.value, courseBuilds.value.length),
)

const libraryRailVisible = computed(
  () => packs.value.length > 0 || courseBuilds.value.length > 0,
)

const workspaceHasRail = computed(() => {
  // IMPORTANT: use `workspaceTab`, not `activeTab`.
  // `activeTab` changes immediately, while `workspaceTab` is updated in Transition
  // leave/enter hooks. If we depend on `activeTab`, `.has-rail` flips mid-animation,
  // and the rail column changes width (visible size "jump").
  if (workspaceTab.value === 'library') {
    return libraryRailVisible.value
  }
  if (workspaceTab.value === 'external') {
    return true
  }
  return false
})

const visibleCourseBuilds = computed(() => {
  if (paneTab.value !== 'library') {
    return []
  }
  if (!librarySourceFilter.value || librarySourceFilter.value === LIBRARY_SOURCE_LOCAL) {
    return courseBuilds.value
  }
  return []
})

const libraryVisibleCount = computed(
  () => filteredPacks.value.length + visibleCourseBuilds.value.length,
)

const allTags = computed(() => {
  const tags = new Set<string>()
  for (const course of catalog.value) {
    for (const tag of inferDisplayTags(course)) {
      tags.add(tag)
    }
  }
  return Array.from(tags).sort((a, b) => a.localeCompare(b))
})

const installedKeys = computed(() => {
  const keys = new Set<string>()
  for (const pack of packs.value) {
    if (pack.source && pack.external_id) {
      keys.add(courseKey(pack.source, pack.external_id))
    }
  }
  return keys
})

const courseRows = computed(() =>
  buildCatalogCourseRows({
    catalog: catalog.value,
    packs: packs.value,
    platformFilter: platformFilter.value,
    tagFilter: tagFilter.value,
    searched: searched.value,
    query: query.value,
    findInstalledPack: installedPack,
  }),
)

const groupedCourses = computed(() => groupCatalogCourseRows(courseRows.value))

const awaitingStepikEnrollment = computed(() =>
  courseRows.value.some((row) => row.platform === 'stepik' && row.enrolled !== true),
)

const pendingStepikRefresh = ref(false)
let stepikPollTimer: ReturnType<typeof setInterval> | null = null
let stepikRefreshInFlight = false

function markStepikReturnRefresh() {
  pendingStepikRefresh.value = true
}

async function refreshStepikCatalogIfNeeded() {
  if (activeTab.value !== 'external') {
    return
  }
  if (!pendingStepikRefresh.value && !awaitingStepikEnrollment.value) {
    return
  }
  if (stepikRefreshInFlight || catalogPending.value || pending.value) {
    return
  }
  stepikRefreshInFlight = true
  try {
    discoverCache.clear()
    await loadDiscover(query.value.trim(), { force: true })
    pendingStepikRefresh.value = false
  } finally {
    stepikRefreshInFlight = false
  }
}

function onWindowBecameVisible() {
  if (document.visibilityState !== 'visible') {
    return
  }
  void refreshStepikCatalogIfNeeded()
}

function syncStepikPollTimer() {
  const shouldPoll =
    activeTab.value === 'external' && (awaitingStepikEnrollment.value || pendingStepikRefresh.value)
  if (shouldPoll && stepikPollTimer === null) {
    stepikPollTimer = setInterval(() => {
      void refreshStepikCatalogIfNeeded()
    }, 45_000)
  } else if (!shouldPoll && stepikPollTimer !== null) {
    clearInterval(stepikPollTimer)
    stepikPollTimer = null
  }
}

const searchPlaceholder = computed(() =>
  activeTab.value === 'library'
    ? t('catalog.searchLibraryPlaceholder')
    : t('catalog.searchPlaceholder'),
)

function installedPack(platform: string, externalId: string) {
  return (
    packs.value.find((pack) => pack.source === platform && pack.external_id === externalId) ?? null
  )
}

function isInstalled(platform: string, externalId: string) {
  return installedKeys.value.has(courseKey(platform, externalId))
}

function isHealthyInstall(platform: string, externalId: string) {
  const pack = installedPack(platform, externalId)
  return Boolean(pack) && !isBrokenPack(pack)
}

function courseDownloadKey(pack: PackSummary) {
  return packDownloadKey(pack, courseKey)
}

async function refreshPacks() {
  try {
    packs.value = await listPacks()
  } catch {
    packs.value = []
  }
  await Promise.all([loadPackLearning(), refreshCourseBuilds()])
}

async function refreshCourseBuilds() {
  try {
    courseBuilds.value = await listCourseBuilds()
  } catch {
    courseBuilds.value = []
  }
}

function openCourseCreate(buildId: string | null = null) {
  resumeBuildId.value = buildId
  showCourseCreate.value = true
}

function closeCourseCreate() {
  showCourseCreate.value = false
  resumeBuildId.value = null
  void refreshCourseBuilds()
}

async function resumeCourseBuild(buildId: string) {
  openCourseCreate(buildId)
}

async function discardIncompleteBuild(build: { build_id: string; title: string }) {
  const { confirm } = useConfirm()
  const ok = await confirm({
    title: t('catalog.discardBuildConfirm', { title: build.title }),
    confirmLabel: t('dialog.delete'),
    cancelLabel: t('dialog.cancel'),
    danger: true,
  })
  if (!ok) {
    return
  }
  try {
    await discardCourseBuild(build.build_id)
    await refreshCourseBuilds()
  } catch (err) {
    toasts.error(extractErrorMessage(err) || t('catalog.errors.deleteFailed'))
  }
}

function buildStageLabel(stage: string) {
  const key = `courseBuild.stages.${stage}`
  return te(key) ? t(key) : stage
}

const {
  importStates,
  downloadQueue,
  isDownloadBusy,
  downloadProgressPercent,
  enqueueDownload,
} = useCatalogDownloads({
  isHealthyInstall,
  findInstalledTitle: (platform: string, externalId: string) =>
    installedPack(platform, externalId)?.title ?? null,
  refreshPacks,
  onEnrolled: async (platform: string, externalId: string) => {
    if (platform !== 'stepik') {
      return
    }
    catalog.value = catalog.value.map((course) =>
      course.platform === platform && course.external_id === externalId
        ? { ...course, enrolled: true }
        : course,
    )
    pendingStepikRefresh.value = true
    void refreshStepikCatalogIfNeeded()
  },
})

const activeImports = computed(
  () => Object.keys(importStates.value).length + downloadQueue.value.length,
)

function platformIcon(platform: string) {
  if (platform === 'stepik') {
    return AcademicCapIcon
  }
  if (platform === 'exercism' || platform === 'freecodecamp') {
    return CodeBracketIcon
  }
  return BookOpenIcon
}

function platformStatusLabel(status: PlatformCatalogBlock['status']) {
  return t(`catalog.platformStatus.${status}`)
}

function platformHint(platform: PlatformCatalogBlock) {
  return platformHintText(
    platform.message,
    t(`catalog.platformHints.${platform.platform_id}`, platform.display_name),
  )
}

function setTab(tab: 'library' | 'external') {
  if (tab === activeTab.value) {
    return
  }
  if (tab !== 'library') {
    librarySourceFilter.value = ''
  }
  activeTab.value = tab
  void router.replace({
    query: catalogQueryForTab(route.query as Record<string, string>, tab),
  })
}

function openLibrarySource(sourceId: string) {
  librarySourceFilter.value = librarySourceFilter.value === sourceId ? '' : sourceId
}

function librarySourceLabel(sourceId: string) {
  if (sourceId === LIBRARY_SOURCE_LOCAL) {
    return t('catalog.libraryLocal')
  }
  return sourceLabel(sourceId)
}

function librarySourceMeta(sourceId: string) {
  if (sourceId === LIBRARY_SOURCE_LOCAL) {
    return t('catalog.libraryLocalMeta')
  }
  return t('catalog.librarySourceMeta')
}

async function focusIncompleteBuilds(event?: Event) {
  event?.stopPropagation()
  if (!courseBuilds.value.length) {
    return
  }
  if (activeTab.value !== 'library') {
    setTab('library')
    await nextTick()
    await nextTick()
  }
  document
    .getElementById('catalog-incomplete-builds')
    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function packPrimaryTo(pack: PackSummary) {
  return packPrimaryHref(pack.id, packLearning.value[pack.id])
}

function packPrimaryLabel(pack: PackSummary) {
  return isActivePackLearning(packLearning.value[pack.id])
    ? t('catalog.continueCourse')
    : t('catalog.openCourse')
}

function cardInitial(title: string) {
  return cardInitialGlyph(title, locale.value)
}

function libraryCardSubtitle(pack: PackSummary) {
  const learning = packLearning.value[pack.id]
  return libraryCardSubtitleText({
    title: pack.title,
    slug: pack.slug,
    version: pack.version,
    chapter: learning?.chapter,
    progress: learning?.progress,
    emptyLabel: t('catalog.noProgressYet'),
  })
}

async function loadPackLearning() {
  if (!packs.value.length) {
    packLearning.value = {}
    return
  }
  try {
    const items = sortSessionsByActivity(await listPackProgress())
    const indexes = indexSessionsForPacks(items)
    const byId = new Map(items.map((item) => [item.id, item]))
    const emptyChapter = t('catalog.noProgressYet')

    const next: Record<string, PackLearning> = {}
    for (const pack of packs.value) {
      const summary = matchSessionForPack(pack, indexes)
      const item = summary ? byId.get(summary.id) : undefined
      next[pack.id] = item
        ? packLearningFromProgress(item, emptyChapter)
        : emptyPackLearning()
    }
    packLearning.value = next
  } catch {
    packLearning.value = {}
  }
}

function selectPlatform(platformId: string) {
  platformFilter.value = platformFilter.value === platformId ? '' : platformId
  setTab('external')
}

function openSource(platform: PlatformCatalogBlock) {
  if (catalogOpenSourceAction(platform.status) === 'settings') {
    navigateTo(settingsLinkForPlatform(platform.platform_id))
    return
  }
  selectPlatform(platform.platform_id)
}

async function loadDiscover(searchQuery = '', { force = false } = {}) {
  catalogPending.value = true
  try {
    if (!force) {
      const cached = discoverCache.read(searchQuery)
      if (cached?.platforms && cached?.courses) {
        platforms.value = cached.platforms
        catalog.value = cached.courses
        return
      }
    }
    const response = await discoverCourses(searchQuery || undefined)
    platforms.value = response.platforms ?? []
    catalog.value = response.courses ?? []
    if (catalog.value.length || platforms.value.some((item) => item.status === 'ready' || item.status === 'needs_auth')) {
      discoverCache.write(searchQuery, {
        platforms: platforms.value,
        courses: catalog.value,
      })
    } else {
      discoverCache.clear()
    }
  } catch (error) {
    platforms.value = []
    catalog.value = []
    toasts.error(extractErrorMessage(error) || t('search.errors.catalogFailed'))
  } finally {
    catalogPending.value = false
  }
}

async function runSearch() {
  if (activeTab.value === 'library') {
    return
  }
  const needle = query.value.trim()
  pending.value = true
  searched.value = Boolean(needle)
  discoverCache.clear()
  try {
    await Promise.all([
      loadDiscover(needle, { force: true }),
      (async () => {
        if (!needle) {
          meiliHits.value = []
          return
        }
        try {
          const response = await search(needle)
          meiliHits.value = response.hits
        } catch {
          meiliHits.value = []
        }
      })(),
      refreshPacks(),
    ])
  } finally {
    pending.value = false
  }
}

async function onCourseInstalled() {
  discoverCache.clear()
  await Promise.all([
    refreshPacks(),
    loadDiscover(query.value.trim(), { force: true }),
  ])
  closeCourseCreate()
  setTab('library')
}

async function removeLocalPack(pack: PackSummary) {
  const { confirm } = useConfirm()
  const ok = await confirm({
    title: t('catalog.deleteConfirm', { title: pack.title }),
    confirmLabel: t('dialog.delete'),
    cancelLabel: t('dialog.cancel'),
    danger: true,
  })
  if (!ok) {
    return
  }
  try {
    await deletePack(pack.id)
    packs.value = packs.value.filter((item) => item.id !== pack.id)
    toasts.success(t('catalog.deleted'))
    discoverCache.clear()
    await Promise.all([refreshPacks(), loadDiscover(query.value.trim(), { force: true })])
  } catch (error) {
    toasts.error(extractErrorMessage(error) || t('catalog.errors.deleteFailed'))
    await refreshPacks()
  }
}

async function redownloadPack(pack: PackSummary) {
  if (!canRedownloadPack(pack) || !pack.external_id) {
    return
  }
  const key = courseDownloadKey(pack)
  if (isDownloadBusy(key)) {
    return
  }
  const { confirm } = useConfirm()
  const ok = await confirm({
    title: t('catalog.redownloadConfirm', { title: pack.title }),
    confirmLabel: t('catalog.redownloadCourse'),
    cancelLabel: t('dialog.cancel'),
  })
  if (!ok) {
    return
  }
  toasts.success(t('catalog.redownloadStarted', { title: pack.title }))
  enqueueDownload(pack.source, pack.external_id, true)
}

function sourceLabel(source: string) {
  return t(`search.sources.${source}`, source)
}

watch(
  () => route.query.platform,
  (value) => {
    platformFilter.value = typeof value === 'string' ? value : ''
  },
  { immediate: true },
)

watch(
  () => route.query.tab,
  (value) => {
    const next = catalogTabFromQuery(value)
    if (next !== activeTab.value) {
      activeTab.value = next
    }
  },
)

watch([activeTab, awaitingStepikEnrollment, pendingStepikRefresh], () => {
  syncStepikPollTimer()
})

onMounted(async () => {
  window.addEventListener('focus', onWindowBecameVisible)
  document.addEventListener('visibilitychange', onWindowBecameVisible)
  await refreshPacks()
  await loadDiscover(query.value.trim())
  syncStepikPollTimer()
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', onWindowBecameVisible)
  document.removeEventListener('visibilitychange', onWindowBecameVisible)
  if (stepikPollTimer !== null) {
    clearInterval(stepikPollTimer)
    stepikPollTimer = null
  }
})
</script>

<template>
  <PageShell :title="t('catalog.title')" :meta="t('catalog.subtitle')">
    <div class="catalog-root">
      <header class="catalog-toolbar">
        <div class="catalog-segment" role="tablist" :aria-label="t('catalog.modeLabel')">
          <button
            class="catalog-segment-btn"
            :class="{ 'is-active': activeTab === 'library' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'library'"
            @click="setTab('library')"
          >
            <BookOpenIcon class="icon-sm" />
            <span>{{ t('catalog.tabLibrary') }}</span>
            <span class="catalog-segment-count">{{ packs.length }}</span>
            <span
              v-if="courseBuilds.length"
              class="catalog-segment-incomplete"
              role="button"
              tabindex="0"
              :title="t('catalog.incompleteBuildsHint', { count: courseBuilds.length })"
              :aria-label="t('catalog.incompleteBuildsHint', { count: courseBuilds.length })"
              @click.stop="focusIncompleteBuilds"
              @keydown.enter.prevent.stop="focusIncompleteBuilds"
              @keydown.space.prevent.stop="focusIncompleteBuilds"
            >
              {{ courseBuilds.length }}
            </span>
          </button>
          <button
            class="catalog-segment-btn"
            :class="{ 'is-active': activeTab === 'external' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'external'"
            @click="setTab('external')"
          >
            <CloudArrowDownIcon class="icon-sm" />
            <span>{{ t('catalog.tabDiscover') }}</span>
            <span v-if="activeImports" class="catalog-segment-count">{{ activeImports }}</span>
          </button>
        </div>

        <div class="catalog-toolbar-tools">
          <form
            class="catalog-search-form"
            :class="{ 'is-library-filter': activeTab === 'library' }"
            @submit.prevent="runSearch"
          >
            <div class="catalog-searchbar">
              <MagnifyingGlassIcon class="catalog-searchbar-icon" aria-hidden="true" />
              <input
                v-model="query"
                class="catalog-searchbar-input"
                type="search"
                :placeholder="searchPlaceholder"
              >
            </div>
            <Transition name="page-cyber">
              <button
                v-if="activeTab === 'external' && workspaceTab === 'external'"
                key="catalog-search-submit"
                class="btn-primary btn-sm catalog-search-submit"
                type="submit"
                :disabled="pending || catalogPending"
              >
                {{ pending || catalogPending ? t('search.loading') : t('search.submit') }}
              </button>
            </Transition>
          </form>

          <Transition name="page-cyber">
            <button
              v-if="activeTab === 'external' && workspaceTab === 'external'"
              key="catalog-toolbar-cta"
              class="btn-primary btn-sm catalog-toolbar-cta"
              type="button"
              @click="openCourseCreate()"
            >
              <SparklesIcon class="icon-sm" />
              {{ t('libraryCreate.open') }}
            </button>
          </Transition>
        </div>
      </header>

      <ClientOnly>
        <LibraryCourseCreate
          :open="showCourseCreate"
          :resume-build-id="resumeBuildId"
          @close="closeCourseCreate"
          @installed="onCourseInstalled"
          @update:resume-build-id="resumeBuildId = $event"
        />
      </ClientOnly>

      <div
        class="catalog-workspace"
        :class="{
          'is-library': workspaceTab === 'library',
          'is-discover': workspaceTab === 'external',
          'has-rail': workspaceHasRail,
        }"
      >
        <Transition name="page-cyber" @after-leave="onSourcesRailAfterLeave">
          <aside
            v-if="activeTab === 'external' && workspaceTab === 'external'"
            key="sources-rail"
            class="catalog-rail"
          >
            <section class="catalog-rail-panel">
              <header class="catalog-rail-head">
                <h3 class="catalog-rail-title">{{ t('catalog.platformsTitle') }}</h3>
                <NuxtLink class="btn-ghost btn-sm" to="/settings" :title="t('catalog.openSettings')">
                  <KeyIcon class="icon-sm" />
                </NuxtLink>
              </header>

              <div v-if="catalogPending && !platforms.length" class="loading-state catalog-loading">
                <span class="loading-spinner" aria-hidden="true" />
              </div>

              <div v-else class="catalog-source-list">
                <button
                  class="catalog-source-item"
                  :class="{ 'catalog-source-item-active': !platformFilter }"
                  type="button"
                  @click="platformFilter = ''"
                >
                  <span class="catalog-source-icon" aria-hidden="true">
                    <CubeIcon class="icon-sm" />
                  </span>
                  <span class="catalog-source-copy">
                    <span class="catalog-source-name">{{ t('catalog.allPlatforms') }}</span>
                    <span class="catalog-source-meta">{{ t('catalog.allPlatformsMeta') }}</span>
                  </span>
                  <span class="catalog-source-count">{{ catalog.length }}</span>
                </button>

                <button
                  v-for="platform in platforms"
                  :key="platform.platform_id"
                  class="catalog-source-item"
                  :class="{ 'catalog-source-item-active': platformFilter === platform.platform_id }"
                  type="button"
                  :title="platformHint(platform)"
                  @click="openSource(platform)"
                >
                  <span class="catalog-source-icon" aria-hidden="true">
                    <component :is="platformIcon(platform.platform_id)" class="icon-sm" />
                  </span>
                  <span class="catalog-source-copy">
                    <span class="catalog-source-name">{{ platform.display_name }}</span>
                    <span class="catalog-source-meta">
                      <span
                        class="catalog-dot"
                        :class="`catalog-dot-${platform.status}`"
                        aria-hidden="true"
                      />
                      {{ platformStatusLabel(platform.status) }}
                    </span>
                  </span>
                  <span class="catalog-source-count">{{ platform.course_count }}</span>
                </button>
              </div>

              <p class="catalog-rail-footnote">{{ t('catalog.railFootnote') }}</p>
            </section>
          </aside>
        </Transition>

        <Transition name="page-cyber" @after-leave="onLibraryRailAfterLeave">
          <aside
            v-if="activeTab === 'library' && workspaceTab === 'library' && libraryRailVisible"
            key="library-sources-rail"
            class="catalog-rail"
          >
            <section class="catalog-rail-panel">
              <header class="catalog-rail-head">
                <h3 class="catalog-rail-title">{{ t('catalog.platformsTitle') }}</h3>
              </header>

              <div class="catalog-source-list">
                <button
                  class="catalog-source-item"
                  :class="{ 'catalog-source-item-active': !librarySourceFilter }"
                  type="button"
                  @click="librarySourceFilter = ''"
                >
                  <span class="catalog-source-icon" aria-hidden="true">
                    <CubeIcon class="icon-sm" />
                  </span>
                  <span class="catalog-source-copy">
                    <span class="catalog-source-name">{{ t('catalog.allPlatforms') }}</span>
                    <span class="catalog-source-meta">{{ t('catalog.allPlatformsMeta') }}</span>
                  </span>
                  <span class="catalog-source-count">{{ librarySourceRails.total }}</span>
                </button>

                <button
                  v-for="source in librarySourceRails.sources"
                  :key="source.id"
                  class="catalog-source-item"
                  :class="{ 'catalog-source-item-active': librarySourceFilter === source.id }"
                  type="button"
                  @click="openLibrarySource(source.id)"
                >
                  <span class="catalog-source-icon" aria-hidden="true">
                    <component
                      :is="source.id === LIBRARY_SOURCE_LOCAL ? BookOpenIcon : platformIcon(source.id)"
                      class="icon-sm"
                    />
                  </span>
                  <span class="catalog-source-copy">
                    <span class="catalog-source-name">{{ librarySourceLabel(source.id) }}</span>
                    <span class="catalog-source-meta">{{ librarySourceMeta(source.id) }}</span>
                  </span>
                  <span class="catalog-source-count">{{ source.count }}</span>
                </button>
              </div>

              <p class="catalog-rail-footnote">{{ t('catalog.libraryRailFootnote') }}</p>
            </section>
          </aside>
        </Transition>

        <section class="catalog-main">
          <Transition
            name="page-cyber"
            mode="out-in"
            @after-leave="onCatalogPaneAfterLeave"
            @after-enter="onCatalogPaneAfterEnter"
          >
            <div :key="activeTab" class="catalog-pane">
          <header class="catalog-command">
            <div class="catalog-command-copy">
              <h2>
                {{
                  paneTab === 'library'
                    ? librarySourceFilter
                      ? librarySourceLabel(librarySourceFilter)
                      : t('catalog.libraryTitle')
                    : platformFilter
                      ? sourceLabel(platformFilter)
                      : t('catalog.externalTitle')
                }}
              </h2>
              <p>
                {{
                  paneTab === 'library'
                    ? t('catalog.libraryCount', { count: libraryVisibleCount })
                    : t('catalog.externalMeta')
                }}
              </p>
            </div>
            <div class="catalog-command-tools">
              <button
                v-if="librarySourceFilter && paneTab === 'library'"
                class="btn-secondary btn-sm"
                type="button"
                @click="librarySourceFilter = ''"
              >
                {{ t('catalog.clearFilter') }}
              </button>
              <button
                v-if="platformFilter && paneTab === 'external'"
                class="btn-secondary btn-sm"
                type="button"
                @click="platformFilter = ''"
              >
                {{ t('catalog.clearFilter') }}
              </button>
            </div>
          </header>

          <div
            v-if="paneTab === 'external' && allTags.length"
            class="catalog-tags"
          >
            <button
              type="button"
              class="catalog-tag"
              :class="{ 'catalog-tag-active': !tagFilter }"
              @click="tagFilter = ''"
            >
              {{ t('search.allTags') }}
            </button>
            <button
              v-for="tag in allTags"
              :key="tag"
              type="button"
              class="catalog-tag"
              :class="{ 'catalog-tag-active': tagFilter === tag }"
              @click="tagFilter = tagFilter === tag ? '' : tag"
            >
              <TagIcon class="icon-sm" />
              {{ tag }}
            </button>
          </div>

          <div class="catalog-scroll">
            <div
              v-if="catalogPending && paneTab === 'external' && !courseRows.length"
              class="loading-state catalog-loading"
            >
              <span class="loading-spinner" aria-hidden="true" />
              <span>{{ t('search.loading') }}</span>
            </div>

            <template v-else-if="paneTab === 'library'">
              <Transition name="page-cyber" mode="out-in">
                <div
                  :key="librarySourceFilter || 'all'"
                  class="catalog-discover-swap"
                >
              <div v-if="!packs.length && !courseBuilds.length" class="catalog-empty">
                <div class="catalog-empty-visual">
                  <BookOpenIcon class="icon-md" />
                </div>
                <p class="catalog-empty-title">{{ t('catalog.empty') }}</p>
                <p class="catalog-empty-meta">{{ t('catalog.emptyLibraryMeta') }}</p>
                <div class="catalog-empty-actions">
                  <button class="btn-primary" type="button" @click="setTab('external')">
                    <CloudArrowDownIcon class="icon-sm" />
                    {{ t('catalog.goDiscover') }}
                  </button>
                </div>
              </div>

              <div v-else-if="!filteredPacks.length && !visibleCourseBuilds.length" class="catalog-empty">
                <p class="catalog-empty-title">
                  {{
                    librarySourceFilter
                      ? t('catalog.libraryFilterEmpty')
                      : t('catalog.librarySearchEmpty')
                  }}
                </p>
                <p class="catalog-empty-meta">
                  {{
                    librarySourceFilter
                      ? t('catalog.libraryFilterEmptyMeta')
                      : t('catalog.librarySearchEmptyMeta')
                  }}
                </p>
                <div v-if="librarySourceFilter" class="catalog-empty-actions">
                  <button class="btn-secondary btn-sm" type="button" @click="librarySourceFilter = ''">
                    {{ t('catalog.clearFilter') }}
                  </button>
                </div>
              </div>

              <div v-else class="catalog-pack-grid catalog-library-grid">
                <article
                  v-for="(build, buildIndex) in visibleCourseBuilds"
                  :id="buildIndex === 0 ? 'catalog-incomplete-builds' : undefined"
                  :key="`build-${build.build_id}`"
                  class="lib-card is-incomplete"
                  :style="{ '--progress': Math.round((build.progress || 0) * 100) }"
                >
                  <header class="lib-card-head">
                    <span class="lib-card-code" aria-hidden="true">··</span>
                    <div class="lib-card-tags">
                      <span class="lib-tag is-incomplete">{{ t('catalog.incompleteBuild') }}</span>
                    </div>
                    <span class="lib-card-time">
                      {{ relativeTime(build.updated_at, locale) }}
                    </span>
                  </header>

                  <div class="lib-card-body">
                    <p class="lib-card-mark" aria-hidden="true">{{ cardInitial(build.title) }}</p>
                    <h3 class="lib-card-title">{{ build.title }}</h3>
                    <p class="lib-card-subtitle">
                      {{
                        t('catalog.buildProgressMeta', {
                          stage: buildStageLabel(build.stage),
                          done: build.chapters_done,
                          total: build.chapter_total || '—',
                        })
                      }}
                    </p>
                  </div>

                  <footer class="lib-card-foot">
                    <div
                      class="lib-card-progress"
                      role="progressbar"
                      :aria-valuenow="Math.round((build.progress || 0) * 100)"
                      aria-valuemin="0"
                      aria-valuemax="100"
                    >
                      <span class="lib-card-pct">
                        {{ Math.round((build.progress || 0) * 100) }}%
                      </span>
                      <div class="lib-card-track" aria-hidden="true">
                        <span
                          class="lib-card-fill"
                          :style="{ width: `${Math.round((build.progress || 0) * 100)}%` }"
                        />
                      </div>
                    </div>
                    <div class="lib-card-actions">
                      <button
                        class="lib-card-cta"
                        type="button"
                        @click="resumeCourseBuild(build.build_id)"
                      >
                        {{ t('catalog.resumeGeneration') }}
                        <span class="lib-card-cta-arrow" aria-hidden="true">→</span>
                      </button>
                      <button
                        class="lib-card-delete"
                        type="button"
                        :aria-label="t('catalog.discardBuild')"
                        :title="t('catalog.discardBuild')"
                        @click="discardIncompleteBuild(build)"
                      >
                        <TrashIcon class="icon-sm" />
                      </button>
                    </div>
                  </footer>
                </article>

                <article
                  v-for="(pack, packIndex) in filteredPacks"
                  :key="pack.id"
                  class="lib-card"
                  :style="{
                    '--progress': packLearning[pack.id]?.progress ?? 0,
                  }"
                >
                  <header class="lib-card-head">
                    <span class="lib-card-code" aria-hidden="true">
                      {{ String(packIndex + 1).padStart(2, '0') }}
                    </span>
                    <div class="lib-card-tags">
                      <span
                        v-if="pack.source && pack.source !== 'local'"
                        class="lib-tag"
                      >
                        {{ sourceLabel(pack.source) }}
                      </span>
                      <span v-else class="lib-tag">{{ t('search.sources.local') }}</span>
                      <span
                        v-for="tagId in packContentTags(pack)"
                        :key="tagId"
                        class="lib-tag"
                        :class="`is-content-${tagId}`"
                      >
                        {{ t(`catalog.contentTags.${tagId}`) }}
                      </span>
                      <span
                        v-if="isBrokenPack(pack)"
                        class="lib-tag is-broken"
                        :title="t('catalog.integrityBrokenMeta')"
                      >
                        {{ t('catalog.integrityBroken') }}
                      </span>
                    </div>
                    <span
                      v-if="packLearning[pack.id]?.updatedAt"
                      class="lib-card-time"
                    >
                      {{ relativeTime(packLearning[pack.id].updatedAt!, locale) }}
                    </span>
                  </header>

                  <div class="lib-card-body">
                    <p class="lib-card-mark" aria-hidden="true">{{ cardInitial(pack.title) }}</p>
                    <h3 class="lib-card-title">{{ pack.title }}</h3>
                    <p class="lib-card-subtitle">{{ libraryCardSubtitle(pack) }}</p>
                  </div>

                  <footer class="lib-card-foot">
                    <div
                      class="lib-card-progress"
                      role="progressbar"
                      :aria-valuenow="packLearning[pack.id]?.progress ?? 0"
                      aria-valuemin="0"
                      aria-valuemax="100"
                      :aria-label="t('catalog.progressLabel', { value: packLearning[pack.id]?.progress ?? 0 })"
                    >
                      <span class="lib-card-pct">
                        {{
                          packLearning[pack.id]?.progress == null
                            ? '—'
                            : `${packLearning[pack.id].progress}%`
                        }}
                      </span>
                      <div class="lib-card-track" aria-hidden="true">
                        <span
                          class="lib-card-fill"
                          :style="{
                            width: `${packLearning[pack.id]?.progress ?? 0}%`,
                          }"
                        />
                      </div>
                    </div>

                    <div class="lib-card-actions">
                      <button
                        v-if="canRedownloadPack(pack)"
                        class="lib-card-cta"
                        :class="{ 'is-progress': isDownloadBusy(courseDownloadKey(pack)) }"
                        type="button"
                        :disabled="isDownloadBusy(courseDownloadKey(pack))"
                        :aria-busy="isDownloadBusy(courseDownloadKey(pack)) || undefined"
                        @click="redownloadPack(pack)"
                      >
                        <span
                          v-if="isDownloadBusy(courseDownloadKey(pack))"
                          class="lib-card-cta-fill"
                          :style="{ width: `${downloadProgressPercent(courseDownloadKey(pack))}%` }"
                          aria-hidden="true"
                        />
                        <span class="lib-card-cta-label">
                          <template v-if="isDownloadBusy(courseDownloadKey(pack))">
                            <span class="loading-spinner loading-spinner-sm" aria-hidden="true" />
                            {{ t('catalog.downloadingCourse') }}
                          </template>
                          <template v-else>
                            {{ t('catalog.redownloadCourse') }}
                            <span class="lib-card-cta-arrow" aria-hidden="true">→</span>
                          </template>
                        </span>
                      </button>
                      <NuxtLink
                        v-else
                        class="lib-card-cta"
                        :to="packPrimaryTo(pack)"
                      >
                        {{ packPrimaryLabel(pack) }}
                        <span class="lib-card-cta-arrow" aria-hidden="true">→</span>
                      </NuxtLink>
                      <button
                        class="lib-card-delete"
                        type="button"
                        :aria-label="t('catalog.delete')"
                        :title="t('catalog.delete')"
                        @click="removeLocalPack(pack)"
                      >
                        <TrashIcon class="icon-sm" />
                      </button>
                    </div>
                  </footer>
                </article>
              </div>
                </div>
              </Transition>
            </template>

            <template v-else>
              <Transition name="page-cyber" mode="out-in">
                <div
                  :key="`${platformFilter || 'all'}|${tagFilter || 'all'}`"
                  class="catalog-discover-swap"
                >
              <div v-if="courseRows.length === 0" class="catalog-empty">
                <div class="catalog-empty-visual">
                  <SignalIcon class="icon-md" />
                </div>
                <p class="catalog-empty-title">
                  {{ searched ? t('search.empty') : t('catalog.externalEmptyTitle') }}
                </p>
                <p class="catalog-empty-meta">{{ t('catalog.externalEmptyMeta') }}</p>
                <NuxtLink class="btn-primary btn-sm" to="/settings">
                  <KeyIcon class="icon-sm" />
                  {{ t('catalog.openSettings') }}
                </NuxtLink>
              </div>

              <div v-else class="catalog-stack">
                <section
                  v-for="[platformId, rows] in groupedCourses"
                  :key="platformId"
                  class="disc-group"
                >
                  <div class="disc-group-head">
                    <span class="disc-group-icon" aria-hidden="true">
                      <component :is="platformIcon(platformId)" class="icon-sm" />
                    </span>
                    <div class="disc-group-copy">
                      <strong>{{ sourceLabel(platformId) }}</strong>
                      <span>{{ t('catalog.groupCount', { count: rows.length }) }}</span>
                    </div>
                  </div>

                  <div class="catalog-pack-grid catalog-library-grid">
                    <article
                      v-for="(row, index) in rows"
                      :key="row.key"
                      class="lib-card"
                      :data-platform="row.platform"
                    >
                      <header class="lib-card-head">
                        <span class="lib-card-code" aria-hidden="true">
                          {{ String(index + 1).padStart(2, '0') }}
                        </span>
                        <div class="lib-card-tags">
                          <span class="lib-tag">{{ sourceLabel(row.platform) }}</span>
                          <span v-if="row.language" class="lib-tag">{{ row.language }}</span>
                          <span
                            v-if="row.platform === 'stepik' && row.enrolled === true"
                            class="lib-tag is-enrolled"
                          >
                            {{ t('catalog.onAccount') }}
                          </span>
                          <span
                            v-else-if="row.platform === 'stepik' && row.enrolled === false"
                            class="lib-tag is-remote"
                          >
                            {{ t('catalog.notOnAccount') }}
                          </span>
                          <span
                            v-if="row.platform === 'stepik' && row.isPaid === true"
                            class="lib-tag is-paid"
                          >
                            {{ t('catalog.paidCourse') }}
                          </span>
                          <span
                            v-else-if="row.platform === 'stepik' && row.isPaid === false"
                            class="lib-tag is-free"
                          >
                            {{ t('catalog.freeCourse') }}
                          </span>
                          <span
                            v-if="row.packId || isInstalled(row.platform, row.externalId)"
                            class="lib-tag"
                          >
                            {{ t('search.installed') }}
                          </span>
                          <span
                            v-if="isBrokenPack(installedPack(row.platform, row.externalId))"
                            class="lib-tag is-broken"
                            :title="t('catalog.integrityBrokenMeta')"
                          >
                            {{ t('catalog.integrityBroken') }}
                          </span>
                        </div>
                      </header>

                      <div class="lib-card-body">
                        <p class="lib-card-mark" aria-hidden="true">{{ cardInitial(row.title) }}</p>
                        <h3 class="lib-card-title">{{ row.title }}</h3>
                        <p class="lib-card-subtitle">{{ courseCardMeta(row) }}</p>
                        <p
                          v-if="row.platform === 'stepik' && !canDownloadExternalCourse(row)"
                          class="lib-card-note"
                        >
                          {{
                            stepikCardAction(row) === 'goto'
                              ? t('catalog.stepikPaidHint')
                              : t('catalog.stepikEnrollHint')
                          }}
                        </p>
                      </div>

                      <footer class="lib-card-foot">
                        <div class="lib-card-actions">
                          <NuxtLink
                            v-if="isHealthyInstall(row.platform, row.externalId)"
                            class="lib-card-cta"
                            :to="`/catalog/${row.packId || installedPack(row.platform, row.externalId)?.id}`"
                          >
                            {{ t('catalog.openCourse') }}
                            <span class="lib-card-cta-arrow" aria-hidden="true">→</span>
                          </NuxtLink>
                          <a
                            v-else-if="stepikCardAction(row) === 'goto'"
                            class="lib-card-cta"
                            :href="stepikCourseUrl(row.externalId)"
                            target="_blank"
                            rel="noopener noreferrer"
                            @click="markStepikReturnRefresh"
                          >
                            {{ t('catalog.openOnStepikPaid') }}
                            <span class="lib-card-cta-arrow" aria-hidden="true">→</span>
                          </a>
                          <button
                            v-else
                            class="lib-card-cta"
                            :class="{ 'is-progress': isDownloadBusy(row.key) }"
                            type="button"
                            :disabled="isDownloadBusy(row.key)"
                            :aria-busy="isDownloadBusy(row.key) || undefined"
                            :aria-valuenow="
                              isDownloadBusy(row.key) ? downloadProgressPercent(row.key) : undefined
                            "
                            :aria-valuemin="isDownloadBusy(row.key) ? 0 : undefined"
                            :aria-valuemax="isDownloadBusy(row.key) ? 100 : undefined"
                            role="button"
                            @click="
                              enqueueDownload(
                                row.platform,
                                row.externalId,
                                isBrokenPack(installedPack(row.platform, row.externalId)),
                                { enrollFirst: stepikCardAction(row) === 'enroll' },
                              )
                            "
                          >
                            <span
                              v-if="isDownloadBusy(row.key)"
                              class="lib-card-cta-fill"
                              :style="{ width: `${downloadProgressPercent(row.key)}%` }"
                              aria-hidden="true"
                            />
                            <span class="lib-card-cta-label">
                              <template v-if="isDownloadBusy(row.key)">
                                <span class="loading-spinner loading-spinner-sm" aria-hidden="true" />
                                {{
                                  importStates[row.key]?.status === 'enrolling'
                                    ? t('catalog.enrollingOnStepik')
                                    : t('catalog.downloadingCourse')
                                }}
                              </template>
                              <template v-else>
                                {{
                                  isBrokenPack(installedPack(row.platform, row.externalId))
                                    ? t('catalog.redownloadCourse')
                                    : t('catalog.downloadCourse')
                                }}
                                <span class="lib-card-cta-arrow" aria-hidden="true">→</span>
                              </template>
                            </span>
                          </button>
                        </div>
                      </footer>
                    </article>
                  </div>
                </section>
              </div>
                </div>
              </Transition>
            </template>
          </div>
            </div>
          </Transition>
        </section>
      </div>
    </div>
  </PageShell>
</template>
