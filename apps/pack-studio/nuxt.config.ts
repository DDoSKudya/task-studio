import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-11',
  css: ['~/assets/css/main.css'],
  features: {
    inlineStyles: false,
  },
  devtools: { enabled: process.env.NUXT_DEVTOOLS !== 'false' },
  app: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/pack-studio/',
    head: {
      link: [
        {
          rel: 'icon',
          type: 'image/svg+xml',
          href: `${(process.env.NUXT_APP_BASE_URL || '/pack-studio/').replace(/\/?$/, '/') }favicon.svg`,
        },
      ],
    },
  },
  typescript: {
    strict: true,
    typeCheck: process.env.NUXT_TYPE_CHECK !== 'false',
    tsConfig: {
      exclude: ['**/*.spec.ts'],
    },
  },
  modules: [
    ...(process.env.NUXT_SKIP_ESLINT === 'true' ? [] : ['@nuxt/eslint']),
    '@nuxtjs/i18n',
  ],
  sourcemap: process.env.NUXT_SOURCEMAP === 'true',
  vite: {
    plugins: [tailwindcss()],
    build: {
      cssCodeSplit: true,
      reportCompressedSize: false,
      sourcemap: process.env.NUXT_SOURCEMAP === 'true',
    },
  },
  nitro: {
    sourceMap: process.env.NUXT_SOURCEMAP === 'true',
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api',
    },
  },
  i18n: {
    strategy: 'no_prefix',
    defaultLocale: 'en',
    locales: [
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ru', name: 'Русский', file: 'ru.json' },
    ],
    langDir: 'locales',

    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'task_studio_locale',
      cookieSecure: false,
      fallbackLocale: 'en',
      alwaysRedirect: false,
      redirectOn: 'root',
    },
  },
})
