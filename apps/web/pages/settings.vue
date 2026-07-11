<script setup lang="ts">
import { parseEditorSettings } from 'editor-core'

type TutorSettingsForm = {
  enabled: boolean
  providerUrl: string
  apiKey: string
  dailyLimit: number
  model: string
}

const { t } = useI18n()
const { settings, fetchMe, patchSettings } = useAuth()

const pending = ref(true)
const saving = ref(false)
const autocomplete = ref(true)
const mode = ref<'full' | 'syntax_only'>('full')
const pythonEnabled = ref(true)
const javascriptEnabled = ref(true)
const tutor = ref<TutorSettingsForm>({
  enabled: true,
  providerUrl: '',
  apiKey: '',
  dailyLimit: 0,
  model: '',
})

function parseTutorSettings(raw: Record<string, unknown>) {
  const blob = raw.tutor
  if (!blob || typeof blob !== 'object' || Array.isArray(blob)) {
    return
  }
  const record = blob as Record<string, unknown>
  tutor.value = {
    enabled: record.enabled !== false,
    providerUrl: typeof record.provider_url === 'string' ? record.provider_url : '',
    apiKey: '',
    dailyLimit: typeof record.daily_limit === 'number' ? record.daily_limit : 0,
    model: typeof record.model === 'string' ? record.model : '',
  }
}

onMounted(async () => {
  await fetchMe()
  const editor = parseEditorSettings(settings.value)
  autocomplete.value = editor.autocomplete
  mode.value = editor.mode
  pythonEnabled.value = editor.languages.python?.enabled ?? true
  javascriptEnabled.value = editor.languages.javascript?.enabled ?? true
  parseTutorSettings(settings.value)
  pending.value = false
})

async function onSave() {
  saving.value = true
  try {
    const tutorPayload: Record<string, unknown> = {
      enabled: tutor.value.enabled,
      provider_url: tutor.value.providerUrl || null,
      daily_limit: tutor.value.dailyLimit,
      model: tutor.value.model || null,
    }
    if (tutor.value.apiKey.trim()) {
      tutorPayload.api_key = tutor.value.apiKey.trim()
    }
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
        tutor: tutorPayload,
      },
    })
    tutor.value.apiKey = ''
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

    <div
      v-else
      class="space-y-6"
    >
      <UCard>
        <div class="space-y-4">
          <h2 class="font-medium">
            {{ t('settings.tutorTitle') }}
          </h2>

          <label class="flex items-center gap-2 text-sm">
            <input
              v-model="tutor.enabled"
              type="checkbox"
            >
            <span>{{ t('settings.tutorEnabled') }}</span>
          </label>

          <UInput
            v-model="tutor.providerUrl"
            :placeholder="t('settings.tutorProviderUrl')"
          />

          <UInput
            v-model="tutor.apiKey"
            type="password"
            :placeholder="t('settings.tutorApiKey')"
          />

          <UInput
            v-model.number="tutor.dailyLimit"
            type="number"
            min="0"
            :placeholder="t('settings.tutorDailyLimit')"
          />

          <UInput
            v-model="tutor.model"
            :placeholder="t('settings.tutorModel')"
          />
        </div>
      </UCard>

      <UCard>
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
        </div>
      </UCard>

      <UButton
        :loading="saving"
        @click="onSave"
      >
        {{ t('settings.save') }}
      </UButton>
    </div>
  </UContainer>
</template>
