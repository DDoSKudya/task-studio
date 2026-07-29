<script setup lang="ts">
import { LightBulbIcon, PaperAirplaneIcon, TrashIcon } from '@heroicons/vue/24/outline'

import { tutorMessageHtml } from '~/utils/tutor'

const props = withDefaults(
  defineProps<{
    sessionId: string
    stepId: string
    stepKind?: string
    mode: 'hint' | 'chat'
    docked?: boolean
  }>(),
  {
    docked: false,
    stepKind: 'theory',
  },
)

const { t, te } = useI18n()
const { getHints, streamChat } = useTutor()
const toasts = useToasts()
const {
  messages,
  draft,
  clear: clearChat,
  append,
  updateLastAssistant,
  popLast,
  historyBeforeSend,
} = useTutorSessionChat(() => props.sessionId)

const pending = ref(false)
const hintsVisible = ref(false)
const hints = ref<string[]>([])
const messagesEl = ref<HTMLElement | null>(null)

function bubbleHtml(content: string) {
  return tutorMessageHtml(content)
}

watch(
  () => props.stepId,
  () => {
    hints.value = []
    hintsVisible.value = false
  },
)

async function onShowHints() {
  pending.value = true
  try {
    const response = await getHints(props.sessionId, props.stepId)
    hints.value = localizeHints(response.hints, response.source)
    hintsVisible.value = true
  } catch {
    toasts.error(t('tutor.errors.hintsFailed'))
  } finally {
    pending.value = false
  }
}

function localizeHints(raw: string[], source: 'fallback' | 'llm') {
  if (source !== 'fallback') {
    return raw
  }
  const localized: string[] = []
  for (let index = 0; index < 4; index += 1) {
    const key = `tutor.fallback.${props.stepKind}.${index}`
    if (te(key)) {
      localized.push(t(key))
    }
  }
  return localized.length ? localized : raw
}

async function onSend() {
  const message = draft.value.trim()
  if (!message || pending.value) {
    return
  }
  pending.value = true
  const history = historyBeforeSend()
  append({ role: 'user', content: message })
  draft.value = ''
  append({ role: 'assistant', content: '' })
  await nextTick()
  scrollMessages()

  try {
    await streamChat(
      props.sessionId,
      message,
      (event) => {
        if (event.type === 'token' && event.content) {
          const last = messages.value.at(-1)
          const next = `${last?.role === 'assistant' ? last.content : ''}${event.content}`
          updateLastAssistant(next)
          scrollMessages()
        }
        if (event.type === 'error' && event.content) {
          toasts.error(event.content)
        }
      },
      { history },
    )
  } catch {
    toasts.error(t('tutor.errors.chatFailed'))
    popLast()
    popLast()
  } finally {
    pending.value = false
  }
}

function onClearChat() {
  if (pending.value) {
    return
  }
  clearChat()
}

function scrollMessages() {
  const el = messagesEl.value
  if (!el) {
    return
  }
  el.scrollTop = el.scrollHeight
}
</script>

<template>
  <div class="session-tutor" :class="{ 'session-tutor-docked': docked }">
    <header v-if="docked" class="session-tutor-head">
      <div>
        <p class="session-tutor-kicker">{{ t('tutor.dockKicker') }}</p>
        <h3 class="session-tutor-title">{{ t('tutor.dockTitle') }}</h3>
      </div>
      <div class="session-tutor-head-actions">
        <button
          class="session-tutor-tool"
          type="button"
          :disabled="pending || !messages.length"
          :aria-label="t('tutor.clearHistory')"
          :title="t('tutor.clearHistory')"
          @click="onClearChat"
        >
          <TrashIcon class="icon-sm" aria-hidden="true" />
          <span class="session-tutor-tool-label">{{ t('tutor.clearHistory') }}</span>
        </button>
        <button
          class="session-tutor-tool session-tutor-tool-hint"
          type="button"
          :disabled="pending"
          :aria-label="t('tutor.showHints')"
          :title="t('tutor.showHints')"
          @click="onShowHints"
        >
          <LightBulbIcon class="icon-sm" aria-hidden="true" />
          <span class="session-tutor-tool-label">{{ t('tutor.showHints') }}</span>
        </button>
      </div>
    </header>

    <div v-else class="session-tutor-actions">
      <button
        class="session-tutor-tool"
        type="button"
        :disabled="pending || !messages.length"
        :aria-label="t('tutor.clearHistory')"
        :title="t('tutor.clearHistory')"
        @click="onClearChat"
      >
        <TrashIcon class="icon-sm" aria-hidden="true" />
        <span class="session-tutor-tool-label">{{ t('tutor.clearHistory') }}</span>
      </button>
      <button
        class="session-tutor-tool session-tutor-tool-hint"
        type="button"
        :disabled="pending"
        :aria-label="t('tutor.showHints')"
        :title="t('tutor.showHints')"
        @click="onShowHints"
      >
        <LightBulbIcon class="icon-sm" aria-hidden="true" />
        <span class="session-tutor-tool-label">{{ t('tutor.showHints') }}</span>
      </button>
    </div>

    <div class="session-tutor-panel">
      <div v-if="hintsVisible && hints.length" class="session-tutor-hints">
        <p class="session-tutor-label">{{ t('tutor.hintsTitle') }}</p>
        <ul>
          <li v-for="hint in hints" :key="hint">{{ hint }}</li>
        </ul>
      </div>

      <div class="session-tutor-chat">
        <div ref="messagesEl" class="session-tutor-messages">
          <div
            v-for="(message, index) in messages"
            :key="index"
            class="session-tutor-bubble"
            :data-role="message.role"
            :data-waiting="message.role === 'assistant' && !message.content && pending ? '' : undefined"
          >
            <span class="session-tutor-bubble-label">
              {{ message.role === 'user' ? t('tutor.you') : t('tutor.tutor') }}
            </span>
            <p
              v-if="message.role === 'user'"
              class="session-tutor-bubble-text"
            >{{ message.content || '…' }}</p>
            
            <div
              v-else-if="message.content"
              class="session-tutor-md"
              v-html="bubbleHtml(message.content)"
            />
            
            <div
              v-else-if="pending"
              class="session-tutor-wait"
              role="status"
              :aria-label="t('tutor.thinking')"
            >
              <span class="session-tutor-wait-bars" aria-hidden="true">
                <i /><i /><i /><i />
              </span>
              <span class="session-tutor-wait-label">{{ t('tutor.thinking') }}</span>
            </div>
            <p v-else class="session-tutor-bubble-text">…</p>
          </div>
        </div>
        <form class="session-tutor-form" @submit.prevent="onSend">
          <input
            v-model="draft"
            class="field session-tutor-input"
            :placeholder="t('tutor.messagePlaceholder')"
            :disabled="pending"
          >
          <button
            class="btn-primary session-tutor-send"
            type="submit"
            :disabled="pending || !draft.trim()"
            :aria-label="t('tutor.send')"
          >
            <PaperAirplaneIcon class="icon-sm" />
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
