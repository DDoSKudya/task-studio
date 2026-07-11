<script setup lang="ts">
const { t } = useI18n()
const { listPacks, uploadPack } = useCatalog()

const packs = ref<Awaited<ReturnType<typeof listPacks>>>([])
const pending = ref(false)
const uploadPending = ref(false)
const errorMessage = ref('')

async function loadPacks() {
  pending.value = true
  errorMessage.value = ''
  try {
    packs.value = await listPacks()
  } catch {
    errorMessage.value = t('catalog.errors.loadFailed')
  } finally {
    pending.value = false
  }
}

async function onUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }
  uploadPending.value = true
  errorMessage.value = ''
  try {
    await uploadPack(file)
    await loadPacks()
  } catch {
    errorMessage.value = t('catalog.errors.uploadFailed')
  } finally {
    uploadPending.value = false
    input.value = ''
  }
}

onMounted(loadPacks)
</script>

<template>
  <UContainer class="py-8 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">
        {{ t('catalog.title') }}
      </h1>
      <label class="inline-flex cursor-pointer items-center gap-2">
        <input
          class="hidden"
          type="file"
          accept=".studio-pack,.zip"
          :disabled="uploadPending"
          @change="onUpload"
        >
        <UButton :loading="uploadPending" as="span">
          {{ t('catalog.upload') }}
        </UButton>
      </label>
    </div>

    <p v-if="errorMessage" class="text-sm text-red-600">
      {{ errorMessage }}
    </p>

    <div v-if="pending" class="text-sm text-muted">
      {{ t('catalog.loading') }}
    </div>

    <div v-else-if="packs.length === 0" class="text-sm text-muted">
      {{ t('catalog.empty') }}
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2">
      <UCard v-for="pack in packs" :key="pack.id">
        <template #header>
          <NuxtLink class="font-semibold hover:underline" :to="`/catalog/${pack.id}`">
            {{ pack.title }}
          </NuxtLink>
        </template>
        <p class="text-sm text-muted">
          {{ pack.slug }} · v{{ pack.version }}
          <UBadge v-if="pack.source !== 'local'" class="ml-2" size="xs" variant="subtle">
            {{ pack.source }}
          </UBadge>
        </p>
      </UCard>
    </div>
  </UContainer>
</template>
