<script setup lang="ts">
import type {
  AttemptTimelineEntry,
  ProgressResponse,
  StudySkipEntry,
} from '~/composables/analytics/useAnalytics'
import {
  attemptPassStats,
  countActiveDays,
  stepsPerActiveDay as stepsPerDay,
  streakFromPoints,
  weakSpotsFromAttempts,
} from '~/utils/analytics'

const { t, locale } = useI18n()
useAppPageTitle(computed(() => t('nav.analytics')))
const { fetchProgress, fetchSkips, fetchAttempts } = useAnalytics()
const toasts = useToasts()

const progress = ref<ProgressResponse | null>(null)
const skips = ref<StudySkipEntry[]>([])
const attempts = ref<AttemptTimelineEntry[]>([])
const pending = ref(false)

async function loadAnalytics() {
  pending.value = true
  try {
    const [progressResponse, skipsResponse, attemptsResponse] = await Promise.all([
      fetchProgress(30),
      fetchSkips(),
      fetchAttempts(50),
    ])
    progress.value = progressResponse
    skips.value = skipsResponse.items
    attempts.value = attemptsResponse.items
  } catch {
    toasts.error(t('analytics.errors.loadFailed'))
  } finally {
    pending.value = false
  }
}

onMounted(loadAnalytics)

const passStats = computed(() => attemptPassStats(attempts.value))
const passedCount = computed(() => passStats.value.passed)
const failedCount = computed(() => passStats.value.failed)
const attemptTotal = computed(() => passStats.value.total)
const passRate = computed(() => passStats.value.passRate)

const activeDays = computed(() => countActiveDays(progress.value?.points ?? []))

const stepsPerActiveDay = computed(() =>
  stepsPerDay(progress.value?.total_steps_completed ?? 0, activeDays.value),
)

const streakDays = computed(() => streakFromPoints(progress.value?.points ?? []))

const weakSpots = computed(() => weakSpotsFromAttempts(attempts.value))

