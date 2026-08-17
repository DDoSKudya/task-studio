<script setup lang="ts">
import { PieChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

import {
  ANALYTICS_SUCCESS,
  analyticsTooltipBase,
} from '~/utils/analytics'

use([CanvasRenderer, PieChart, TooltipComponent])

const props = defineProps<{
  passed: number
  failed: number
  passLabel: string
  failLabel: string
  emptyLabel: string
}>()

const total = computed(() => props.passed + props.failed)
const rate = computed(() => (total.value ? Math.round((props.passed / total.value) * 100) : null))

const option = computed(() => ({
  tooltip: {
    ...analyticsTooltipBase(),
    trigger: 'item',
  },
  series: [
    {
      type: 'pie',
      radius: ['62%', '82%'],
      center: ['50%', '50%'],
      silent: total.value === 0,
      label: { show: false },
      data:
        total.value === 0
          ? [{ value: 1, name: props.emptyLabel, itemStyle: { color: 'rgba(255,255,255,0.1)' } }]
          : [
              {
                value: props.passed,
                name: props.passLabel,
                itemStyle: {
                  color: ANALYTICS_SUCCESS,
                  shadowBlur: 8,
                  shadowColor: 'rgba(179, 102, 255, 0.28)',
                },
              },
              {
                value: props.failed,
                name: props.failLabel,
                itemStyle: {
                  color: 'rgba(255, 215, 0, 0.55)',
                },
              },
            ],
      emphasis: {
        scale: false,
        itemStyle: {
          shadowBlur: 18,
          shadowColor: 'rgba(179, 102, 255, 0.4)',
        },
      },
    },
  ],
}))
</script>

<template>
  <div class="ax-ring">
    <ClientOnly>
      <VChart class="ax-chart ax-chart-ring" :option="option" autoresize />
    </ClientOnly>
    <div class="ax-ring-center" aria-hidden="true">
      <span class="ax-ring-rate">{{ rate == null ? '—' : `${rate}%` }}</span>
      <span class="ax-ring-caption">{{ total ? passLabel : emptyLabel }}</span>
    </div>
  </div>
</template>
