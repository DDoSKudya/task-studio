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

import type { DailyProgressPoint } from '~/composables/analytics/useAnalytics'
import {
  ANALYTICS_GRID,
  ANALYTICS_LINE,
  ANALYTICS_VIOLET,
  analyticsAxisLabel,
  analyticsLegend,
  analyticsTooltipBase,
} from '~/utils/analytics'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps<{
  points: DailyProgressPoint[]
  sessionsLabel: string
  stepsLabel: string
}>()

const option = computed(() => {
  const labels = props.points.map((point) => point.day.slice(5, 10))
  return {
    color: [ANALYTICS_LINE, ANALYTICS_VIOLET],
    tooltip: {
      ...analyticsTooltipBase(),
      trigger: 'axis',
    },
    legend: {
      ...analyticsLegend(),
      data: [props.sessionsLabel, props.stepsLabel],
    },
    grid: { left: 36, right: 12, top: 36, bottom: 28 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLine: { lineStyle: { color: ANALYTICS_GRID } },
      axisTick: { show: false },
      axisLabel: analyticsAxisLabel(),
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: analyticsAxisLabel(),
      splitLine: { lineStyle: { color: ANALYTICS_GRID, type: 'dashed' } },
    },
    series: [
      {
        name: props.sessionsLabel,
        type: 'line',
        smooth: 0.25,
        symbol: 'rect',
        symbolSize: 5,
        lineStyle: { width: 1.6, color: ANALYTICS_LINE },
        itemStyle: { color: ANALYTICS_LINE },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255, 255, 255, 0.1)' },
              { offset: 1, color: 'rgba(255, 255, 255, 0)' },
            ],
          },
        },
        data: props.points.map((point) => point.sessions_started),
      },
      {
        name: props.stepsLabel,
        type: 'line',
        smooth: 0.25,
        symbol: 'rect',
        symbolSize: 5,
        lineStyle: { width: 1.6, color: ANALYTICS_VIOLET },
        itemStyle: { color: ANALYTICS_VIOLET },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(179, 102, 255, 0.14)' },
              { offset: 1, color: 'rgba(179, 102, 255, 0)' },
            ],
          },
        },
        data: props.points.map((point) => point.steps_completed),
      },
    ],
  }
})
</script>

<template>
  <div class="ax-chart-host">
    <ClientOnly>
      <VChart class="ax-chart ax-chart-line" :option="option" autoresize />
    </ClientOnly>
  </div>
</template>
