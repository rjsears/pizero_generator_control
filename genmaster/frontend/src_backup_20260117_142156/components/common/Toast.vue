<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/Toast.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div :class="toastClasses">
    <div class="flex items-start">
      <!-- Icon -->
      <div :class="iconClasses">
        <component :is="icon" class="w-5 h-5" />
      </div>

      <!-- Content -->
      <div class="ml-3 flex-1">
        <p v-if="title" class="text-sm font-medium" :class="titleClass">
          {{ title }}
        </p>
        <p class="text-sm" :class="messageClass">
          {{ message }}
        </p>
      </div>

      <!-- Close button -->
      <button
        v-if="dismissible"
        type="button"
        class="ml-4 inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
        @click="$emit('dismiss')"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['success', 'error', 'warning', 'info'].includes(value),
  },
  title: {
    type: String,
    default: '',
  },
  message: {
    type: String,
    required: true,
  },
  dismissible: {
    type: Boolean,
    default: true,
  },
})

defineEmits(['dismiss'])

const typeStyles = {
  success: {
    bg: 'bg-green-50 dark:bg-green-900/50',
    icon: 'text-green-400',
    title: 'text-green-800 dark:text-green-200',
    message: 'text-green-700 dark:text-green-300',
  },
  error: {
    bg: 'bg-red-50 dark:bg-red-900/50',
    icon: 'text-red-400',
    title: 'text-red-800 dark:text-red-200',
    message: 'text-red-700 dark:text-red-300',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-900/50',
    icon: 'text-amber-400',
    title: 'text-amber-800 dark:text-amber-200',
    message: 'text-amber-700 dark:text-amber-300',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-900/50',
    icon: 'text-blue-400',
    title: 'text-blue-800 dark:text-blue-200',
    message: 'text-blue-700 dark:text-blue-300',
  },
}

const icons = {
  success: {
    render() {
      return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M5 13l4 4L19 7',
        }),
      ])
    },
  },
  error: {
    render() {
      return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M6 18L18 6M6 6l12 12',
        }),
      ])
    },
  },
  warning: {
    render() {
      return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
        }),
      ])
    },
  },
  info: {
    render() {
      return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' }, [
        h('path', {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
        }),
      ])
    },
  },
}

const style = computed(() => typeStyles[props.type])
const icon = computed(() => icons[props.type])

const toastClasses = computed(() => [
  'rounded-lg p-4 shadow-lg border border-gray-200 dark:border-gray-700',
  style.value.bg,
])

const iconClasses = computed(() => [
  'flex-shrink-0',
  style.value.icon,
])

const titleClass = computed(() => style.value.title)
const messageClass = computed(() => style.value.message)
</script>
