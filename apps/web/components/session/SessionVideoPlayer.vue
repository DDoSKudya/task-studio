<script setup lang="ts">
import {
  ArrowsPointingOutIcon,
  PauseIcon,
  PlayIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
} from '@heroicons/vue/24/solid'

import { youtubeEmbedSrc } from '~/utils/study'
import {
  formatMediaTime,
  mediaProgressPercent,
  resolvePlaybackSrc,
  seekRatioFromClientX,
} from '~/utils/media'

const props = defineProps<{
  src: string
  title: string
  poster?: string
}>()

const { t } = useI18n()

const RATES = [0.75, 1, 1.25, 1.5, 2] as const

const youtubeSrc = computed(() => youtubeEmbedSrc(props.src))
const videoEl = ref<HTMLVideoElement | null>(null)
const rootEl = ref<HTMLElement | null>(null)
const playing = ref(false)
const muted = ref(false)
const volume = ref(1)
const rate = ref(1)
const duration = ref(0)
const current = ref(0)
const buffered = ref(0)
const hovering = ref(false)
const failed = ref(false)
const scrubbing = ref(false)
const showRates = ref(false)
const hideChromeTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const chromePinned = ref(true)

const playbackSrc = computed(() =>
  resolvePlaybackSrc(props.src, import.meta.client ? window.location.href : null),
)

const progress = computed(() => mediaProgressPercent(current.value, duration.value))
const bufferProgress = computed(() => mediaProgressPercent(buffered.value, duration.value))
const showChrome = computed(
  () => chromePinned.value || !playing.value || hovering.value || scrubbing.value || showRates.value,
)

function onLoadedMetadata() {
  duration.value = videoEl.value?.duration || 0
  const video = videoEl.value
  if (!video) {
    return
  }
  video.muted = false
  video.volume = volume.value || 1
  muted.value = false
}

function formatTime(seconds: number): string {
  return formatMediaTime(seconds)
}

function syncBuffer() {
  const video = videoEl.value
  if (!video || !video.buffered.length) {
    buffered.value = 0
    return
  }
  buffered.value = video.buffered.end(video.buffered.length - 1)
}

function scheduleChromeHide() {
  if (hideChromeTimer.value) {
    clearTimeout(hideChromeTimer.value)
  }
  chromePinned.value = true
  hideChromeTimer.value = setTimeout(() => {
    if (playing.value && !hovering.value && !scrubbing.value && !showRates.value) {
      chromePinned.value = false
    }
  }, 1600)
}

async function togglePlay() {
  const video = videoEl.value
  if (!video || failed.value) {
    return
  }
  try {
    if (video.paused) {
      await video.play()
      scheduleChromeHide()
    } else {
      video.pause()
      chromePinned.value = true
    }
  } catch {
    failed.value = true
  }
}

function toggleMute() {
  const video = videoEl.value
  if (!video) {
    return
  }
  video.muted = !video.muted
  muted.value = video.muted
  if (!video.muted && video.volume === 0) {
    video.volume = 0.6
    volume.value = 0.6
  }
}

function onVolumeInput(event: Event) {
  const video = videoEl.value
  const target = event.target as HTMLInputElement
  if (!video) {
    return
  }
  const next = Number(target.value)
  video.volume = next
  volume.value = next
  video.muted = next === 0
  muted.value = video.muted
}

function setRate(next: number) {
  const video = videoEl.value
  rate.value = next
  if (video) {
    video.playbackRate = next
  }
  showRates.value = false
  scheduleChromeHide()
}

async function toggleFullscreen() {
  const root = rootEl.value
  if (!root) {
    return
  }
  if (document.fullscreenElement) {
    await document.exitFullscreen()
    return
  }
  await root.requestFullscreen().catch(() => undefined)
}

function onTimeUpdate() {
  const video = videoEl.value
  if (!video || scrubbing.value) {
    return
  }
  current.value = video.currentTime
  syncBuffer()
}

function seekFromClientX(clientX: number, target: HTMLElement) {
  const video = videoEl.value
  if (!video || !duration.value) {
    return
  }
  const rect = target.getBoundingClientRect()
  const ratio = seekRatioFromClientX(clientX, rect.left, rect.width)
  video.currentTime = ratio * duration.value
  current.value = video.currentTime
}

function onScrubPointerDown(event: PointerEvent) {
  const target = event.currentTarget as HTMLElement
  scrubbing.value = true
  target.setPointerCapture(event.pointerId)
  seekFromClientX(event.clientX, target)
}

function onScrubPointerMove(event: PointerEvent) {
  if (!scrubbing.value) {
    return
  }
  seekFromClientX(event.clientX, event.currentTarget as HTMLElement)
}

function onScrubPointerUp(event: PointerEvent) {
  const target = event.currentTarget as HTMLElement
  if (scrubbing.value) {
    seekFromClientX(event.clientX, target)
  }
  scrubbing.value = false
  scheduleChromeHide()
}

function onKeydown(event: KeyboardEvent) {
  const root = rootEl.value
  if (!root || failed.value || youtubeSrc.value) {
    return
  }
  if (!root.contains(document.activeElement) && document.activeElement !== root) {
    return
  }
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
    return
  }
  if (event.code === 'Space' || event.key === 'k' || event.key === 'K') {
    event.preventDefault()
    void togglePlay()
  } else if (event.key === 'm' || event.key === 'M') {
    toggleMute()
  } else if (event.key === 'f' || event.key === 'F') {
    void toggleFullscreen()
  } else if (event.key === 'ArrowRight') {
    const video = videoEl.value
    if (video) {
      video.currentTime = Math.min(duration.value, video.currentTime + 5)
    }
  } else if (event.key === 'ArrowLeft') {
    const video = videoEl.value
    if (video) {
      video.currentTime = Math.max(0, video.currentTime - 5)
    }
  }
}