function formatDate(value: string) {
  return new Date(value).toLocaleString(locale.value === 'ru' ? 'ru-RU' : 'en-US', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <PageShell :title="t('analytics.title')" :meta="t('analytics.subtitle')">
    <div v-if="pending" class="loading-state">
      <span class="loading-spinner" aria-hidden="true" />
      <span>{{ t('analytics.loading') }}</span>
    </div>

    <div v-else-if="progress" class="ax-root">
      <div class="ax-stats ax-stats-3">
        <article class="ax-stat">
          <p class="ax-stat-label">{{ t('analytics.stats.passRate') }}</p>
          <p class="ax-stat-value">{{ passRate == null ? '—' : `${passRate}%` }}</p>
          <p class="ax-stat-foot">
            {{
              attemptTotal
                ? t('analytics.stats.passRateFoot', { passed: passedCount, failed: failedCount })
                : t('analytics.stats.noAttempts')
            }}
          </p>
        </article>
        <article class="ax-stat">
          <p class="ax-stat-label">{{ t('analytics.stats.steps') }}</p>
          <p class="ax-stat-value">{{ progress.total_steps_completed }}</p>
          <p class="ax-stat-foot">
            {{ t('analytics.stats.stepsFoot', { perDay: stepsPerActiveDay, days: activeDays }) }}
          </p>
        </article>
        <article class="ax-stat">
          <p class="ax-stat-label">{{ t('analytics.stats.streak') }}</p>
          <p class="ax-stat-value">{{ streakDays }}</p>
          <p class="ax-stat-foot">
            {{ t('analytics.stats.streakFoot', { sessions: progress.total_sessions }) }}
          </p>
        </article>
      </div>

      <div class="ax-hero">
        <section class="ax-panel">
          <header class="ax-panel-head">
            <div>
              <p class="ax-panel-kicker">{{ t('analytics.rhythm.kicker') }}</p>
              <h2 class="ax-panel-title">{{ t('analytics.progressChart') }}</h2>
            </div>
            <p class="ax-panel-meta">{{ t('analytics.rhythm.meta') }}</p>
          </header>
          <div class="ax-panel-body">
            <AnalyticsProgressChart
              v-if="progress.points.length"
              :points="progress.points"
              :sessions-label="t('analytics.series.sessions')"
              :steps-label="t('analytics.series.steps')"
            />
            <div v-else class="ax-empty">
              <p class="empty-state-title">{{ t('analytics.emptyProgress') }}</p>
              <p class="ax-empty-meta">{{ t('analytics.emptyProgressMeta') }}</p>
            </div>
          </div>
        </section>

        <section class="ax-panel">
          <header class="ax-panel-head">
            <div>
              <p class="ax-panel-kicker">{{ t('analytics.ring.kicker') }}</p>
              <h2 class="ax-panel-title">{{ t('analytics.ring.title') }}</h2>
            </div>
          </header>
          <div class="ax-panel-body">
            <AnalyticsPassRing
              :passed="passedCount"
              :failed="failedCount"
              :pass-label="t('analytics.passed')"
              :fail-label="t('analytics.failed')"
              :empty-label="t('analytics.emptyAttempts')"
            />
          </div>
        </section>
      </div>

      <div class="ax-grid-wide">
        <section class="ax-panel">
          <header class="ax-panel-head">
            <div>
              <p class="ax-panel-kicker">{{ t('analytics.weak.kicker') }}</p>
              <h2 class="ax-panel-title">{{ t('analytics.weak.title') }}</h2>
            </div>
            <p class="ax-panel-meta">{{ t('analytics.weak.meta') }}</p>
          </header>
          <div class="ax-panel-body">
            <div v-if="!weakSpots.length" class="ax-empty">
              <p class="empty-state-title">{{ t('analytics.weak.empty') }}</p>
              <p class="ax-empty-meta">{{ t('analytics.weak.emptyMeta') }}</p>
            </div>
            <div v-else class="ax-weak">
              <article
                v-for="spot in weakSpots"
                :key="spot.key"
                class="ax-weak-item"
              >
                <div class="ax-weak-copy">
                  <p class="ax-weak-title">{{ spot.title }}</p>
                  <p class="ax-weak-meta">
                    {{ t('analytics.topicLabel', { topic: spot.topicId }) }}
                  </p>
                </div>
                <div class="ax-weak-metrics">
                  <span class="ax-weak-fails">
                    {{ t('analytics.weak.fails', { count: spot.failed }) }}
                  </span>
                  <span class="ax-weak-rate">{{ spot.failRate }}%</span>
                </div>
                <div class="ax-weak-bar" aria-hidden="true">
                  <span class="ax-weak-bar-fill" :style="{ width: `${spot.failRate}%` }" />
                </div>
              </article>
            </div>
          </div>
        </section>

        <section class="ax-panel">
          <header class="ax-panel-head">
            <div>
              <p class="ax-panel-kicker">{{ t('analytics.feed.kicker') }}</p>
              <h2 class="ax-panel-title">{{ t('analytics.attemptsTitle') }}</h2>
            </div>
          </header>
          <div class="ax-panel-body">
            <div v-if="!attempts.length" class="ax-empty">
              <p class="empty-state-title">{{ t('analytics.emptyAttempts') }}</p>
            </div>
            <div v-else class="ax-feed">
              <article
                v-for="attempt in attempts.slice(0, 10)"
                :key="attempt.attempt_id"
                class="ax-feed-item"
                :class="attempt.passed ? 'is-pass' : 'is-fail'"
              >
                <div>
                  <p class="ax-feed-title">{{ attempt.pack_title || attempt.topic_id }}</p>
                  <p class="ax-feed-meta">
                    {{ attempt.phase }} · {{ attempt.step_id }}
                  </p>
                  <p class="ax-feed-time">{{ formatDate(attempt.created_at) }}</p>
                </div>
                <span
                  class="ax-feed-badge"
                  :class="attempt.passed ? 'is-pass' : 'is-fail'"
                >
                  {{ attempt.passed ? t('analytics.passed') : t('analytics.failed') }}
                </span>
              </article>
            </div>
          </div>
        </section>
      </div>

      <section v-if="skips.length" class="ax-panel">
        <header class="ax-panel-head">
          <div>
            <p class="ax-panel-kicker">{{ t('analytics.skips.kicker') }}</p>
            <h2 class="ax-panel-title">{{ t('analytics.skipsTitle') }}</h2>
          </div>
          <p class="ax-panel-meta">{{ t('analytics.skips.meta', { count: skips.length }) }}</p>
        </header>
        <div class="ax-panel-body">
          <div class="ax-feed ax-feed-flat">
            <article
              v-for="skip in skips.slice(0, 6)"
              :key="`${skip.session_id}-${skip.topic_id}`"
              class="ax-feed-item is-skip"
            >
              <div>
                <p class="ax-feed-title">{{ skip.pack_title || skip.topic_id }}</p>
                <p class="ax-feed-meta">
                  {{ t('analytics.topicLabel', { topic: skip.topic_id }) }}
                </p>
              </div>
              <time class="ax-feed-time">{{ formatDate(skip.skipped_at) }}</time>
            </article>
          </div>
        </div>
      </section>
    </div>
  </PageShell>
</template>
