<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

import type { DailyProgressPoint } from '~/composables/useAnalytics'

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const props = defineProps<{
  points: DailyProgressPoint[]
}>()

const option = computed(() => {
  const labels = props.points.map((point) => point.day.slice(0, 10))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Sessions', 'Steps completed'] },
    grid: { left: 40, right: 16, top: 40, bottom: 32 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: 'Sessions',
        type: 'line',
        smooth: true,
        data: props.points.map((point) => point.sessions_started),
      },
      {
        name: 'Steps completed',
        type: 'line',
        smooth: true,
        data: props.points.map((point) => point.steps_completed),
      },
    ],
  }
})
</script>

<template>
  <ClientOnly>
    <VChart class="h-72 w-full" :option="option" autoresize />
  </ClientOnly>
</template>