function onVideoError() {
  failed.value = true
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  scheduleChromeHide()
  nextTick(() => {
    const video = videoEl.value
    if (!video) {
      return
    }
    video.defaultMuted = false
    video.muted = false
    video.volume = 1
    muted.value = false
    volume.value = 1
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (hideChromeTimer.value) {
    clearTimeout(hideChromeTimer.value)
  }
})

watch(
  () => props.src,
  () => {
    failed.value = false
    playing.value = false
    current.value = 0
    duration.value = 0
    buffered.value = 0
    showRates.value = false
    chromePinned.value = true
  },
)
</script>

<template>
  <div
    v-if="youtubeSrc"
    class="session-player session-player-embed"
  >
    <iframe
      :src="youtubeSrc"
      :title="props.title"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      allowfullscreen
      loading="lazy"
      referrerpolicy="strict-origin-when-cross-origin"
    />
  </div>

  <div
    v-else
    ref="rootEl"
    class="session-player"
    tabindex="0"
    :class="{
      'is-playing': playing,
      'is-failed': failed,
      'is-chrome': showChrome,
    }"
    @mouseenter="hovering = true; chromePinned = true"
    @mouseleave="hovering = false; scheduleChromeHide()"
    @mousemove="scheduleChromeHide()"
    @focusin="chromePinned = true"
  >
    <span class="session-player-frame" aria-hidden="true">
      <span class="session-player-corner session-player-corner-tl" />
      <span class="session-player-corner session-player-corner-tr" />
      <span class="session-player-corner session-player-corner-bl" />
      <span class="session-player-corner session-player-corner-br" />
    </span>

    <video
      ref="videoEl"
      class="session-player-video"
      :src="playbackSrc"
      :poster="props.poster || undefined"
      :title="props.title"
      playsinline
      preload="metadata"
      :muted="false"
      controlslist="nodownload noremoteplayback"
      @click="togglePlay"
      @play="playing = true"
      @pause="playing = false"
      @loadedmetadata="onLoadedMetadata"
      @timeupdate="onTimeUpdate"
      @progress="syncBuffer"
      @error="onVideoError"
      @volumechange="muted = !!videoEl?.muted; volume = videoEl?.volume ?? volume"
    />

    <button
      v-if="!failed && !playing"
      class="session-player-bigplay"
      type="button"
      :aria-label="t('session.videoPlay')"
      @click.stop="togglePlay"
    >
      <PlayIcon class="session-player-bigplay-icon" />
    </button>

    <div v-if="failed" class="session-player-error">
      <p>{{ t('session.videoUnavailable') }}</p>
      <a class="btn-secondary" :href="playbackSrc" target="_blank" rel="noopener noreferrer">
        {{ t('session.videoOpenExternal') }}
      </a>
    </div>

    <div class="session-player-chrome" :aria-hidden="!showChrome">
      <div
        class="session-player-scrub"
        role="slider"
        :aria-valuemin="0"
        :aria-valuemax="Math.floor(duration)"
        :aria-valuenow="Math.floor(current)"
        tabindex="0"
        @pointerdown="onScrubPointerDown"
        @pointermove="onScrubPointerMove"
        @pointerup="onScrubPointerUp"
        @pointercancel="scrubbing = false"
      >
        <div class="session-player-buffer" :style="{ width: `${bufferProgress}%` }" />
        <div class="session-player-progress" :style="{ width: `${progress}%` }">
          <span class="session-player-knob" />
        </div>
      </div>

      <div class="session-player-dock">
        <button class="session-player-btn" type="button" :aria-label="t('session.videoPlay')" @click="togglePlay">
          <PauseIcon v-if="playing" class="icon-sm" />
          <PlayIcon v-else class="icon-sm" />
        </button>

        <span class="session-player-time">
          <span>{{ formatTime(current) }}</span>
          <span class="session-player-time-sep">/</span>
          <span>{{ formatTime(duration) }}</span>
        </span>

        <span class="session-player-spacer" />

        <div class="session-player-volume">
          <button class="session-player-btn" type="button" @click="toggleMute">
            <SpeakerXMarkIcon v-if="muted || volume === 0" class="icon-sm" />
            <SpeakerWaveIcon v-else class="icon-sm" />
          </button>
          <input
            class="session-player-volume-range"
            type="range"
            min="0"
            max="1"
            step="0.05"
            :value="muted ? 0 : volume"
            @input="onVolumeInput"
          >
        </div>

        <div class="session-player-rate">
          <button class="session-player-rate-btn" type="button" @click="showRates = !showRates">
            {{ rate === 1 ? '1×' : `${rate}×` }}
          </button>
          <Transition name="op-panel">
            <div v-if="showRates" class="session-player-rate-menu">
              <button
                v-for="option in RATES"
                :key="option"
                type="button"
                class="session-player-rate-option"
                :class="{ active: option === rate }"
                @click="setRate(option)"
              >
                {{ option === 1 ? '1×' : `${option}×` }}
              </button>
            </div>
          </Transition>
        </div>

        <button class="session-player-btn" type="button" @click="toggleFullscreen">
          <ArrowsPointingOutIcon class="icon-sm" />
        </button>
      </div>
    </div>
  </div>
</template>
