<script setup lang="ts">
const { t } = useI18n()
const { search, importFromSearch } = useSearch()

const query = ref('')
const results = ref<Awaited<ReturnType<typeof search>>['hits']>([])
const pending = ref(false)
const importPending = ref<string | null>(null)
const errorMessage = ref('')

async function runSearch() {
  if (!query.value.trim()) {
    return
  }
  pending.value = true
  errorMessage.value = ''
  try {
    const response = await search(query.value.trim())
    results.value = response.hits
  } catch {
    errorMessage.value = t('search.errors.failed')
  } finally {
    pending.value = false
  }
}

async function importHit(hit: (typeof results.value)[number]) {
  if (!hit.platform || !hit.external_id) {
    return
  }
  importPending.value = hit.id
  errorMessage.value = ''
  try {
    await importFromSearch(hit.platform, hit.external_id)
  } catch {
    errorMessage.value = t('search.errors.importFailed')
  } finally {
    importPending.value = null
  }
}

function sourceLabel(source: string) {
  return t(`search.sources.${source}`, source)
}
</script>

<template>
  <UContainer class="py-8 space-y-6">
    <h1 class="text-2xl font-semibold">
      {{ t('search.title') }}
    </h1>

    <form class="flex flex-wrap gap-3" @submit.prevent="runSearch">
      <UInput v-model="query" class="min-w-64 flex-1" :placeholder="t('search.placeholder')" />
      <UButton type="submit" :loading="pending">
        {{ t('search.submit') }}
      </UButton>
    </form>

    <p v-if="errorMessage" class="text-sm text-red-600">
      {{ errorMessage }}
    </p>

    <div v-if="pending" class="text-sm text-muted">
      {{ t('search.loading') }}
    </div>

    <div v-else-if="results.length === 0 && query" class="text-sm text-muted">
      {{ t('search.empty') }}
    </div>

    <div v-else class="space-y-3">
      <UCard v-for="hit in results" :key="hit.id">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p class="font-semibold">
              {{ hit.title }}
            </p>
            <p v-if="hit.description" class="text-sm text-muted">
              {{ hit.description }}
            </p>
            <p class="mt-1 text-xs text-muted">
              {{ sourceLabel(hit.source) }} · {{ hit.kind }}
            </p>
          </div>
          <UButton
            v-if="hit.kind === 'external' && hit.platform && hit.external_id"
            size="sm"
            :loading="importPending === hit.id"
            @click="importHit(hit)"
          >
            {{ t('search.import') }}
          </UButton>
        </div>
      </UCard>
    </div>
  </UContainer>
</template>
