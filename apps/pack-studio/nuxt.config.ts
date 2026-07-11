export default defineNuxtConfig({
  compatibilityDate: '2025-07-11',
  devtools: { enabled: true },
  app: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/pack-studio/',
  },
  typescript: {
    strict: true,
    typeCheck: true,
    tsConfig: {
      exclude: ['**/*.spec.ts'],
    },
  },
  modules: ['@nuxt/eslint', '@nuxtjs/i18n', '@nuxt/ui'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api',
    },
  },
  i18n: {
    defaultLocale: 'en',
    locales: [
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ru', name: 'Русский', file: 'ru.json' },
    ],
    langDir: 'locales',
  },
})
