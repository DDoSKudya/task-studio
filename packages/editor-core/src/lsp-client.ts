import type * as Monaco from 'monaco-editor'

import { buildLspWebSocketUrl } from './editor-policy'

export type LspClientHandle = {
  dispose: () => void
}

type JsonRpcId = number | string

type JsonRpcMessage = {
  jsonrpc: '2.0'
  id?: JsonRpcId
  method?: string
  params?: unknown
  result?: unknown
  error?: { code: number; message: string; data?: unknown }
}

export type ConnectLanguageClientOptions = {
  apiBase: string
  lspId: string
  sessionId: string
  languageId: string
  rootUri: string
  documentUri: string
  getText: () => string
  model: Monaco.editor.ITextModel
  onReady?: () => void
}

const LANGUAGE_EXT: Record<string, string> = {
  python: 'py',
  javascript: 'js',
  typescript: 'ts',
  go: 'go',
  sql: 'sql',
}

export function documentUriForSession(sessionId: string, languageId: string): string {
  const ext = LANGUAGE_EXT[languageId] ?? 'txt'
  return `file:///session/${sessionId}/main.${ext}`
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

async function openSocket(url: string, attempts = 8): Promise<WebSocket> {
  let lastError: Error | null = null
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await new Promise<WebSocket>((resolve, reject) => {
        const ws = new WebSocket(url)
        const onOpen = () => {
          cleanup()
          resolve(ws)
        }
        const onError = () => {
          cleanup()
          reject(new Error('lsp websocket failed'))
        }
        const cleanup = () => {
          ws.removeEventListener('open', onOpen)
          ws.removeEventListener('error', onError)
        }
        ws.addEventListener('open', onOpen)
        ws.addEventListener('error', onError)
      })
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))
      if (attempt < attempts) {
        await sleep(250 * attempt)
      }
    }
  }
  throw lastError ?? new Error('lsp websocket failed')
}

function asCompletionItems(
  monaco: typeof Monaco,
  result: unknown,
  range: Monaco.IRange,
): Monaco.languages.CompletionItem[] {
  const payload = result as { items?: unknown[] } | unknown[] | null | undefined
  const rows = Array.isArray(payload) ? payload : payload?.items
  if (!Array.isArray(rows)) {
    return []
  }
  const Kind = monaco.languages.CompletionItemKind
  const kindMap: Record<number, Monaco.languages.CompletionItemKind> = {
    1: Kind.Text,
    2: Kind.Method,
    3: Kind.Function,
    4: Kind.Constructor,
    5: Kind.Field,
    6: Kind.Variable,
    7: Kind.Class,
    8: Kind.Interface,
    9: Kind.Module,
    10: Kind.Property,
    11: Kind.Unit,
    12: Kind.Value,
    13: Kind.Enum,
    14: Kind.Keyword,
    15: Kind.Snippet,
    16: Kind.Color,
    17: Kind.File,
    18: Kind.Reference,
    19: Kind.Folder,
    20: Kind.EnumMember,
    21: Kind.Constant,
    22: Kind.Struct,
    23: Kind.Event,
    24: Kind.Operator,
    25: Kind.TypeParameter,
  }
  const out: Monaco.languages.CompletionItem[] = []
  for (const row of rows) {
    if (!row || typeof row !== 'object') {
      continue
    }
    const item = row as {
      label?: string | { label?: string }
      insertText?: string
      detail?: string
      documentation?: string | { value?: string }
      kind?: number
      sortText?: string
      filterText?: string
    }
    const label =
      typeof item.label === 'string'
        ? item.label
        : typeof item.label?.label === 'string'
          ? item.label.label
          : ''
    if (!label) {
      continue
    }
    const documentation =
      typeof item.documentation === 'string'
        ? item.documentation
        : typeof item.documentation?.value === 'string'
          ? item.documentation.value
          : undefined
    out.push({
      label,
      kind: kindMap[item.kind ?? 1] ?? Kind.Text,
      insertText: item.insertText || label,
      detail: item.detail,
      documentation,
      sortText: item.sortText,
      filterText: item.filterText,
      range,
    })
  }
  return out
}


