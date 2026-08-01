import { credentialFieldKey, isSecretCredentialField } from '~/utils/settings'

export { credentialFieldKey, isSecretCredentialField }

export function useCredentialAutofill(resetSignal?: () => unknown) {
  const unlockedCredentialFields = ref<Record<string, true>>({})

  if (resetSignal) {
    watch(resetSignal, () => {
      unlockedCredentialFields.value = {}
    })
  }

  function unlockCredentialField(key: string) {
    if (unlockedCredentialFields.value[key]) {
      return
    }
    unlockedCredentialFields.value = { ...unlockedCredentialFields.value, [key]: true }
  }

  function isCredentialFieldUnlocked(key: string) {
    return Boolean(unlockedCredentialFields.value[key])
  }

  return {
    unlockCredentialField,
    isCredentialFieldUnlocked,
  }
}
