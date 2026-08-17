<script setup lang="ts">
const { t } = useI18n()
const { state, settle } = useConfirm()

const confirmLabel = computed(
  () => state.confirmLabel || t('dialog.confirm'),
)
const cancelLabel = computed(
  () => state.cancelLabel || t('dialog.cancel'),
)

function onKeydown(event: KeyboardEvent) {
  if (!state.open) {
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    settle(false)
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="op-modal">
      <div
        v-if="state.open"
        class="op-dialog-backdrop"
        role="presentation"
        @click.self="settle(false)"
      >
        <div
          class="op-dialog"
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="'op-dialog-title'"
          :aria-describedby="state.message ? 'op-dialog-message' : undefined"
        >
          <header class="op-dialog-head">
            <h2 id="op-dialog-title" class="op-dialog-title">
              {{ state.title }}
            </h2>
          </header>
          <p
            v-if="state.message"
            id="op-dialog-message"
            class="op-dialog-message"
          >
            {{ state.message }}
          </p>
          <footer class="op-dialog-actions">
            <button
              type="button"
              class="btn-ghost op-dialog-cancel"
              @click="settle(false)"
            >
              {{ cancelLabel }}
            </button>
            <button
              type="button"
              class="btn-primary op-dialog-confirm"
              :class="{ 'is-danger': state.danger }"
              @click="settle(true)"
            >
              {{ confirmLabel }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
