<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/LoadingSpinner.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div :class="containerClasses">
    <svg
      :class="spinnerClasses"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      ></circle>
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      ></path>
    </svg>
    <span v-if="text" :class="textClasses">{{ text }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'xl'].includes(value),
  },
  text: {
    type: String,
    default: '',
  },
  fullscreen: {
    type: Boolean,
    default: false,
  },
  overlay: {
    type: Boolean,
    default: false,
  },
})

const sizeMap = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
}

const textSizeMap = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
  xl: 'text-lg',
}

const containerClasses = computed(() => {
  const classes = ['flex items-center justify-center']

  if (props.fullscreen) {
    classes.push('fixed inset-0 z-50')
  }

  if (props.overlay) {
    classes.push('bg-white/75 dark:bg-gray-900/75')
  }

  if (props.text) {
    classes.push('flex-col gap-2')
  }

  return classes
})

const spinnerClasses = computed(() => [
  'animate-spin',
  sizeMap[props.size],
  'text-primary-600 dark:text-primary-400',
])

const textClasses = computed(() => [
  textSizeMap[props.size],
  'text-gray-600 dark:text-gray-400',
])
</script>
