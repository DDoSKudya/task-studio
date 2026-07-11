<script setup lang="ts">
const route = useRoute()
const { t } = useI18n()
const { getPack } = useCatalog()

const packId = computed(() => String(route.params.id))
const pack = ref<Awaited<ReturnType<typeof getPack>> | null>(null)
const topics = computed(() => {
  const raw = pack.value?.manifest.topics
  if (!Array.isArray(raw)) {
    return []
  }
  return raw.filter(
    (topic): topic is { id: string; title: string } =>
      typeof topic === 'object' && topic !== null && 'id' in topic && 'title' in topic,
  )
})
const pending = ref(true)
const errorMessage = ref('')

onMounted(async () => {
  try {
    pack.value = await getPack(packId.value)
  } catch {
    errorMessage.value = t('catalog.errors.loadFailed')
  } finally {
    pending.value = false
  }
})
</script>

<template>
  <UContainer class="py-8 space-y-6">
    <NuxtLink class="text-sm text-primary" to="/catalog">
      {{ t('catalog.back') }}
    </NuxtLink>

    <p v-if="pending" class="text-sm text-muted">
      {{ t('catalog.loading') }}
    </p>

    <p v-else-if="errorMessage" class="text-sm text-red-600">
      {{ errorMessage }}
    </p>

    <template v-else-if="pack">
      <div class="space-y-2">
        <h1 class="text-2xl font-semibold">
          {{ pack.title }}
        </h1>
        <p class="text-sm text-muted">
          {{ pack.slug }} · v{{ pack.active_version.version }}
        </p>
      </div>

      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ t('catalog.topics') }}
          </h2>
        </template>
        <ul class="space-y-2">
          <li
            v-for="topic in topics"
            :key="topic.id"
            class="text-sm"
          >
            {{ topic.title }}
          </li>
        </ul>
      </UCard>
    </template>
  </UContainer>
</template>
