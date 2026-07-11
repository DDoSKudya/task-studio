<script setup lang="ts">
const { t } = useI18n()
const { user, fetchMe, logout } = useAuth()
const { validateManifest, buildPack, suggestFragment } = useStudio()
const { uploadPack } = useCatalog()
const router = useRouter()

const pending = ref(true)
const actionPending = ref(false)
const errorMessage = ref('')
const validationMessage = ref('')
const uploadMessage = ref('')
const suggestPrompt = ref('')
const manifestText = ref(`{
  "schema_version": 1,
  "id": "my-pack",
  "version": "1.0.0",
  "title": "My Pack",
  "source": { "type": "local" },
  "topics": [
    {
      "id": "topic-1",
      "title": "Intro",
      "phases": {
        "study": ["theory-1"],
        "practice": ["lab-1"],
        "assess": []
      }
    }
  ],
  "steps": {
    "theory-1": {
      "kind": "theory",
      "title": "Welcome",
      "content": "Lab pack example."
    },
    "lab-1": {
      "kind": "lab",
      "title": "Start nginx",
      "instructions": "Bring up the lab stack and verify nginx responds.",
      "compose_file": "lab/compose.yaml",
      "timeout_seconds": 120,
      "checks": [
        {
          "type": "command",
          "command": "wget -qO- http://localhost:8080 | grep -q nginx",
          "expect_exit_code": 0
        }
      ]
    }
  },
  "policies": {
    "skip_study_allowed": true,
    "assess_without_practice": false,
    "assess_autocomplete": false,
    "tutor_enabled": false
  }
}`)

onMounted(async () => {
  try {
    await fetchMe()
  } catch {
    await router.push('/login')
    return
  } finally {
    pending.value = false
  }
})

function parseManifest(): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(manifestText.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('not object')
    }
    return parsed as Record<string, unknown>
  } catch {
    throw createError({ statusCode: 422, message: t('editor.errors.invalidJson') })
  }
}

async function onValidate() {
  actionPending.value = true
  errorMessage.value = ''
  validationMessage.value = ''
  try {
    const manifest = parseManifest()
    const result = await validateManifest(manifest)
    if (result.valid) {
      validationMessage.value = t('editor.valid')
    } else {
      validationMessage.value = result.errors.map((issue) => `${issue.path}: ${issue.message}`).join('\n')
    }
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onBuild() {
  actionPending.value = true
  errorMessage.value = ''
  try {
    const manifest = parseManifest()
    const blob = await buildPack(manifest, [])
    const slug = typeof manifest.id === 'string' ? manifest.id : 'pack'
    const version = typeof manifest.version === 'string' ? manifest.version : '1.0.0'
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${slug}-${version}.studio-pack`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onUpload() {
  actionPending.value = true
  errorMessage.value = ''
  uploadMessage.value = ''
  try {
    const manifest = parseManifest()
    const blob = await buildPack(manifest, [])
    const slug = typeof manifest.id === 'string' ? manifest.id : 'pack'
    const version = typeof manifest.version === 'string' ? manifest.version : '1.0.0'
    const file = new File([blob], `${slug}-${version}.studio-pack`, { type: 'application/zip' })
    const response = await uploadPack(file)
    uploadMessage.value = t('editor.uploaded', { title: response.title, version: response.version })
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onSuggest() {
  if (!suggestPrompt.value.trim()) {
    return
  }
  actionPending.value = true
  errorMessage.value = ''
  try {
    const manifest = parseManifest()
    const result = await suggestFragment({
      context: 'pack authoring',
      step_kind: 'lab',
      prompt: suggestPrompt.value,
      manifest_fragment: manifest,
    })
    manifestText.value = JSON.stringify(result.suggestion, null, 2)
  } catch {
    errorMessage.value = t('editor.errors.actionFailed')
  } finally {
    actionPending.value = false
  }
}

async function onLogout() {
  await logout()
  await router.push('/login')
}
</script>

<template>
  <UContainer class="py-8 space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold">
          {{ t('app.title') }}
        </h1>
        <p class="text-sm text-muted">
          {{ t('app.subtitle') }}
        </p>
      </div>
      <div v-if="user" class="flex items-center gap-3 text-sm">
        <span>{{ t('auth.signedInAs', { email: user.email }) }}</span>
        <UButton variant="outline" size="sm" @click="onLogout">
          {{ t('auth.logout') }}
        </UButton>
      </div>
    </div>

    <p v-if="pending" class="text-sm text-muted">
      {{ t('editor.loading') }}
    </p>

    <template v-else>
      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ t('editor.manifest') }}
          </h2>
        </template>

        <UTextarea
          v-model="manifestText"
          :rows="24"
          class="font-mono text-sm w-full"
        />

        <div class="mt-4 flex flex-wrap gap-2">
          <UButton :loading="actionPending" @click="onValidate">
            {{ t('editor.validate') }}
          </UButton>
          <UButton variant="outline" :loading="actionPending" @click="onBuild">
            {{ t('editor.build') }}
          </UButton>
          <UButton variant="soft" :loading="actionPending" @click="onUpload">
            {{ t('editor.upload') }}
          </UButton>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="font-semibold">
            {{ t('editor.suggest') }}
          </h2>
        </template>
        <div class="space-y-3">
          <UInput v-model="suggestPrompt" :placeholder="t('editor.suggestPrompt')" />
          <UButton :loading="actionPending" @click="onSuggest">
            {{ t('editor.suggest') }}
          </UButton>
        </div>
      </UCard>

      <p v-if="validationMessage" class="text-sm whitespace-pre-wrap">
        {{ validationMessage }}
      </p>
      <p v-if="uploadMessage" class="text-sm text-green-700">
        {{ uploadMessage }}
      </p>
      <p v-if="errorMessage" class="text-sm text-red-600">
        {{ errorMessage }}
      </p>
    </template>
  </UContainer>
</template>
