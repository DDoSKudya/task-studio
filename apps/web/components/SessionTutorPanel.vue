<script setup lang="ts">
const props = defineProps<{
  sessionId: string
  stepId: string
  mode: 'hint' | 'chat'
}>()

const { t } = useI18n()
const { getHints, streamChat } = useTutor()

const open = ref(false)
const pending = ref(false)
const hints = ref<string[]>([])
const messages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([])
const draft = ref('')
const errorMessage = ref('')

async function onShowHints() {
  pending.value = true
  errorMessage.value = ''
  try {
    const response = await getHints(props.sessionId, props.stepId)
    hints.value = response.hints
    open.value = true
  } catch {
    errorMessage.value = t('tutor.errors.hintsFailed')
  } finally {
    pending.value = false
  }
}

async function onSend() {
  const message = draft.value.trim()
  if (!message || pending.value) {
    return
  }
  pending.value = true
  errorMessage.value = ''
  messages.value.push({ role: 'user', content: message })
  draft.value = ''
  open.value = true

  let assistant = ''
  messages.value.push({ role: 'assistant', content: '' })

  try {
    await streamChat(props.sessionId, message, (event) => {
      if (event.type === 'token' && event.content) {
        assistant += event.content
        const last = messages.value.at(-1)
        if (last?.role === 'assistant') {
          last.content = assistant
        }
      }
      if (event.type === 'error' && event.content) {
        errorMessage.value = event.content
      }
    })
  } catch {
    errorMessage.value = t('tutor.errors.chatFailed')
    messages.value.pop()
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex flex-wrap gap-2">
      <UButton
        variant="outline"
        :loading="pending && mode === 'hint'"
        @click="onShowHints"
      >
        {{ t('tutor.showHints') }}
      </UButton>
      <UButton
        v-if="mode === 'chat'"
        variant="soft"
        @click="open = !open"
      >
        {{ open ? t('tutor.hideChat') : t('tutor.openChat') }}
      </UButton>
    </div>

    <p
      v-if="errorMessage"
      class="text-sm text-red-600"
    >
      {{ errorMessage }}
    </p>

    <UCard v-if="open">
      <div
        v-if="hints.length"
        class="mb-4 space-y-2"
      >
        <p class="text-sm font-medium">
          {{ t('tutor.hintsTitle') }}
        </p>
        <ul class="list-disc space-y-1 pl-5 text-sm">
          <li
            v-for="hint in hints"
            :key="hint"
          >
            {{ hint }}
          </li>
        </ul>
      </div>

      <div
        v-if="mode === 'chat'"
        class="space-y-3"
      >
        <div class="max-h-48 space-y-2 overflow-y-auto text-sm">
          <p
            v-for="(message, index) in messages"
            :key="index"
            :class="message.role === 'user' ? 'text-muted' : ''"
          >
            <span class="font-medium">{{ message.role === 'user' ? t('tutor.you') : t('tutor.tutor') }}:</span>
            {{ message.content }}
          </p>
        </div>
        <form
          class="flex gap-2"
          @submit.prevent="onSend"
        >
          <UInput
            v-model="draft"
            class="flex-1"
            :placeholder="t('tutor.messagePlaceholder')"
          />
          <UButton
            type="submit"
            :loading="pending"
            :disabled="!draft.trim()"
          >
            {{ t('tutor.send') }}
          </UButton>
        </form>
      </div>
    </UCard>
  </div>
</template>
