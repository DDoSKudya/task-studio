<script setup lang="ts">
import { parseEditorSettings } from 'editor-core'

const { t } = useI18n()
const { settings, fetchMe, patchSettings } = useAuth()

const pending = ref(true)
const saving = ref(false)
const autocomplete = ref(true)
const mode = ref<'full' | 'syntax_only'>('full')
const pythonEnabled = ref(true)
const javascriptEnabled = ref(true)

onMounted(async () => {
  await fetchMe()
  const editor = parseEditorSettings(settings.value)
  autocomplete.value = editor.autocomplete
  mode.value = editor.mode
  pythonEnabled.value = editor.languages.python?.enabled ?? true
  javascriptEnabled.value = editor.languages.javascript?.enabled ?? true
  pending.value = false
})

async function onSave() {
  saving.value = true
  try {
    await patchSettings({
      settings: {
        editor: {
          autocomplete: autocomplete.value,
          mode: mode.value,
          languages: {
            python: { enabled: pythonEnabled.value },
            javascript: { enabled: javascriptEnabled.value },
          },
        },
      },
    })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UContainer class="py-8 space-y-6 max-w-lg">
    <h1 class="text-2xl font-semibold">
      {{ t('settings.title') }}
    </h1>

    <p
      v-if="pending"
      class="text-sm text-muted"
    >
      {{ t('settings.loading') }}
    </p>

    <UCard v-else>
      <div class="space-y-4">
        <h2 class="font-medium">
          {{ t('settings.editorTitle') }}
        </h2>

        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="autocomplete"
            type="checkbox"
          >
          <span>{{ t('settings.autocomplete') }}</span>
        </label>

        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="mode"
            type="radio"
            value="full"
          >
          <span>{{ t('settings.modeFull') }}</span>
        </label>

        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="mode"
            type="radio"
            value="syntax_only"
          >
          <span>{{ t('settings.modeSyntaxOnly') }}</span>
        </label>

        <div class="space-y-2">
          <p class="text-sm font-medium">
            {{ t('settings.languages') }}
          </p>
          <label class="flex items-center gap-2 text-sm">
            <input
              v-model="pythonEnabled"
              type="checkbox"
            >
            <span>Python</span>
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input
              v-model="javascriptEnabled"
              type="checkbox"
            >
            <span>JavaScript</span>
          </label>
        </div>

        <UButton
          :loading="saving"
          @click="onSave"
        >
          {{ t('settings.save') }}
        </UButton>
      </div>
    </UCard>
  </UContainer>
</template>
