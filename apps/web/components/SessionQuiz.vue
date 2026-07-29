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
  const isCorrect =
    (reveal.expectedIndex !== null && reveal.expectedIndex === index)
    || (reveal.passed && selected.value === index)
  const isWrong =
    !reveal.passed
    && selected.value === index
    && (reveal.expectedIndex === null || reveal.expectedIndex !== index)
  return {
    'quiz-option-correct': isCorrect,
    'quiz-option-wrong': isWrong,
  }
}
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
          :disabled="props.disabled || Boolean(props.reveal)"
        >
        <span class="quiz-option-letter">{{ letters[index] || index + 1 }}</span>
        <span class="quiz-option-text">{{ choice }}</span>
      </label>
    </div>
  </fieldset>
</template>
