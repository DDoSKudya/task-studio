<script setup lang="ts">
import {
  configureMonacoEnvironment,
  connectLanguageClient,
  disconnectLanguageClient,
  documentUriForSession,
  parseEditorSettings,
  registerGrammar,
  shouldConnectLsp,
  type LspClientHandle,
} from 'editor-core'

const props = defineProps<{
  modelValue: string
  language?: string
  readOnly?: boolean
  sessionId: string
  phase: 'study' | 'practice' | 'assess'
  packAutocomplete: boolean
  lspId?: string | null
  editorSettings?: Record<string, unknown>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { apiBase, sendBeacon } = useEditor()
const host = ref<HTMLElement | null>(null)
let editor: import('monaco-editor').editor.IStandaloneCodeEditor | null = null
let lspHandle: LspClientHandle | null = null
let disposed = false
const languageId = computed(() => props.language ?? 'python')
const MONACO_THEME = 'task-studio-ink'

function defineEditorTheme(monaco: typeof import('monaco-editor')) {
  monaco.editor.defineTheme(MONACO_THEME, {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: '', foreground: 'F0F0F5' },
      { token: 'comment', foreground: '6B6B78', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'E8D5FF', fontStyle: 'bold' },
      { token: 'string', foreground: '9AD7B3' },
      { token: 'number', foreground: 'F0C38A' },
      { token: 'type', foreground: 'B366FF' },
      { token: 'class', foreground: 'B366FF' },
      { token: 'function', foreground: 'F5F5FA' },
      { token: 'variable', foreground: 'F0F0F5' },
      { token: 'constant', foreground: 'FFD700' },
      { token: 'operator', foreground: 'C8C8D0' },
      { token: 'delimiter', foreground: 'A0A0A8' },
    ],
    colors: {
      'editor.background': '#0C0C12',
      'editor.foreground': '#F0F0F5',
      'editorLineNumber.foreground': '#5A5A68',
      'editorLineNumber.activeForeground': '#B366FF',
      'editorCursor.foreground': '#B366FF',
      'editor.selectionBackground': '#B366FF33',
      'editor.inactiveSelectionBackground': '#B366FF18',
      'editor.lineHighlightBackground': '#FFFFFF08',
      'editorIndentGuide.background': '#FFFFFF12',
      'editorIndentGuide.activeBackground': '#B366FF44',
      'editorWidget.background': '#10101A',
      'editorWidget.border': '#FFFFFF22',
      'input.background': '#0A0A10',
      'focusBorder': '#B366FF',
      'scrollbar.shadow': '#00000000',
      'scrollbarSlider.background': '#FFFFFF33',
      'scrollbarSlider.hoverBackground': '#B366FF8C',
      'scrollbarSlider.activeBackground': '#B366FFB8',
    },
  })
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

async function setupLsp(
  monaco: typeof import('monaco-editor'),
  model: import('monaco-editor').editor.ITextModel,
) {
  const settings = parseEditorSettings(props.editorSettings)
  const runtime = languageId.value
  if (
    !shouldConnectLsp({
      editorSettings: settings,
      phase: props.phase,
      packAutocomplete: props.packAutocomplete,
      runtime,
      lspId: props.lspId,
    })
    || !props.lspId
  ) {
    return
  }

  try {
    await sendBeacon('open', { language: props.lspId, sessionId: props.sessionId })
  } catch (error) {
    console.warn('[editor] lsp beacon failed', error)
  }

  const rootUri = `file:///session/${props.sessionId}`
  const documentUri = documentUriForSession(props.sessionId, runtime)
  const options = {
    apiBase: apiBase(),
    lspId: props.lspId,
    sessionId: props.sessionId,
    languageId: runtime,
    rootUri,
    documentUri,
    getText: () => editor?.getValue() ?? '',
    model,
  }


  let lastError: unknown = null
  for (let attempt = 1; attempt <= 8; attempt += 1) {
    if (disposed) {
      return
    }
    try {
      lspHandle = await connectLanguageClient(monaco, options)
      return
    } catch (error) {
      lastError = error
      await sleep(300 * attempt)
    }
  }
  throw lastError instanceof Error ? lastError : new Error('lsp connect failed')
}

onMounted(async () => {
  if (!import.meta.client || !host.value) {
    return
  }
  configureMonacoEnvironment()
  const monaco = await import('monaco-editor')
  if (disposed) {
    return
  }
  await registerGrammar(monaco, languageId.value)
  defineEditorTheme(monaco)
  monaco.editor.setTheme(MONACO_THEME)

  const documentUri = documentUriForSession(props.sessionId, languageId.value)
  const model = monaco.editor.createModel(
    props.modelValue,
    languageId.value,
    monaco.Uri.parse(documentUri),
  )

  editor = monaco.editor.create(host.value, {
    model,
    readOnly: props.readOnly ?? false,
    theme: MONACO_THEME,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 13,
    lineHeight: 20,
    fontFamily: 'JetBrains Mono Variable, JetBrains Mono, ui-monospace, monospace',
    lineNumbers: 'on',
    renderLineHighlight: 'line',
    scrollBeyondLastLine: false,
    padding: { top: 10, bottom: 10 },
    scrollbar: {
      verticalScrollbarSize: 8,
      horizontalScrollbarSize: 8,
    },
    overviewRulerLanes: 0,
    hideCursorInOverviewRuler: true,

    quickSuggestions: { other: true, comments: false, strings: true },
    suggestOnTriggerCharacters: true,
    wordBasedSuggestions: 'off',
    tabCompletion: 'on',
    snippetSuggestions: 'none',
  })
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor?.getValue() ?? '')
  })
  try {
    await setupLsp(monaco, model)
  } catch (error) {
    console.warn('[editor] lsp unavailable, syntax-only mode', error)
  }
})

watch(
  () => props.modelValue,
  (value) => {
    if (!editor || editor.getValue() === value) {
      return
    }
    editor.setValue(value)
  },
)

onBeforeUnmount(async () => {
  disposed = true
  if (props.lspId) {
    try {
      await sendBeacon('close', { language: props.lspId, sessionId: props.sessionId })
    } catch {

    }
  }
  await disconnectLanguageClient(lspHandle)
  lspHandle = null
  const model = editor?.getModel()
  editor?.dispose()
  editor = null
  model?.dispose()
})
</script>

<template>
  <div
    ref="host"
    class="session-code-editor"
  />
</template>
