import { describe, expect, it } from 'vitest'
import type { AdapterInfo } from '../../search'
import {
  fieldsForAdapter,
  isOptionalAdapterField,
  requiredFieldsForAdapter,
} from './integrationFields'

function adapter(partial: {
  id: string
  auth?: AdapterInfo['auth']
}): AdapterInfo {
  return {
    id: partial.id,
    version: '1',
    display_name: partial.id,
    capabilities: {
      import_course: true,
      search_catalog: true,
      requires_auth: true,
      content_types: [],
    },
    auth: partial.auth ?? null,
  }
}

describe('settingsIntegrationFields', () => {
  it('merges required and optional fields without duplicates', () => {
    const item = adapter({
      id: 'stepik',
      auth: {
        type: 'oauth',
        settings_fields: ['username', 'password'],
        optional_settings_fields: ['password', 'client_id'],
      },
    })
    expect(fieldsForAdapter(item)).toEqual(['username', 'password', 'client_id'])
    expect(requiredFieldsForAdapter(item)).toEqual(['username', 'password'])
    expect(isOptionalAdapterField(item, 'client_id')).toBe(true)
    expect(isOptionalAdapterField(item, 'password')).toBe(false)
  })

  it('falls back to api_key when auth fields missing', () => {
    expect(fieldsForAdapter(adapter({ id: 'x' }))).toEqual(['api_key'])
  })
})
