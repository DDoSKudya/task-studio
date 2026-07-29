<script setup lang="ts">
import {
  ArrowRightEndOnRectangleIcon,
  UserPlusIcon,
} from '@heroicons/vue/24/outline'

definePageMeta({ layout: 'auth' })

type AuthMode = 'login' | 'register'

const { t } = useI18n()
const { login, register } = useAuth()
const route = useRoute()
const router = useRouter()
const toasts = useToasts()

function modeFromQuery(value: unknown): AuthMode {
  return value === 'register' ? 'register' : 'login'
}

const mode = ref<AuthMode>(modeFromQuery(route.query.mode))
const email = ref('')
const password = ref('')
const pending = ref(false)

const isRegister = computed(() => mode.value === 'register')

watch(
  () => route.query.mode,
  (value) => {
    mode.value = modeFromQuery(value)
  },
)

function setMode(next: AuthMode) {
  if (mode.value === next || pending.value) {
    return
  }
  mode.value = next
  const query = { ...route.query } as Record<string, string>
  if (next === 'register') {
    query.mode = 'register'
  } else {
    delete query.mode
  }
  void router.replace({ path: '/login', query })
}

async function onSubmit() {
  pending.value = true
  try {
    if (isRegister.value) {
      await register(email.value, password.value)
    } else {
      await login(email.value, password.value)
    }
    await router.push('/catalog')
  } catch (error) {
    const statusCode = (error as { statusCode?: number }).statusCode
    if (!isRegister.value && statusCode === 401) {
      toasts.error(t('auth.errors.invalidCredentials'))
    } else if (isRegister.value && statusCode === 409) {
      toasts.error(t('auth.errors.emailTaken'))
    } else {
      toasts.error(t('auth.errors.generic'))
    }
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <main class="login-shell">
    <form class="login-panel" @submit.prevent="onSubmit">
      <div class="auth-brand">
        <span class="sidebar-mark">
          <AppIcon icon-class="sidebar-mark-icon" />
        </span>
        <div class="auth-brand-copy">
          <div class="sidebar-title">{{ t('app.title') }}</div>
        </div>
      </div>

      <Transition name="auth-mode" mode="out-in">
        <div :key="mode" class="auth-mode-body">
          <header class="auth-panel-header">
            <h1 class="auth-title">
              {{ isRegister ? t('auth.register') : t('auth.login') }}
            </h1>
            <p class="auth-subtitle">
              {{ isRegister ? t('auth.registerSubtitle') : t('auth.loginSubtitle') }}
            </p>
          </header>

          <div class="auth-fields">
            <label class="form-field">
              <span class="form-label">{{ t('auth.email') }}</span>
              <input
                v-model="email"
                class="field"
                type="email"
                autocomplete="email"
                required
              >
            </label>

            <label class="form-field">
              <span class="form-label">{{ t('auth.password') }}</span>
              <input
                v-model="password"
                class="field"
                type="password"
                :autocomplete="isRegister ? 'new-password' : 'current-password'"
                :minlength="isRegister ? 8 : undefined"
                required
              >
            </label>
          </div>

          <button class="btn-primary btn-block auth-submit" type="submit" :disabled="pending">
            <UserPlusIcon v-if="isRegister" class="icon-sm" />
            <ArrowRightEndOnRectangleIcon v-else class="icon-sm" />
            <template v-if="pending">
              {{ isRegister ? t('auth.registering') : t('auth.submitting') }}
            </template>
            <template v-else>
              {{ isRegister ? t('auth.submitRegister') : t('auth.submitLogin') }}
            </template>
          </button>

          <p class="auth-footer-link">
            <button
              class="auth-mode-switch"
              type="button"
              :disabled="pending"
              @click="setMode(isRegister ? 'login' : 'register')"
            >
              {{ isRegister ? t('auth.haveAccount') : t('auth.noAccount') }}
            </button>
          </p>
        </div>
      </Transition>
    </form>
  </main>
</template>