export async function connectLanguageClient(
  monaco: typeof Monaco,
  options: ConnectLanguageClientOptions,
): Promise<LspClientHandle> {
  const url = buildLspWebSocketUrl(options.apiBase, options.lspId, options.sessionId)
  const socket = await openSocket(url)

  let nextId = 1
  let documentVersion = 1
  let disposed = false
  const pending = new Map<
    JsonRpcId,
    { resolve: (value: unknown) => void; reject: (error: Error) => void }
  >()

  const send = (message: JsonRpcMessage) => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message))
    }
  }

  const request = (method: string, params: unknown): Promise<unknown> => {
    const id = nextId
    nextId += 1
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject })
      send({ jsonrpc: '2.0', id, method, params })
    })
  }

  const notify = (method: string, params: unknown) => {
    send({ jsonrpc: '2.0', method, params })
  }

  const onMessage = (event: MessageEvent) => {
    let message: JsonRpcMessage
    try {
      message = JSON.parse(String(event.data)) as JsonRpcMessage
    } catch {
      return
    }
    if (message.id != null && (message.result !== undefined || message.error)) {
      const waiter = pending.get(message.id)
      if (!waiter) {
        return
      }
      pending.delete(message.id)
      if (message.error) {
        waiter.reject(new Error(message.error.message || 'lsp error'))
        return
      }
      waiter.resolve(message.result)
      return
    }
    if (message.method && message.id != null) {
      if (message.method === 'workspace/configuration') {
        const params = message.params as { items?: unknown[] } | undefined
        const count = Array.isArray(params?.items) ? params.items.length : 1
        send({ jsonrpc: '2.0', id: message.id, result: Array.from({ length: count }, () => ({})) })
        return
      }
      send({ jsonrpc: '2.0', id: message.id, result: null })
      return
    }
    if (message.method === 'textDocument/publishDiagnostics') {
      const params = message.params as
        | {
            uri?: string
            diagnostics?: Array<{
              message?: string
              severity?: number
              range?: {
                start: { line: number; character: number }
                end: { line: number; character: number }
              }
            }>
          }
        | undefined
      if (!params?.uri || params.uri !== options.documentUri) {
        return
      }
      const markers: Monaco.editor.IMarkerData[] = []
      for (const item of params.diagnostics ?? []) {
        if (!item.range || !item.message) {
          continue
        }
        const severity =
          item.severity === 1
            ? monaco.MarkerSeverity.Error
            : item.severity === 2
              ? monaco.MarkerSeverity.Warning
              : monaco.MarkerSeverity.Info
        markers.push({
          severity,
          message: item.message,
          startLineNumber: item.range.start.line + 1,
          startColumn: item.range.start.character + 1,
          endLineNumber: item.range.end.line + 1,
          endColumn: item.range.end.character + 1,
        })
      }
      monaco.editor.setModelMarkers(options.model, 'lsp', markers)
    }
  }

  socket.addEventListener('message', onMessage)

  try {
    await request('initialize', {
      processId: null,
      clientInfo: { name: 'task-studio-web', version: '1' },
      rootUri: options.rootUri,
      rootPath: options.rootUri.replace(/^file:\/\//, ''),
      capabilities: {
        textDocument: {
          synchronization: { didSave: false, dynamicRegistration: false },
          completion: {
            completionItem: {
              snippetSupport: false,
              documentationFormat: ['plaintext', 'markdown'],
            },
            contextSupport: true,
          },
          hover: { contentFormat: ['plaintext', 'markdown'] },
          publishDiagnostics: { relatedInformation: false },
        },
        workspace: {
          workspaceFolders: true,
          configuration: true,
          didChangeConfiguration: { dynamicRegistration: false },
        },
      },
      workspaceFolders: [{ uri: options.rootUri, name: 'session' }],
      locale: 'en',
    })
    notify('initialized', {})
    notify('textDocument/didOpen', {
      textDocument: {
        uri: options.documentUri,
        languageId: options.languageId,
        version: documentVersion,
        text: options.getText(),
      },
    })
    options.onReady?.()
  } catch (error) {
    socket.removeEventListener('message', onMessage)
    socket.close()
    throw error
  }

  const changeSub = options.model.onDidChangeContent(() => {
    if (disposed) {
      return
    }
    documentVersion += 1
    notify('textDocument/didChange', {
      textDocument: { uri: options.documentUri, version: documentVersion },
      contentChanges: [{ text: options.getText() }],
    })
  })

  const completionProvider = monaco.languages.registerCompletionItemProvider(options.languageId, {
    triggerCharacters: ['.', '"', "'", '/', '@'],
    provideCompletionItems: async (model, position) => {
      if (disposed || model.uri.toString() !== options.model.uri.toString()) {
        return { suggestions: [] }
      }
      try {
        const result = await request('textDocument/completion', {
          textDocument: { uri: options.documentUri },
          position: {
            line: position.lineNumber - 1,
            character: position.column - 1,
          },
        })
        const word = model.getWordUntilPosition(position)
        const range: Monaco.IRange = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }
        return { suggestions: asCompletionItems(monaco, result, range) }
      } catch {
        return { suggestions: [] }
      }
    },
  })

  const hoverProvider = monaco.languages.registerHoverProvider(options.languageId, {
    provideHover: async (model, position) => {
      if (disposed || model.uri.toString() !== options.model.uri.toString()) {
        return null
      }
      try {
        const result = await request('textDocument/hover', {
          textDocument: { uri: options.documentUri },
          position: {
            line: position.lineNumber - 1,
            character: position.column - 1,
          },
        })
        const hover = result as
          | { contents?: string | { value?: string } | Array<string | { value?: string }> }
          | null
        if (!hover?.contents) {
          return null
        }
        const parts = Array.isArray(hover.contents) ? hover.contents : [hover.contents]
        const value = parts
          .map((part) => (typeof part === 'string' ? part : part?.value || ''))
          .filter(Boolean)
          .join('\n\n')
        if (!value) {
          return null
        }
        return { contents: [{ value }] }
      } catch {
        return null
      }
    },
  })

  return {
    dispose: () => {
      if (disposed) {
        return
      }
      disposed = true
      changeSub.dispose()
      completionProvider.dispose()
      hoverProvider.dispose()
      monaco.editor.setModelMarkers(options.model, 'lsp', [])
      for (const waiter of pending.values()) {
        waiter.reject(new Error('lsp disposed'))
      }
      pending.clear()
      socket.removeEventListener('message', onMessage)
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    },
  }
}

export async function disconnectLanguageClient(handle: LspClientHandle | null): Promise<void> {
  handle?.dispose()
}
