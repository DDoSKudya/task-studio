import { MonacoLanguageClient } from 'monaco-languageclient'
import type * as Monaco from 'monaco-editor'
import { CloseAction, ErrorAction } from 'vscode-languageclient/browser.js'
import { toSocket, WebSocketMessageReader, WebSocketMessageWriter } from 'vscode-ws-jsonrpc'

import { buildLspWebSocketUrl } from './editor-policy'

export type LspClientHandle = {
  client: MonacoLanguageClient
  socket: WebSocket
}

export async function connectLanguageClient(
  monaco: typeof Monaco,
  options: {
    apiBase: string
    lspId: string
    sessionId: string
    languageId: string
    rootUri: string
  },
): Promise<LspClientHandle> {
  const url = buildLspWebSocketUrl(options.apiBase, options.lspId, options.sessionId)
  const socket = new WebSocket(url)
  await new Promise<void>((resolve, reject) => {
    socket.onopen = () => resolve()
    socket.onerror = () => reject(new Error('lsp websocket failed'))
  })

  const socketWrapper = toSocket(socket)
  const reader = new WebSocketMessageReader(socketWrapper)
  const writer = new WebSocketMessageWriter(socketWrapper)
  const client = new MonacoLanguageClient({
    name: `${options.languageId} language client`,
    clientOptions: {
      documentSelector: [options.languageId],
      errorHandler: {
        error: () => ({ action: ErrorAction.Continue }),
        closed: () => ({ action: CloseAction.DoNotRestart }),
      },
    },
    messageTransports: {
      reader,
      writer,
    },
  })
  await client.start()
  return { client, socket }
}

export async function disconnectLanguageClient(handle: LspClientHandle | null): Promise<void> {
  if (!handle) {
    return
  }
  await handle.client.stop()
  handle.socket.close()
}
