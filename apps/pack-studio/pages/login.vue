<script setup lang="ts">
import { ArrowRightEndOnRectangleIcon } from '@heroicons/vue/24/outline'

definePageMeta({ layout: 'auth' })

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
  <main class="login-shell">
    <form class="login-panel" @submit.prevent="onSubmit">
      <div class="auth-panel-header">
        <div class="auth-brand">
          <span class="sidebar-mark">
            <AppIcon icon-class="sidebar-mark-icon" />
          </span>
          <div>
            <div class="sidebar-title">{{ t('app.title') }}</div>
            <div class="sidebar-subtitle">{{ t('app.subtitle') }}</div>
          </div>
        </div>
        <h1 class="auth-title">{{ t('auth.login') }}</h1>
      </div>

      <label class="form-field">
        <span class="form-label">{{ t('auth.email') }}</span>
        <input v-model="email" class="field" type="email" autocomplete="email" required>
      </label>

      <label class="form-field" style="margin-top: 0.875rem">
        <span class="form-label">{{ t('auth.password') }}</span>
        <input v-model="password" class="field" type="password" autocomplete="current-password" required>
      </label>

      <p v-if="errorMessage" class="alert-error" style="margin-top: 1rem">
        {{ errorMessage }}
      </p>

      <button class="btn-primary btn-block" style="margin-top: 1.25rem" type="submit" :disabled="pending">
        <ArrowRightEndOnRectangleIcon class="icon-sm" />
        {{ pending ? t('auth.submitting') : t('auth.submitLogin') }}
      </button>
    </form>
  </main>
</template>
