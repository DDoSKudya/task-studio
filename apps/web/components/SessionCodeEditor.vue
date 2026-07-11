<script setup lang="ts">
import {
  configureMonacoEnvironment,
  connectLanguageClient,
  disconnectLanguageClient,
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
const languageId = computed(() => props.language ?? 'python')

async function setupLsp(monaco: typeof import('monaco-editor')) {
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

  await sendBeacon('open', { language: props.lspId, sessionId: props.sessionId })
  lspHandle = await connectLanguageClient(monaco, {
    apiBase: apiBase(),
    lspId: props.lspId,
    sessionId: props.sessionId,
    languageId: runtime,
    rootUri: `file:///session/${props.sessionId}`,
  })
}

onMounted(async () => {
  if (!import.meta.client || !host.value) {
    return
  }
  configureMonacoEnvironment()
  const monaco = await import('monaco-editor')
  await registerGrammar(monaco, languageId.value)
  editor = monaco.editor.create(host.value, {
    value: props.modelValue,
    language: languageId.value,
    readOnly: props.readOnly ?? false,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
  })
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor?.getValue() ?? '')
  })
  try {
    await setupLsp(monaco)
  } catch {
    // syntax-only fallback
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
  if (props.lspId) {
    await sendBeacon('close', { language: props.lspId, sessionId: props.sessionId })
  }
  await disconnectLanguageClient(lspHandle)
  lspHandle = null
  editor?.dispose()
  editor = null
})
</script>

<template>
  <div
    ref="host"
    class="h-72 w-full rounded-md border border-default"
  />
</template>
