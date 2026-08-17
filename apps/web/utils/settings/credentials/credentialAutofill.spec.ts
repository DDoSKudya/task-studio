import { describe, expect, it } from 'vitest'
import { credentialFieldKey, isSecretCredentialField } from './credentialAutofill'

describe('credentialAutofill helpers', () => {
  it('marks password and secret-like fields', () => {
    expect(isSecretCredentialField('password')).toBe(true)
    expect(isSecretCredentialField('client_secret')).toBe(true)
    expect(isSecretCredentialField('api_key')).toBe(true)
    expect(isSecretCredentialField('access_token')).toBe(true)
    expect(isSecretCredentialField('username')).toBe(false)
    expect(isSecretCredentialField('client_id')).toBe(false)
  })

  it('builds stable field keys', () => {
    expect(credentialFieldKey('stepik', 'password')).toBe('stepik:password')
  })
})
