import type { AdapterInfo } from '~/utils/search'

export function fieldsForAdapter(adapter: AdapterInfo): string[] {
  const required = adapter.auth?.settings_fields ?? []
  const optional = adapter.auth?.optional_settings_fields ?? []
  if (required.length || optional.length) {
    return [...required, ...optional.filter((field) => !required.includes(field))]
  }
  return ['api_key']
}

export function requiredFieldsForAdapter(adapter: AdapterInfo): string[] {
  const required = adapter.auth?.settings_fields ?? []
  if (required.length) {
    return required
  }
  return fieldsForAdapter(adapter)
}

export function isOptionalAdapterField(adapter: AdapterInfo, field: string): boolean {
  const required = new Set(requiredFieldsForAdapter(adapter))
  if (required.has(field)) {
    return false
  }
  return (adapter.auth?.optional_settings_fields ?? []).includes(field)
}

export function platformCapabilityLabels(
  adapter: AdapterInfo,
  labels: { import: string, search: string },
): string {
  const parts: string[] = []
  if (adapter.capabilities.import_course) {
    parts.push(labels.import)
  }
  if (adapter.capabilities.search_catalog) {
    parts.push(labels.search)
  }
  return parts.join(' · ')
}
