import { EDITOR_RUNTIMES, type TutorProviderMode } from './tutorForm'

export function clonePlain<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

export function jsonEqual(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right)
}

export function integrationDraftDirty(
  draft: Record<string, string> | undefined,
  baseline: Record<string, string> | undefined,
): boolean {
  return !jsonEqual(clonePlain(draft ?? {}), baseline ?? {})
}

export function languagesMapDirty(
  current: Record<string, boolean>,
  baseline: Record<string, boolean>,
  runtimes: readonly string[] = EDITOR_RUNTIMES,
): boolean {
  return runtimes.some((runtime) => current[runtime] !== baseline[runtime])
}

export type TutorDirtySnapshot = {
  providerUrl: string
  providerMode: TutorProviderMode
  dailyLimit: number
  model: string
}

export function tutorFormDirty(
  form: { providerUrl: string; apiKey: string; dailyLimit: number; model: string },
  providerMode: TutorProviderMode,
  baseline: TutorDirtySnapshot,
): boolean {
  if (form.apiKey.trim()) {
    return true
  }
  return (
    form.providerUrl !== baseline.providerUrl
    || providerMode !== baseline.providerMode
    || form.dailyLimit !== baseline.dailyLimit
    || form.model !== baseline.model
  )
}

export function credentialValuePresent(
  values: Record<string, string> | undefined,
  field: string,
): boolean {
  if (!values) {
    return false
  }
  if (values[field]?.trim()) {
    return true
  }

  return Boolean(values[`${field}_encrypted`]?.trim())
}

export function requiredFieldsFilled(
  fields: string[],
  values: Record<string, string> | undefined,
): boolean {
  if (!values) {
    return false
  }
  return fields.every((field) => credentialValuePresent(values, field))
}

export function settingsFormDirty(input: {
  tutorDirty: boolean
  autocomplete: boolean
  baselineAutocomplete: boolean
  mode: string
  baselineMode: string
  languagesDirty: boolean
  integrationDrafts: Record<string, Record<string, string>>
  baselineIntegrations: Record<string, Record<string, string>>
}): boolean {
  if (input.tutorDirty) {
    return true
  }
  if (
    input.autocomplete !== input.baselineAutocomplete
    || input.mode !== input.baselineMode
    || input.languagesDirty
  ) {
    return true
  }
  return !jsonEqual(clonePlain(input.integrationDrafts), input.baselineIntegrations)
}
