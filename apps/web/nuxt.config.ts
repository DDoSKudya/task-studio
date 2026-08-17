import tailwindcss from '@tailwindcss/vite'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

type AppVersionFile = {
  version?: string
  build?: number | string
  channel?: string
}

function loadAppVersion(): Required<AppVersionFile> {
  const fallback = {
    version: '0.0.0-develop',
    build: 0,
    channel: 'develop',
  }
  try {
    const root = dirname(fileURLToPath(import.meta.url))
    const raw = JSON.parse(
      readFileSync(join(root, 'app-version.json'), 'utf8'),
    ) as AppVersionFile
    return {
      version: String(raw.version || fallback.version),
      build: Number(raw.build) || 0,
      channel: String(raw.channel || fallback.channel),
    }
  } catch {
    return fallback
  }
}

const appVersion = loadAppVersion()

export default defineNuxtConfig({
  compatibilityDate: '2025-07-11',
  css: ['~/assets/css/main.css'],
  components: [{ path: '~/components', pathPrefix: false }],
  imports: {
    dirs: ['~/composables', '~/composables/**'],
  },
  app: {
    head: {
      title: 'Task Studio',
      titleTemplate: '%s · Task Studio',
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
        types: ['node'],
      },
      exclude: ['**/*.spec.ts', 'e2e/**', 'playwright.config.ts'],
    },
  },
  modules: [
    ...(process.env.NUXT_SKIP_ESLINT === 'true' ? [] : ['@nuxt/eslint']),
    '@nuxtjs/i18n',
  ],
  build: {
    transpile: ['mermaid'],
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
      appVersion: process.env.NUXT_PUBLIC_APP_VERSION || appVersion.version,
      appBuild: process.env.NUXT_PUBLIC_APP_BUILD || String(appVersion.build),
      appChannel: process.env.NUXT_PUBLIC_APP_CHANNEL || appVersion.channel,
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
