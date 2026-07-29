import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-11',
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },
  features: {
    inlineStyles: false,
  },
  devtools: { enabled: process.env.NUXT_DEVTOOLS !== 'false' },
  typescript: {
    strict: true,
    typeCheck: process.env.NUXT_TYPE_CHECK !== 'false',
    tsConfig: {
      compilerOptions: {
        types: ['node', 'vidstack/vue'],
      },
      exclude: ['**/*.spec.ts', 'e2e/**', 'playwright.config.ts'],
    },
  },
  vue: {
    compilerOptions: {
      isCustomElement: (tag) => tag.startsWith('media-'),
    },
  },
  modules: [
    ...(process.env.NUXT_SKIP_ESLINT === 'true' ? [] : ['@nuxt/eslint']),
    '@nuxtjs/i18n',
  ],
  build: {
    transpile: ['vidstack', 'mermaid'],
  },

  sourcemap: process.env.NUXT_SOURCEMAP === 'true',
  vite: {
    plugins: [tailwindcss()],
    build: {
      cssCodeSplit: false,
      reportCompressedSize: false,
      sourcemap: process.env.NUXT_SOURCEMAP === 'true',
    },
    optimizeDeps: {
      exclude: ['monaco-editor'],
      include: ['mermaid'],
    },
    server: {

      proxy: {
        '/api': {
          target: process.env.NUXT_DEV_API_PROXY || 'http://127.0.0.1',
          changeOrigin: true,
          ws: true,
        },
      },
    },
  },
  nitro: {
    sourceMap: process.env.NUXT_SOURCEMAP === 'true',
    devProxy: {
      '/api': {
        target: process.env.NUXT_DEV_API_PROXY || 'http://127.0.0.1',
        changeOrigin: true,
      },
    },
  },
  runtimeConfig: {
    apiBaseInternal: process.env.API_BASE_INTERNAL || 'http://studio-api:8000',
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
    bundle: {
      optimizeTranslationDirective: false,
    },
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
