<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/charts/MetricsLineChart.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  labels: {
    type: Array,
    default: () => [],
  },
  datasets: {
    type: Array,
    required: true,
  },
  height: {
    type: Number,
    default: 200,
  },
  yAxisMax: {
    type: Number,
    default: null,
  },
  yAxisLabel: {
    type: String,
    default: '',
  },
  showLegend: {
    type: Boolean,
    default: false,
  },
  fill: {
    type: Boolean,
    default: true,
  },
  formatTooltip: {
    type: Function,
    default: null,
  },
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(ds => ({
    ...ds,
    tension: 0.4,
    pointRadius: 0,
    pointHoverRadius: 4,
    fill: props.fill,
    borderWidth: 2,
  })),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      display: props.showLegend,
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 15,
      },
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      padding: 12,
      titleFont: {
        size: 13,
      },
      bodyFont: {
        size: 12,
      },
      callbacks: props.formatTooltip ? {
        label: props.formatTooltip,
      } : undefined,
    },
  },
  scales: {
    x: {
      display: true,
      grid: {
        display: false,
      },
      ticks: {
        maxTicksLimit: 6,
        font: {
          size: 10,
        },
      },
    },
    y: {
      display: true,
      max: props.yAxisMax,
      beginAtZero: true,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)',
      },
      ticks: {
        font: {
          size: 10,
        },
        callback: function(value) {
          if (props.yAxisLabel) {
            return value + props.yAxisLabel
          }
          return value
        },
      },
    },
  },
}))
</script>

<template>
  <div :style="{ height: `${height}px` }">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
