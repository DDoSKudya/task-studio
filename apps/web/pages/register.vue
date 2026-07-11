<script setup lang="ts">
const { t } = useI18n()
const { register } = useAuth()
const router = useRouter()

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const pending = ref(false)

async function onSubmit() {
  errorMessage.value = ''
  pending.value = true
  try {
    await register(email.value, password.value)
    await router.push('/')
  } catch (error) {
    const statusCode = (error as { statusCode?: number }).statusCode
    if (statusCode === 409) {
      errorMessage.value = t('auth.errors.emailTaken')
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
          {{ t('auth.register') }}
        </h1>
      </template>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <UFormField :label="t('auth.email')">
          <UInput v-model="email" type="email" autocomplete="email" required />
        </UFormField>
        <UFormField :label="t('auth.password')">
          <UInput v-model="password" type="password" autocomplete="new-password" minlength="8" required />
        </UFormField>
        <p v-if="errorMessage" class="text-sm text-red-600">
          {{ errorMessage }}
        </p>
        <UButton type="submit" block :loading="pending">
          {{ t('auth.submitRegister') }}
        </UButton>
      </form>

      <template #footer>
        <NuxtLink class="text-sm text-primary" to="/login">
          {{ t('auth.haveAccount') }}
        </NuxtLink>
      </template>
    </UCard>
  </UContainer>
</template>
