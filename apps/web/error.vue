<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{
  error: NuxtError
}>()

const { t } = useI18n()

const statusCode = computed(() => props.error?.statusCode || 500)
const pathHint = computed(() => {
  const url = (props.error as { url?: string }).url
  if (url) {
    return `: ${url}`
  }
  const statusMessage = props.error?.statusMessage || ''
  const match = statusMessage.match(/:\s*(\/\S+)/)
  return match?.[1] ? `: ${match[1]}` : ''
})
const message = computed(() => {
  if (statusCode.value === 404) {
    return t('error.notFound', { path: pathHint.value })
  }
  return props.error?.statusMessage || t('error.generic')
})

function goHome() {
  clearError({ redirect: '/login' })
}
</script>

<template>
  <div class="error-shell">
    <OpBackdrop />
    <main class="error-panel">
      <p class="error-kicker">TASK STUDIO</p>
      <h1 class="error-code">{{ statusCode }}</h1>
      <p class="error-message">{{ message }}</p>
      <button class="btn-primary error-action" type="button" @click="goHome">
        {{ statusCode === 404 ? t('error.goLogin') : t('error.goHome') }}
      </button>
    </main>
  </div>
</template>

<style scoped>
.error-shell {
  position: relative;
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 1.5rem;
  background: var(--color-bg);
  color: var(--color-text);
}

.error-panel {
  position: relative;
  z-index: 1;
  width: min(28rem, 100%);
  border: 1px solid var(--color-border);
  background: rgb(12 12 22 / 0.72);
  backdrop-filter: blur(6px);
  padding: 2rem 1.75rem;
  text-align: center;
}

.error-panel::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--op-violet), transparent 45%, transparent 55%, var(--op-gold));
}

.error-kicker {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.error-code {
  margin: 0.75rem 0 0;
  font-family: var(--font-display);
  font-size: clamp(3.5rem, 12vw, 5.5rem);
  font-weight: 900;
  letter-spacing: -0.06em;
  line-height: 1;
}

.error-message {
  margin: 0.85rem 0 0;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.error-action {
  margin-top: 1.5rem;
}
</style>
