export default defineNuxtConfig({
  compatibilityDate: '2025-07-11',
  devtools: { enabled: true },
  typescript: {
    strict: true,
    typeCheck: true,
    tsConfig: {
      compilerOptions: {
        types: ['node', 'vidstack/vue'],
      },
      exclude: ['**/*.spec.ts'],
    },
  },
  vue: {
    compilerOptions: {
      isCustomElement: (tag) => tag.startsWith('media-'),
    },
  },
  modules: ['@nuxt/eslint', '@nuxtjs/i18n', '@nuxt/ui'],
  build: {
    transpile: ['vidstack'],
  },
  vite: {
    optimizeDeps: {
      exclude: ['monaco-editor'],
    },
  },
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
