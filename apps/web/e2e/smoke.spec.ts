import path from 'node:path'

import { expect, test } from '@playwright/test'

const samplePack = path.join(import.meta.dirname, 'fixtures', 'intro-python.studio-pack')

test('register, upload pack, and open session', async ({ page }) => {
  const email = `e2e-${crypto.randomUUID()}@example.com`
  const password = 'password12345'

  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText(email)).toBeVisible()

  await page.goto('/catalog')
  await page.locator('input[type="file"]').setInputFiles(samplePack)
  await expect(page.getByRole('link', { name: 'Intro Python' })).toBeVisible({ timeout: 30_000 })

  await page.getByRole('link', { name: 'Intro Python' }).click()
  await page.getByRole('button', { name: 'Start session' }).click()

  await expect(page).toHaveURL(/\/sessions\/[0-9a-f-]+$/)
  await expect(page.getByRole('heading', { name: 'Hello Python' })).toBeVisible()
})
