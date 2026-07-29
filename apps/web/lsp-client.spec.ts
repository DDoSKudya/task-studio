import { describe, expect, it } from 'vitest'
import { buildLspWebSocketUrl, documentUriForSession } from 'editor-core'

describe('lsp client helpers', () => {
  it('builds session document uri with language extension', () => {
    expect(documentUriForSession('abc', 'python')).toBe('file:///session/abc/main.py')
    expect(documentUriForSession('abc', 'javascript')).toBe('file:///session/abc/main.js')
    expect(documentUriForSession('abc', 'go')).toBe('file:///session/abc/main.go')
    expect(documentUriForSession('abc', 'sql')).toBe('file:///session/abc/main.sql')
  })

  it('builds websocket url from api base', () => {
    expect(buildLspWebSocketUrl('/api', 'pyright', 'sess-1')).toBe(
      '/api/v1/lsp/pyright?session_id=sess-1',
    )
    expect(buildLspWebSocketUrl('https://studio.example/api', 'gopls', 's2')).toBe(
      'wss://studio.example/api/v1/lsp/gopls?session_id=s2',
    )
  })
})
