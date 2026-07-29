import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['**/*.spec.ts'],
    exclude: ['e2e/**', 'node_modules/**', 'playwright.config.ts'],
  },
})
