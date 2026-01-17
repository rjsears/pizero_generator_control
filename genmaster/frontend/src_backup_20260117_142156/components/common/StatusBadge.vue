<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/StatusBadge.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
  size: {
    type: String,
    default: 'md', // 'sm', 'md', 'lg'
  },
  pulse: {
    type: Boolean,
    default: false,
  },
})

const statusConfig = {
  // Container statuses
  running: { label: 'Running', color: 'emerald' },
  stopped: { label: 'Stopped', color: 'gray' },
  restarting: { label: 'Restarting', color: 'amber' },
  unhealthy: { label: 'Unhealthy', color: 'red' },
  healthy: { label: 'Healthy', color: 'emerald' },
  exited: { label: 'Exited', color: 'gray' },
  created: { label: 'Created', color: 'blue' },
  paused: { label: 'Paused', color: 'amber' },
  dead: { label: 'Dead', color: 'red' },

  // Generator statuses
  starting: { label: 'Starting', color: 'amber' },
  stopping: { label: 'Stopping', color: 'amber' },
  cooldown: { label: 'Cooldown', color: 'blue' },
  idle: { label: 'Idle', color: 'gray' },
  warmup: { label: 'Warmup', color: 'amber' },

  // Schedule statuses
  scheduled: { label: 'Scheduled', color: 'blue' },
  completed: { label: 'Completed', color: 'emerald' },
  cancelled: { label: 'Cancelled', color: 'gray' },
  missed: { label: 'Missed', color: 'red' },

  // Generic
  success: { label: 'Success', color: 'emerald' },
  failed: { label: 'Failed', color: 'red' },
  pending: { label: 'Pending', color: 'amber' },
  active: { label: 'Active', color: 'emerald' },
  inactive: { label: 'Inactive', color: 'gray' },
  enabled: { label: 'Enabled', color: 'emerald' },
  disabled: { label: 'Disabled', color: 'gray' },
  error: { label: 'Error', color: 'red' },
  warning: { label: 'Warning', color: 'amber' },
  info: { label: 'Info', color: 'blue' },
  online: { label: 'Online', color: 'emerald' },
  offline: { label: 'Offline', color: 'red' },
  connected: { label: 'Connected', color: 'emerald' },
  disconnected: { label: 'Disconnected', color: 'red' },
}

const config = computed(() => {
  const status = props.status.toLowerCase()
  return statusConfig[status] || { label: props.status, color: 'gray' }
})

const colorClasses = computed(() => {
  const colors = {
    emerald: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-400',
    red: 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-400',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-400',
    blue: 'bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-400',
    gray: 'bg-gray-100 text-gray-800 dark:bg-gray-500/20 dark:text-gray-400',
  }
  return colors[config.value.color] || colors.gray
})

const sizeClasses = computed(() => {
  const sizes = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-1 text-xs',
    lg: 'px-2.5 py-1 text-sm',
  }
  return sizes[props.size] || sizes.md
})

const pulseColors = {
  emerald: 'bg-emerald-400',
  amber: 'bg-amber-400',
  red: 'bg-red-400',
  blue: 'bg-blue-400',
  gray: 'bg-gray-400',
}

const pulseColorClass = computed(() => pulseColors[config.value.color] || pulseColors.gray)
</script>

<template>
  <span
    :class="[
      'inline-flex items-center font-medium rounded-full',
      colorClasses,
      sizeClasses
    ]"
  >
    <span v-if="pulse" class="relative flex h-1.5 w-1.5 mr-1.5">
      <span
        class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
        :class="pulseColorClass"
      ></span>
      <span
        class="relative inline-flex rounded-full h-1.5 w-1.5"
        :class="pulseColorClass"
      ></span>
    </span>
    <span v-else class="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-75" />
    {{ config.label }}
  </span>
</template>
