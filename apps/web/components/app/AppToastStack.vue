<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline'

const { toasts, dismiss } = useToasts()
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack" aria-live="polite" aria-relevant="additions">
      <TransitionGroup name="op-toast" tag="div" class="toast-stack-list">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="`toast-${toast.kind}`"
          role="status"
        >
          <p class="toast-message">{{ toast.message }}</p>
          <button
            class="toast-dismiss"
            type="button"
            @click="dismiss(toast.id)"
          >
            <XMarkIcon class="icon-sm" aria-hidden="true" />
            <span class="sr-only">{{ $t('dialog.close') }}</span>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
