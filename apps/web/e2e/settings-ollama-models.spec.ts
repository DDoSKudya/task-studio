import { expect, test } from '@playwright/test'

const models = ['phi4-mini', 'qwen2.5', 'tinyllama']

test('settings shows all Ollama models in dropdown', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user: {
          id: '11111111-1111-1111-1111-111111111111',
          email: 'e2e-settings@example.com',
          locale: 'en',
          theme: 'system',
        },
        settings: {
          tutor: {
            active_provider: 'ollama',
            provider_url: '',
            daily_limit: 0,
            model: '',
          },
          integrations: {},
        },
      }),
    })
  })

  await page.route('**/api/v1/integrations', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/tutor/llm-status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        provider: 'ollama',
        detail: 'Ollama is ready',
        models,
        default_model: 'qwen2.5',
      }),
    })
  })

  await page.goto('/settings')
  await page.getByRole('button', { name: 'AI agent' }).click()
  await page.getByText('Local agent').click()

  const modelSelect = page.locator('select[required][aria-required="true"]').first()
  await expect(modelSelect).toBeVisible()

  await expect.poll(async () => {
    return modelSelect.locator('option').evaluateAll((nodes) =>
      nodes
        .map((node) => node.textContent?.trim() ?? '')
        .filter((text) => Boolean(text)),
    )
  }).toEqual(['Select a model', 'phi4-mini', 'qwen2.5', 'tinyllama'])
})
