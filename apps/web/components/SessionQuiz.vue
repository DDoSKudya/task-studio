<script setup lang="ts">
const props = defineProps<{
  question: string
  choices: string[]
  disabled?: boolean

  reveal?: {
    passed: boolean
    expectedIndex: number | null
  } | null
}>()

const selected = defineModel<number | null>({ default: null })
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

function optionClass(index: number) {
  const reveal = props.reveal
  if (!reveal) {
    return { 'quiz-option-selected': selected.value === index }
  }
  // Wrong: mark only the chosen option. Do not reveal the correct answer.
  if (!reveal.passed) {
    return {
      'quiz-option-selected': selected.value === index,
      'quiz-option-wrong': selected.value === index,
    }
  }
  // Passed: confirm the chosen answer; still do not paint other options.
  return {
    'quiz-option-correct': selected.value === index,
  }
}

const locked = computed(() => props.disabled || props.reveal?.passed === true)
</script>

<template>
  <fieldset class="quiz-panel">
    <legend v-if="props.question" class="quiz-question">{{ props.question }}</legend>
    <div class="quiz-options">
      <label
        v-for="(choice, index) in props.choices"
        :key="index"
        class="quiz-option"
        :class="optionClass(index)"
      >
        <input
          v-model="selected"
          class="quiz-option-input"
          type="radio"
          :value="index"
          :disabled="locked"
        >
        <span class="quiz-option-letter">{{ letters[index] || index + 1 }}</span>
        <span class="quiz-option-text">{{ choice }}</span>
      </label>
    </div>
  </fieldset>
</template>
