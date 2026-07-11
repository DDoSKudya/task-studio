<script setup lang="ts">
import type {
  AttemptTimelineEntry,
  ProgressResponse,
  StudySkipEntry,
} from '~/composables/useAnalytics'

const { t } = useI18n()
const { fetchProgress, fetchSkips, fetchAttempts } = useAnalytics()

const progress = ref<ProgressResponse | null>(null)
const skips = ref<StudySkipEntry[]>([])
const attempts = ref<AttemptTimelineEntry[]>([])
const pending = ref(false)
const errorMessage = ref('')

async function loadAnalytics() {
  pending.value = true
  errorMessage.value = ''
  try {
    const [progressResponse, skipsResponse, attemptsResponse] = await Promise.all([
      fetchProgress(30),
      fetchSkips(),
      fetchAttempts(30),
    ])
    progress.value = progressResponse
    skips.value = skipsResponse.items
    attempts.value = attemptsResponse.items
  } catch {
    errorMessage.value = t('analytics.errors.loadFailed')
  } finally {
    pending.value = false
  }
}

onMounted(loadAnalytics)

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}
</script>

<template>
  <UContainer class="space-y-6 py-8">
    <div>
      <h1 class="text-2xl font-semibold">
        {{ t('analytics.title') }}
      </h1>
      <p class="mt-1 text-sm text-muted">
        {{ t('analytics.subtitle') }}
      </p>
    </div>

    <p v-if="errorMessage" class="text-sm text-red-600">
      {{ errorMessage }}
    </p>

    <div v-if="pending" class="text-sm text-muted">
      {{ t('analytics.loading') }}
    </div>

    <template v-else-if="progress">
      <div class="grid gap-4 md:grid-cols-3">
        <UCard>
          <p class="text-sm text-muted">
            {{ t('analytics.stats.sessions') }}
          </p>
          <p class="mt-1 text-2xl font-semibold">
            {{ progress.total_sessions }}
          </p>
        </UCard>
        <UCard>
          <p class="text-sm text-muted">
            {{ t('analytics.stats.steps') }}
          </p>
          <p class="mt-1 text-2xl font-semibold">
            {{ progress.total_steps_completed }}
          </p>
        </UCard>
        <UCard>
          <p class="text-sm text-muted">
            {{ t('analytics.stats.skips') }}
          </p>
          <p class="mt-1 text-2xl font-semibold">
            {{ skips.length }}
          </p>
        </UCard>
      </div>

      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ t('analytics.progressChart') }}
          </h2>
        </template>
        <AnalyticsProgressChart v-if="progress.points.length" :points="progress.points" />
        <p v-else class="text-sm text-muted">
          {{ t('analytics.emptyProgress') }}
        </p>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ t('analytics.skipsTitle') }}
          </h2>
        </template>
        <div v-if="skips.length === 0" class="text-sm text-muted">
          {{ t('analytics.emptySkips') }}
        </div>
        <ul v-else class="divide-y divide-default">
          <li
            v-for="skip in skips"
            :key="`${skip.session_id}-${skip.topic_id}`"
            class="flex flex-wrap items-start justify-between gap-3 py-3"
          >
            <div>
              <p class="font-medium">
                {{ skip.pack_title || skip.topic_id }}
              </p>
              <p class="text-sm text-muted">
                {{ t('analytics.topicLabel', { topic: skip.topic_id }) }}
              </p>
            </div>
            <time class="text-xs text-muted">{{ formatDate(skip.skipped_at) }}</time>
          </li>
        </ul>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ t('analytics.attemptsTitle') }}
          </h2>
        </template>
        <div v-if="attempts.length === 0" class="text-sm text-muted">
          {{ t('analytics.emptyAttempts') }}
        </div>
        <ul v-else class="divide-y divide-default">
          <li
            v-for="attempt in attempts"
            :key="attempt.attempt_id"
            class="flex flex-wrap items-start justify-between gap-3 py-3"
          >
            <div>
              <p class="font-medium">
                {{ attempt.pack_title || attempt.topic_id }}
              </p>
              <p class="text-sm text-muted">
                {{ attempt.phase }} · {{ attempt.topic_id }} · {{ attempt.step_id }}
              </p>
            </div>
            <div class="text-right text-sm">
              <UBadge :color="attempt.passed ? 'success' : 'warning'" variant="subtle">
                {{ attempt.passed ? t('analytics.passed') : t('analytics.failed') }}
              </UBadge>
              <p class="mt-1 text-xs text-muted">
                {{ formatDate(attempt.created_at) }}
              </p>
            </div>
          </li>
        </ul>
      </UCard>
    </template>
  </UContainer>
</template>
