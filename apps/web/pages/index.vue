<script setup lang="ts">
const { t, locale, locales, setLocale } = useI18n()
const { user, fetchMe, logout } = useAuth()

onMounted(async () => {
  try {
    await fetchMe()
  } catch {
    user.value = null
  }
})
</script>

<template>
  <UContainer class="py-8 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">
        {{ t('app.title') }}
      </h1>
      <div class="flex flex-wrap items-center gap-2">
        <UButton
          v-for="item in locales"
          :key="item.code"
          size="sm"
          :variant="locale === item.code ? 'solid' : 'outline'"
          @click="setLocale(item.code)"
        >
          {{ item.name }}
        </UButton>
      </div>
    </div>

    <p>{{ t('app.welcome') }}</p>

    <UCard v-if="user">
      <p>{{ t('auth.signedInAs', { email: user.email }) }}</p>
      <div class="mt-4 flex flex-wrap gap-3">
        <UButton to="/catalog">
          {{ t('catalog.title') }}
        </UButton>
        <UButton to="/search" variant="outline">
          {{ t('search.title') }}
        </UButton>
        <UButton to="/analytics" variant="outline">
          {{ t('analytics.title') }}
        </UButton>
        <UButton to="/settings" variant="outline">
          {{ t('settings.title') }}
        </UButton>
        <UButton color="neutral" variant="soft" @click="logout">
          {{ t('auth.logout') }}
        </UButton>
      </div>
    </UCard>

    <div v-else class="flex gap-3">
      <UButton to="/login">
        {{ t('auth.login') }}
      </UButton>
      <UButton to="/register" variant="outline">
        {{ t('auth.register') }}
      </UButton>
    </div>
  </UContainer>
</template>
