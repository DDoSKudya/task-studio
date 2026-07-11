export default defineNuxtConfig({
  compatibilityDate: '2025-07-11',
  devtools: { enabled: true },
  typescript: {
    strict: true,
    typeCheck: true,
  },
  modules: ['@nuxt/eslint', '@nuxtjs/i18n'],
  i18n: {
    defaultLocale: 'en',
    locales: [
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ru', name: 'Русский', file: 'ru.json' },
    ],
    langDir: 'i18n/locales',
  },
})
