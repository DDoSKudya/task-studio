<script setup lang="ts">
defineProps<{
  iconClass?: string
}>()

const config = useRuntimeConfig()
const src = `${config.app.baseURL || '/'}favicon.svg`.replace(/([^:]\/)\/+/g, '$1')
</script>

<template>
  <img :src="src" alt="" :class="iconClass" aria-hidden="true">
</template>
