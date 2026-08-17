import type { AdapterInfo } from '~/utils/search'
import {
  fieldsForAdapter,
  isOptionalAdapterField,
  platformCapabilityLabels,
  requiredFieldsForAdapter,
} from './integrationFields'

type TranslateFn = (key: string, params?: Record<string, unknown> | string) => string

export function fieldsFor(adapter: AdapterInfo) {
  return fieldsForAdapter(adapter)
}

export function requiredFieldsFor(adapter: AdapterInfo) {
  return requiredFieldsForAdapter(adapter)
}

export function isOptionalField(adapter: AdapterInfo, field: string) {
  return isOptionalAdapterField(adapter, field)
}

export function fieldHint(t: TranslateFn, adapter: AdapterInfo, field: string) {
  if (isOptionalField(adapter, field)) {
    return t('settings.integrations.optionalField')
  }
  return ''
}

export function fieldPlaceholder(t: TranslateFn, adapter: AdapterInfo, field: string) {
  if (adapter.id === 'stepik' && field === 'client_id') {
    return t('settings.integrations.stepik.clientIdPlaceholder')
  }
  return ''
}

export function platformHelp(t: TranslateFn, adapter: AdapterInfo) {
  if (adapter.id === 'stepik') {
    return t('settings.integrations.stepik.help')
  }
  return t('settings.integrations.credentialsMeta')
}

export function authTypeLabel(t: TranslateFn, adapter: AdapterInfo) {
  const authType = adapter.auth?.type
  if (!authType) {
    return t('settings.integrations.authTypes.none')
  }
  return t(`settings.integrations.authTypes.${authType}`, authType)
}

export function fieldLabel(t: TranslateFn, field: string) {
  return t(`settings.integrations.fields.${field}`, field.replace(/_/g, ' '))
}

export function platformCapabilities(
  t: TranslateFn,
  adapter: AdapterInfo,
) {
  return platformCapabilityLabels(adapter, {
    import: t('settings.integrations.capImport'),
    search: t('settings.integrations.capSearch'),
  })
}
