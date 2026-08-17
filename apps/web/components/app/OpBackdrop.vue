<template>
  <div class="op-backdrop" aria-hidden="true">
    <div class="op-backdrop-wash" />
    <div class="op-backdrop-grid" />

    <div class="op-backdrop-field">
      <span
        v-for="ring in rings"
        :key="`r-${ring.id}`"
        class="op-diamond"
        :class="[ring.size, ring.fill ? 'is-fill' : '', ring.upright ? 'is-upright' : '']"
        :style="ring.style"
      />
      <span
        v-for="shard in shards"
        :key="`s-${shard.id}`"
        class="op-shard"
        :class="{ 'is-signal': shard.signal }"
        :style="shard.style"
      />
    </div>

    <div class="op-orbit op-orbit-a" />
    <div class="op-orbit op-orbit-b" />
  </div>
</template>

<script setup lang="ts">
const rings = [
  { id: 1, size: 'op-diamond-lg', fill: false, upright: false, style: { top: '3%', left: '5%', animationDelay: '0s', animationDuration: '14s' } },
  { id: 2, size: 'op-diamond-md', fill: true, upright: false, style: { top: '14%', right: '8%', animationDelay: '-2s', animationDuration: '11s' } },
  { id: 3, size: 'op-diamond-sm', fill: false, upright: true, style: { top: '36%', left: '44%', animationDelay: '-4s', animationDuration: '9s' } },
  { id: 4, size: 'op-diamond-md', fill: false, upright: false, style: { bottom: '14%', right: '12%', animationDelay: '-1s', animationDuration: '13s' } },
  { id: 5, size: 'op-diamond-sm', fill: true, upright: false, style: { bottom: '26%', left: '16%', animationDelay: '-6s', animationDuration: '10s' } },
  { id: 6, size: 'op-diamond-lg', fill: false, upright: false, style: { top: '50%', left: '-10%', animationDelay: '-8s', animationDuration: '16s' } },
  { id: 7, size: 'op-diamond-md', fill: true, upright: true, style: { top: '62%', right: '22%', animationDelay: '-3s', animationDuration: '12s' } },
  { id: 8, size: 'op-diamond-sm', fill: false, upright: false, style: { top: '78%', left: '55%', animationDelay: '-5s', animationDuration: '8s' } },
]

const shards = Array.from({ length: 16 }, (_, index) => ({
  id: index,
  signal: index % 7 === 0,
  style: {
    top: `${4 + ((index * 17) % 88)}%`,
    left: `${2 + ((index * 29) % 94)}%`,
    animationDelay: `${-index * 0.35}s`,
    animationDuration: `${3.2 + (index % 6) * 0.55}s`,
  },
}))
</script>
