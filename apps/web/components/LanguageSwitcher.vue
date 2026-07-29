<script setup lang="ts">
const { locale, setLocale, t } = useI18n()
const { user, patchSettings } = useAuth()

const currentCode = computed(() => (locale.value === 'ru' ? 'ru' : 'en'))
const nextCode = computed(() => (currentCode.value === 'en' ? 'ru' : 'en'))

const ariaLabel = computed(() =>
  t('settings.languageSwitch', { from: currentCode.value.toUpperCase(), to: nextCode.value.toUpperCase() }),
)

async function applyLocale(code: 'en' | 'ru') {
  const previous = locale.value === 'ru' ? 'ru' : 'en'
  if (code === previous) {
    return
  }
  await setLocale(code)
  if (!user.value) {
    return
  }
  try {
    await patchSettings({ locale: code })
  } catch {
    await setLocale(previous)
  }
}

function toggleLocale() {
  void applyLocale(nextCode.value)
}
</script>

<template>
  <div class="language-switcher">
    <button
      type="button"
      class="language-switcher-compact-btn"
      :aria-label="ariaLabel"
      :title="ariaLabel"
      @click="toggleLocale"
    >
      <span class="language-switcher-code">{{ currentCode }}</span>
    </button>

    <div class="language-switcher-expanded">
      <p class="language-switcher-label">
        {{ t('settings.language') }}
      </p>
      <div class="language-switcher-seg" role="group" :aria-label="t('settings.language')">
        <button
          type="button"
          class="language-switcher-opt"
          :class="{ active: currentCode === 'en' }"
          :aria-pressed="currentCode === 'en'"
          @click="applyLocale('en')"
        >
          EN
        </button>
        <button
          type="button"
          class="language-switcher-opt"
          :class="{ active: currentCode === 'ru' }"
          :aria-pressed="currentCode === 'ru'"
          @click="applyLocale('ru')"
        >
          RU
        </button>
      </div>
    </div>
  </div>
</template>
