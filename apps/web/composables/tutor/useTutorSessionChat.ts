export type TutorChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

const MAX_STORED_TURNS = 40

export function useTutorSessionChat(sessionId: MaybeRefOrGetter<string>) {
  const bags = useState<Record<string, TutorChatMessage[]>>('tutor-session-chats', () => ({}))
  const draft = ref('')

  const messages = computed(() => bags.value[toValue(sessionId)] ?? [])

  function replace(next: TutorChatMessage[]) {
    const id = toValue(sessionId)
    bags.value = {
      ...bags.value,
      [id]: next.slice(-MAX_STORED_TURNS),
    }
  }

  function clear() {
    replace([])
    draft.value = ''
  }

  function append(message: TutorChatMessage) {
    replace([...messages.value, message])
  }

  function updateLastAssistant(content: string) {
    const current = messages.value
    if (!current.length) {
      return
    }
    const last = current[current.length - 1]
    if (last?.role !== 'assistant') {
      return
    }
    replace([...current.slice(0, -1), { ...last, content }])
  }

  function popLast() {
    replace(messages.value.slice(0, -1))
  }

  function historyBeforeSend() {
    return messages.value.filter((item) => item.content.trim()).slice(-20)
  }

  return {
    messages,
    draft,
    clear,
    append,
    updateLastAssistant,
    popLast,
    historyBeforeSend,
  }
}
