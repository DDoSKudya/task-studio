<script setup lang="ts">
const props = defineProps<{
  question: string
  choices: string[]
  disabled?: boolean
}>()

const selected = defineModel<number | null>({ default: null })
</script>

<template>
  <fieldset class="space-y-3">
    <legend class="text-sm font-medium">
      {{ props.question }}
    </legend>
    <label
      v-for="(choice, index) in props.choices"
      :key="index"
      class="flex items-center gap-2 text-sm"
    >
      <input
        v-model="selected"
        type="radio"
        :value="index"
        :disabled="props.disabled"
      >
      <span>{{ choice }}</span>
    </label>
  </fieldset>
</template>
