

export function isSecretCredentialField(field: string): boolean {
  return (
    field === 'password'
    || field.includes('secret')
    || field.includes('token')
    || field.includes('key')
  )
}

export function credentialFieldKey(platformId: string, field: string): string {
  return `${platformId}:${field}`
}
