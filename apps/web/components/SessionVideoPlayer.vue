<script setup lang="ts">
import 'vidstack/player/styles/default/theme.css'
import 'vidstack/player/styles/default/layouts/video.css'

const props = defineProps<{
  src: string
  title: string
}>()
</script>

<template>
  <ClientOnly>
    <media-player
      :title="props.title"
      :src="props.src"
      playsinline
      class="w-full overflow-hidden rounded-md border border-default"
    >
      <media-provider />
      <media-video-layout />
    </media-player>
  </ClientOnly>
</template>
