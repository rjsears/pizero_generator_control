<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/Toggle.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="flex items-center">
    <button
      type="button"
      role="switch"
      :aria-checked="modelValue"
      :disabled="disabled"
      :class="toggleClasses"
      @click="toggle"
    >
      <span :class="dotClasses"></span>
    </button>
    <span v-if="label" class="ml-3 text-sm text-gray-700 dark:text-gray-300">
      {{ label }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value),
  },
})

const emit = defineEmits(['update:modelValue'])

const sizes = {
  sm: {
    track: 'w-8 h-4',
    dot: 'w-3 h-3',
    translate: 'translate-x-4',
  },
  md: {
    track: 'w-11 h-6',
    dot: 'w-5 h-5',
    translate: 'translate-x-5',
  },
  lg: {
    track: 'w-14 h-7',
    dot: 'w-6 h-6',
    translate: 'translate-x-7',
  },
}

const toggleClasses = computed(() => [
  'relative inline-flex flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent',
  'transition-colors duration-200 ease-in-out',
  'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900',
  'disabled:opacity-50 disabled:cursor-not-allowed',
  sizes[props.size].track,
  props.modelValue
    ? 'bg-primary-600'
    : 'bg-gray-200 dark:bg-gray-700',
])

const dotClasses = computed(() => [
  'pointer-events-none inline-block rounded-full bg-white shadow',
  'transform ring-0 transition duration-200 ease-in-out',
  sizes[props.size].dot,
  props.modelValue ? sizes[props.size].translate : 'translate-x-0',
])

function toggle() {
  if (!props.disabled) {
    emit('update:modelValue', !props.modelValue)
  }
}
</script>
