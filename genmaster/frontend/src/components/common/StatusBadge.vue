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

<template>
  <span :class="badgeClasses">
    <span v-if="pulse" class="relative flex h-2 w-2 mr-1.5">
      <span
        class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
        :class="pulseColorClass"
      ></span>
      <span
        class="relative inline-flex rounded-full h-2 w-2"
        :class="dotColorClass"
      ></span>
    </span>
    <slot>{{ text }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'gray',
    validator: (value) =>
      ['success', 'warning', 'danger', 'info', 'gray', 'green', 'amber', 'red', 'blue'].includes(value),
  },
  text: {
    type: String,
    default: '',
  },
  pulse: {
    type: Boolean,
    default: false,
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value),
  },
})

const statusColors = {
  success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  green: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  red: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
}

const pulseColors = {
  success: 'bg-green-400',
  green: 'bg-green-400',
  warning: 'bg-amber-400',
  amber: 'bg-amber-400',
  danger: 'bg-red-400',
  red: 'bg-red-400',
  info: 'bg-blue-400',
  blue: 'bg-blue-400',
  gray: 'bg-gray-400',
}

const dotColors = {
  success: 'bg-green-500',
  green: 'bg-green-500',
  warning: 'bg-amber-500',
  amber: 'bg-amber-500',
  danger: 'bg-red-500',
  red: 'bg-red-500',
  info: 'bg-blue-500',
  blue: 'bg-blue-500',
  gray: 'bg-gray-500',
}

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
}

const badgeClasses = computed(() => [
  'inline-flex items-center rounded-full font-medium',
  statusColors[props.status] || statusColors.gray,
  sizeClasses[props.size],
])

const pulseColorClass = computed(() => pulseColors[props.status] || pulseColors.gray)
const dotColorClass = computed(() => dotColors[props.status] || dotColors.gray)
</script>
