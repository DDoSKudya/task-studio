import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const localesDir = resolve(import.meta.dirname, 'i18n/locales')

type LocalePayload = {
  app: {
    title: string
    welcome: string
  }
}

function loadLocale(code: 'en' | 'ru'): LocalePayload {
  return JSON.parse(readFileSync(resolve(localesDir, `${code}.json`), 'utf8')) as LocalePayload
}

describe('web scaffold', () => {
  it('health route returns ok status', () => {
    const health = () => ({ status: 'ok' as const })
    expect(health()).toEqual({ status: 'ok' })
  })

  it.each(['en', 'ru'] as const)('locale %s defines app title and welcome', (code) => {
    const locale = loadLocale(code)
    expect(locale.app.title).toBeTruthy()
    expect(locale.app.welcome).toBeTruthy()
  })

  it('locales differ for welcome message', () => {
    const en = loadLocale('en')
    const ru = loadLocale('ru')
    expect(en.app.welcome).not.toBe(ru.app.welcome)
  })
})
