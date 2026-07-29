<script setup lang="ts">
import {
  ArrowPathIcon,
  ChevronLeftIcon,
  PlayIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'

import { extractErrorMessage } from '~/utils/api'
import { buildCourseOutline } from '~/utils/catalog'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { getPack, deletePack } = useCatalog()
const { importFromSearch, getImportJob } = useSearch()
const discoverCache = useDiscoverCache()
const { startSession } = useSessions()
const toasts = useToasts()

const packId = computed(() => String(route.params.id))
const pack = ref<Awaited<ReturnType<typeof getPack>> | null>(null)
const pending = ref(true)
const starting = ref(false)
const deleting = ref(false)
const redownloading = ref(false)
const loadFailed = ref(false)

const outline = computed(() =>
  pack.value?.manifest
    ? buildCourseOutline(pack.value.manifest as Record<string, unknown>)
    : [],
)

const totalSteps = computed(() =>
  outline.value.reduce((sum, module) => sum + module.lessons.length, 0),
)
const canStart = computed(() => Boolean(pack.value?.active_version.id) && totalSteps.value > 0)
const isBroken = computed(() => pack.value?.integrity === 'broken')
const canRedownload = computed(() => {
  const current = pack.value
  return Boolean(
    current
    && current.integrity === 'broken'
    && current.external_id
    && current.source
    && current.source !== 'local',
  )
})

const sourceLabel = computed(() => {
  const source = pack.value?.source
  if (!source) {
    return ''
  }
  return t(`search.sources.${source}`, source)
})

async function reloadPack() {
  pack.value = await getPack(packId.value)
}

onMounted(async () => {
  try {
    await reloadPack()
  } catch (error) {
    loadFailed.value = true
    toasts.error(extractErrorMessage(error) || t('catalog.errors.loadFailed'))
  } finally {
    pending.value = false
  }
})

async function onStartSession() {
  if (!pack.value || starting.value) {
    return
  }
  starting.value = true
  try {
    const session = await startSession(pack.value.active_version.id)
    await router.push(`/sessions/${session.id}`)
  } catch (error) {
    toasts.error(extractErrorMessage(error) || t('catalog.errors.startFailed'))
  } finally {
    starting.value = false
  }
}

async function onDelete() {
  if (!pack.value || deleting.value) {
    return
  }
  const { confirm } = useConfirm()
  const confirmed = await confirm({
    title: t('catalog.deleteConfirm', { title: pack.value.title }),
    confirmLabel: t('dialog.delete'),
    cancelLabel: t('dialog.cancel'),
    danger: true,
  })
  if (!confirmed) {
    return
  }
  deleting.value = true
  try {
    await deletePack(pack.value.id)
    discoverCache.clear()
    toasts.success(t('catalog.deleted'))
    await router.push('/catalog')
  } catch (error) {
    toasts.error(extractErrorMessage(error) || t('catalog.errors.deleteFailed'))
  } finally {
    deleting.value = false
  }
}

async function onRedownload() {
  if (!pack.value || !canRedownload.value || redownloading.value || !pack.value.external_id) {
    return
  }
  const { confirm } = useConfirm()
  const confirmed = await confirm({
    title: t('catalog.redownloadConfirm', { title: pack.value.title }),
    confirmLabel: t('catalog.redownloadCourse'),
    cancelLabel: t('dialog.cancel'),
  })
  if (!confirmed) {
    return
  }
  redownloading.value = true
  try {
    const accepted = await importFromSearch(pack.value.source, pack.value.external_id, {
      force: true,
    })
    const deadline = Date.now() + 5 * 60_000
    while (Date.now() < deadline) {
      const job = await getImportJob(accepted.id)
      if (job.status === 'done') {
        discoverCache.clear()
        await reloadPack()
        toasts.success(t('search.downloadDone', { title: pack.value.title }))
        return
      }
      if (job.status === 'failed') {
        throw new Error(job.error || 'failed')
      }
      await new Promise((resolve) => setTimeout(resolve, 900))
    }
    throw new Error('timeout')
  } catch (error) {
    if (error instanceof Error && error.message === 'timeout') {
      toasts.error(t('search.errors.importTimeout'))
    } else {
      const message = extractErrorMessage(error)
      if (message.includes('import already in progress')) {
        toasts.error(t('search.errors.importInProgress'))
      } else {
        toasts.error(message || t('search.errors.importFailed'))
      }
    }
  } finally {
    redownloading.value = false
  }
}
</script>

<template>
  <PageShell
    :title="pack?.title ?? t('catalog.courseTitle')"
    :meta="pack ? `${pack.slug} · v${pack.active_version.version}` : undefined"
    :fill="false"
  >
    <template #actions>
      <button
        v-if="pack"
        class="btn-ghost"
        type="button"
        :disabled="deleting || starting"
        @click="onDelete"
      >
        <TrashIcon class="icon-sm" />
        {{ deleting ? t('catalog.deleting') : t('catalog.delete') }}
      </button>
    </template>

    <NuxtLink class="link-back" to="/catalog">
      <ChevronLeftIcon class="icon-sm" />
      {{ t('catalog.back') }}
    </NuxtLink>

    <div v-if="pending" class="loading-state">
      <span class="loading-spinner" aria-hidden="true" />
      <span>{{ t('catalog.loading') }}</span>
    </div>

    <div v-else-if="loadFailed || !pack" class="empty-state">
      <p class="empty-state-title">{{ t('catalog.errors.loadFailed') }}</p>
    </div>

    <div v-else class="course-root">
      <section class="course-hero" aria-labelledby="course-hero-title">
        <div class="course-hero-glow" aria-hidden="true" />
        <div class="course-hero-grid" aria-hidden="true" />
        <div class="course-hero-inner">
          <p class="course-eyebrow">{{ t('catalog.courseEyebrow') }}</p>
          <h2 id="course-hero-title" class="course-title">{{ pack.title }}</h2>
          <p class="course-lede">{{ t('catalog.courseLede') }}</p>

          <div class="course-meta-row">
            <span v-if="sourceLabel" class="course-chip">{{ sourceLabel }}</span>
            <span
              v-if="isBroken"
              class="course-chip course-chip-warning"
              :title="t('catalog.integrityBrokenMeta')"
            >
              {{ t('catalog.integrityBroken') }}
            </span>
            <span class="course-chip course-chip-muted">v{{ pack.active_version.version }}</span>
            <span class="course-chip course-chip-muted">
              {{ t('catalog.topicCount', { count: outline.length }) }}
            </span>
            <span class="course-chip course-chip-muted">
              {{ t('catalog.stepCount', { count: totalSteps }) }}
            </span>
          </div>

          <p v-if="isBroken" class="course-hero-hint">{{ t('catalog.integrityBrokenMeta') }}</p>

          <div class="course-hero-actions">
            <button
              v-if="canRedownload"
              class="btn-primary"
              type="button"
              :disabled="redownloading || deleting || starting"
              @click="onRedownload"
            >
              <span
                v-if="redownloading"
                class="loading-spinner loading-spinner-sm"
                aria-hidden="true"
              />
              <ArrowPathIcon v-else class="icon-sm" />
              {{ redownloading ? t('catalog.downloadingCourse') : t('catalog.redownloadCourse') }}
            </button>
            <button
              class="btn-primary"
              :class="{ 'btn-ghost': canRedownload }"
              type="button"
              :disabled="starting || deleting || redownloading || !canStart"
              @click="onStartSession"
            >
              <PlayIcon class="icon-sm" />
              {{ starting ? t('catalog.loading') : t('catalog.startSession') }}
            </button>
            <p v-if="!canStart && !isBroken" class="course-hero-hint">{{ t('catalog.errors.noSteps') }}</p>
          </div>
        </div>
      </section>

      <section class="course-curriculum" aria-labelledby="course-curriculum-title">
        <div class="course-curriculum-header">
          <div>
            <h3 id="course-curriculum-title" class="course-curriculum-title">
              {{ t('catalog.topics') }}
            </h3>
            <p class="course-curriculum-meta">{{ t('catalog.curriculumMeta') }}</p>
          </div>
        </div>

        <div v-if="outline.length" class="stepik-program">
          <article
            v-for="module in outline"
            :key="module.topicId"
            class="stepik-module"
          >
            <header class="stepik-module-header">
              <h4 class="stepik-module-title">
                {{ module.index }}. {{ module.title }}
              </h4>
              <span class="stepik-module-progress">
                <span class="stepik-progress-dot" aria-hidden="true" />
                {{ t('catalog.lessonProgress', { done: 0, total: module.lessons.length }) }}
              </span>
            </header>
            <ul v-if="module.lessons.length" class="stepik-lesson-list">
              <li
                v-for="lesson in module.lessons"
                :key="lesson.stepId"
                class="stepik-lesson"
              >
                <span class="stepik-lesson-mark" aria-hidden="true">
                  {{ lesson.kind.slice(0, 1).toUpperCase() }}
                </span>
                <span class="stepik-lesson-title">
                  {{ lesson.indexLabel }} {{ lesson.title }}
                </span>
                <span class="stepik-lesson-progress">
                  {{ t('catalog.lessonProgress', { done: 0, total: 1 }) }}
                </span>
              </li>
            </ul>
          </article>
        </div>

        <div v-else class="course-empty">
          <p class="course-empty-title">{{ t('catalog.emptyTopicsTitle') }}</p>
          <p class="course-empty-meta">{{ t('catalog.emptyTopicsMeta') }}</p>
        </div>
      </section>
    </div>
  </PageShell>
</template>
