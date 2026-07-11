<script setup lang="ts">
const { t } = useI18n()
const { login } = useAuth()
const router = useRouter()

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const pending = ref(false)

async function onSubmit() {
  errorMessage.value = ''
  pending.value = true
  try {
    await login(email.value, password.value)
    await router.push('/')
  } catch (error) {
    const statusCode = (error as { statusCode?: number }).statusCode
    if (statusCode === 401) {
      errorMessage.value = t('auth.errors.invalidCredentials')
    } else {
      errorMessage.value = t('auth.errors.generic')
    }
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UContainer class="py-8 max-w-md">
    <UCard>
      <template #header>
        <h1 class="text-xl font-semibold">
          {{ t('auth.login') }}
        </h1>
      </template>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <UFormField :label="t('auth.email')">
          <UInput v-model="email" type="email" autocomplete="email" required />
        </UFormField>
        <UFormField :label="t('auth.password')">
          <UInput v-model="password" type="password" autocomplete="current-password" required />
        </UFormField>
        <p v-if="errorMessage" class="text-sm text-red-600">
          {{ errorMessage }}
        </p>
        <UButton type="submit" block :loading="pending">
          {{ t('auth.submitLogin') }}
        </UButton>
      </form>

      <template #footer>
        <NuxtLink class="text-sm text-primary" to="/register">
          {{ t('auth.noAccount') }}
        </NuxtLink>
      </template>
    </UCard>
  </UContainer>
</template>
