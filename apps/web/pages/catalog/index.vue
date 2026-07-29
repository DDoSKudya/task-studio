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
import type { SessionState, SessionSummary } from '~/composables/useSessions'
import {
  relativeTime,
  sortSessionsByActivity,
} from '~/utils/session'
import { extractErrorMessage } from '~/utils/api'
import {
  buildCatalogCourseRows,
  canRedownloadPack,
  cardInitial as cardInitialGlyph,
  catalogOpenSourceAction,
  catalogQueryForTab,
  catalogTabFromQuery,
  chapterTitleFromOutline,
  courseCardMeta,
  courseDownloadKey as packDownloadKey,
  courseKey,
  emptyPackLearning,
  filterLibraryPacks,
  groupCatalogCourseRows,
  indexSessionsForPacks,
  inferDisplayTags,
  isActivePackLearning,
  isBrokenPack,
  libraryCardSubtitleText,
  matchSessionForPack,
  packLearningFromSession,
  packPrimaryHref,
  platformHintText,
  settingsLinkForPlatform,
  type PackLearningSnapshot,
} from '~/utils/catalog'


type PackLearning = PackLearningSnapshot

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const { search, discoverCourses } = useSearch()
const { listPacks, deletePack } = useCatalog()
const { listSessions, getSession } = useSessions()
const discoverCache = useDiscoverCache()
const toasts = useToasts()

const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const platformFilter = ref(typeof route.query.platform === 'string' ? route.query.platform : '')
const tagFilter = ref('')
const activeTab = ref<'library' | 'external'>(catalogTabFromQuery(route.query.tab))

const workspaceTab = ref<'library' | 'external'>(activeTab.value)
const showCourseCreate = ref(false)

watch(activeTab, (tab) => {
  if (tab === 'external') {
    workspaceTab.value = 'external'
  }
})

function onSourcesRailAfterLeave() {
  if (activeTab.value === 'library') {
    workspaceTab.value = 'library'
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
  if (activeTab.value !== 'library') {
    return packs.value
  }
  return filterLibraryPacks(packs.value, query.value)
})

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
  await loadPackLearning()
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
  activeTab.value = tab
  void router.replace({
    query: catalogQueryForTab(route.query as Record<string, string>, tab),
  })
}

function chapterTitle(detail: SessionState | null, summary: SessionSummary): string {
  return chapterTitleFromOutline(
    detail?.outline,
    summary.current_topic_id,
    t('catalog.noProgressYet'),
  )
}

function phaseLabel(phase: SessionSummary['current_phase'] | null) {
  if (!phase) {
    return ''
  }
  return t(`session.phase.${phase}`)
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
    const summaries = sortSessionsByActivity(await listSessions())
    const indexes = indexSessionsForPacks(summaries)

    const next: Record<string, PackLearning> = {}
    await Promise.all(
      packs.value.map(async (pack) => {
        const summary = matchSessionForPack(pack, indexes)
        if (!summary) {
          next[pack.id] = emptyPackLearning()
          return
        }
        let detail: SessionState | null = null
        try {
          detail = await getSession(summary.id)
        } catch {
          detail = null
        }
        next[pack.id] = packLearningFromSession({
          summary,
          detail,
          chapter: chapterTitle(detail, summary),
        })
      }),
    )
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
  await Promise.all([refreshPacks(), loadDiscover(query.value.trim(), { force: true })])
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
    activeTab.value = catalogTabFromQuery(value)
  },
)

onMounted(async () => {
  await refreshPacks()
  await loadDiscover(query.value.trim())
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
            <button
              v-if="activeTab === 'external'"
              class="btn-primary btn-sm catalog-search-submit"
              type="submit"
              :disabled="pending || catalogPending"
            >
              {{ pending || catalogPending ? t('search.loading') : t('search.submit') }}
            </button>
          </form>

          <button
            v-if="activeTab === 'external'"
            class="btn-primary btn-sm catalog-toolbar-cta"
            type="button"
            @click="showCourseCreate = true"
          >
            <SparklesIcon class="icon-sm" />
            {{ t('libraryCreate.open') }}
          </button>
        </div>
      </header>

      <ClientOnly>
        <LibraryCourseCreate
          :open="showCourseCreate"
          @close="showCourseCreate = false"
          @installed="onCourseInstalled"
        />
      </ClientOnly>

      <div
        class="catalog-workspace"
        :class="{ 'is-library': workspaceTab === 'library', 'is-discover': workspaceTab === 'external' }"
      >
        <Transition name="page-cyber" @after-leave="onSourcesRailAfterLeave">
          <aside v-if="activeTab === 'external'" key="sources-rail" class="catalog-rail">
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

        <section class="catalog-main">
          <Transition name="page-cyber" mode="out-in">
            <div :key="activeTab" class="catalog-pane">
          <header class="catalog-command">
            <div class="catalog-command-copy">
              <h2>
                {{
                  activeTab === 'library'
                    ? t('catalog.libraryTitle')
                    : platformFilter
                      ? sourceLabel(platformFilter)
                      : t('catalog.externalTitle')
                }}
              </h2>
              <p>
                {{
                  activeTab === 'library'
                    ? t('catalog.libraryCount', { count: filteredPacks.length })
                    : t('catalog.externalMeta')
                }}
              </p>
            </div>
            <div class="catalog-command-tools">
              <button
                v-if="platformFilter && activeTab === 'external'"
                class="btn-secondary btn-sm"
                type="button"
                @click="platformFilter = ''"
              >
                {{ t('catalog.clearFilter') }}
              </button>
            </div>
          </header>

          <div
            v-if="activeTab === 'external' && allTags.length"
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
              v-if="catalogPending && activeTab === 'external' && !courseRows.length"
              class="loading-state catalog-loading"
            >
              <span class="loading-spinner" aria-hidden="true" />
              <span>{{ t('search.loading') }}</span>
            </div>

            <template v-else-if="activeTab === 'library'">
              <div v-if="!packs.length" class="catalog-empty">
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

              <div v-else-if="!filteredPacks.length" class="catalog-empty">
                <p class="catalog-empty-title">{{ t('catalog.librarySearchEmpty') }}</p>
                <p class="catalog-empty-meta">{{ t('catalog.librarySearchEmptyMeta') }}</p>
              </div>

              <div v-else class="catalog-pack-grid catalog-library-grid">
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
                        v-if="packLearning[pack.id]?.phase"
                        class="lib-tag"
                      >
                        {{ phaseLabel(packLearning[pack.id].phase) }}
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
                                {{ t('catalog.downloadingCourse') }}
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
