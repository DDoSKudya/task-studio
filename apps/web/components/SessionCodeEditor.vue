<script setup lang="ts">
const props = defineProps<{
  modelValue: string
  language?: string
  readOnly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const host = ref<HTMLElement | null>(null)
let editor: import('monaco-editor').editor.IStandaloneCodeEditor | null = null

onMounted(async () => {
  if (!import.meta.client || !host.value) {
    return
  }
  const monaco = await import('monaco-editor')
  editor = monaco.editor.create(host.value, {
    value: props.modelValue,
    language: props.language ?? 'python',
    readOnly: props.readOnly ?? false,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
  })
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor?.getValue() ?? '')
  })
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

onBeforeUnmount(() => {
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
