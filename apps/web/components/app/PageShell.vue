<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    meta?: string
    fill?: boolean
    preserveTitleCase?: boolean
    preserveMetaCase?: boolean
  }>(),
  {
    fill: true,
    meta: undefined,
    preserveTitleCase: false,
    preserveMetaCase: false,
  },
)
</script>

<template>
  <div class="board-page" :class="{ 'board-page-fill': fill }">
    <div class="board-shell">
      <header class="board-toolbar">
        <div class="board-toolbar-info">
          <h1 class="page-title" :class="{ 'case-sensitive': preserveTitleCase }">{{ title }}</h1>
          <p v-if="meta" class="page-meta" :class="{ 'case-sensitive': preserveMetaCase }">{{ meta }}</p>
        </div>
        <div v-if="$slots.actions" class="board-toolbar-actions">
          <slot name="actions" />
        </div>
      </header>
      <div class="board-body" :class="{ 'board-body-fill': fill }">
        <slot />
      </div>
    </div>
  </div>
</template>
