import { describe, expect, it } from 'vitest'
import { parseEditorSettings, shouldConnectLsp } from 'editor-core/policy'

describe('editor policy', () => {
  it('disables lsp in assess when pack blocks autocomplete', () => {
    const settings = parseEditorSettings({})
    expect(
      shouldConnectLsp({
        editorSettings: settings,
        phase: 'assess',
        packAutocomplete: false,
        runtime: 'python',
        lspId: 'pyright',
      }),
    ).toBe(false)
  })

  it('enables lsp in practice by default', () => {
    const settings = parseEditorSettings({})
    expect(
      shouldConnectLsp({
        editorSettings: settings,
        phase: 'practice',
        packAutocomplete: false,
        runtime: 'python',
        lspId: 'pyright',
      }),
    ).toBe(true)
  })
})
