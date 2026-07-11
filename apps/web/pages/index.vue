<script setup lang="ts">
const { t, locale, locales, setLocale } = useI18n()
</script>

<template>
  <main class="page">
    <header class="header">
      <h1>{{ t('app.title') }}</h1>
      <nav class="locales">
        <button
          v-for="item in locales"
          :key="item.code"
          type="button"
          :class="{ active: locale === item.code }"
          @click="setLocale(item.code)"
        >
          {{ item.name }}
        </button>
      </nav>
    </header>
    <p>{{ t('app.welcome') }}</p>
  </main>
</template>

<style scoped>
.page {
  margin: 0 auto;
  max-width: 48rem;
  padding: 2rem 1.5rem;
  font-family: system-ui, sans-serif;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.locales {
  display: flex;
  gap: 0.5rem;
}

button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 0.375rem;
  padding: 0.25rem 0.75rem;
  cursor: pointer;
}

button.active {
  border-color: #2563eb;
  color: #2563eb;
}
</style>
