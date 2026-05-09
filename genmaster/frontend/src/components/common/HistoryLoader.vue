<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/HistoryLoader.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 16th, 2026

  Animated timeline-style loader for history views
  with rotating messages and data visualization effects.

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="flex flex-col items-center justify-center py-12">
    <!-- Timeline animation container -->
    <div class="relative w-48 h-32">
      <!-- Horizontal timeline line -->
      <div class="absolute top-1/2 left-0 right-0 h-1 bg-gradient-to-r from-purple-300 via-purple-500 to-purple-300 dark:from-purple-700 dark:via-purple-500 dark:to-purple-700 rounded-full transform -translate-y-1/2"></div>

      <!-- Timeline nodes -->
      <div
        v-for="i in 5"
        :key="i"
        class="absolute top-1/2 transform -translate-y-1/2"
        :style="{ left: `${(i - 1) * 25}%` }"
      >
        <div
          class="w-4 h-4 rounded-full animate-timeline-pulse"
          :class="[
            i === 3 ? 'bg-purple-500 scale-125' : 'bg-purple-400',
            'shadow-lg shadow-purple-500/30'
          ]"
          :style="{ animationDelay: `${(i - 1) * 0.2}s` }"
        ></div>
      </div>

      <!-- Data cards floating -->
      <div class="absolute -top-2 left-4 animate-float-1">
        <div class="w-10 h-8 bg-gradient-to-br from-purple-500 to-purple-600 rounded-md shadow-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
      </div>

      <div class="absolute -bottom-2 right-8 animate-float-2">
        <div class="w-10 h-8 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-md shadow-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>

      <div class="absolute top-0 right-4 animate-float-3">
        <div class="w-10 h-8 bg-gradient-to-br from-violet-500 to-violet-600 rounded-md shadow-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
      </div>

      <!-- Scanning line -->
      <div class="absolute top-0 bottom-0 w-0.5 bg-gradient-to-b from-transparent via-purple-500 to-transparent animate-scan"></div>
    </div>

    <!-- Rotating message -->
    <p class="mt-8 text-lg text-gray-600 dark:text-gray-300 font-medium transition-opacity duration-300">
      {{ currentMessage }}
    </p>

    <!-- Animated dots -->
    <div class="flex space-x-1 mt-2">
      <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style="animation-delay: 0s"></div>
      <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
      <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({
  text: {
    type: String,
    default: ''
  },
  messages: {
    type: Array,
    default: () => []
  }
})

const defaultMessages = [
  'Loading run history...',
  'Gathering statistics...',
  'Calculating run times...',
  'Parsing event logs...',
  'Analyzing usage patterns...',
  'Building timeline...',
  'Fetching historical data...',
  'Crunching the numbers...',
  'Almost there...'
]

const messageIndex = ref(0)
let messageInterval = null

const activeMessages = computed(() => {
  if (props.messages && props.messages.length > 0) {
    return props.messages
  }
  const shuffled = [...defaultMessages].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, 6)
})

const currentMessage = computed(() => {
  if (props.text) return props.text
  return activeMessages.value[messageIndex.value] || 'Loading...'
})

onMounted(() => {
  messageInterval = setInterval(() => {
    messageIndex.value = (messageIndex.value + 1) % activeMessages.value.length
  }, 2000)
})

onUnmounted(() => {
  if (messageInterval) {
    clearInterval(messageInterval)
  }
})
</script>

<style scoped>
@keyframes timeline-pulse {
  0%, 100% {
    transform: translateY(-50%) scale(1);
    opacity: 1;
  }
  50% {
    transform: translateY(-50%) scale(1.3);
    opacity: 0.7;
  }
}

@keyframes float-1 {
  0%, 100% {
    transform: translateY(0) rotate(-5deg);
  }
  50% {
    transform: translateY(-8px) rotate(5deg);
  }
}

@keyframes float-2 {
  0%, 100% {
    transform: translateY(0) rotate(5deg);
  }
  50% {
    transform: translateY(-10px) rotate(-5deg);
  }
}

@keyframes float-3 {
  0%, 100% {
    transform: translateY(0) rotate(3deg);
  }
  50% {
    transform: translateY(-6px) rotate(-3deg);
  }
}

@keyframes scan {
  0% {
    left: 0;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    left: 100%;
    opacity: 0;
  }
}

.animate-timeline-pulse {
  animation: timeline-pulse 1.5s ease-in-out infinite;
}

.animate-float-1 {
  animation: float-1 3s ease-in-out infinite;
}

.animate-float-2 {
  animation: float-2 3.5s ease-in-out infinite 0.5s;
}

.animate-float-3 {
  animation: float-3 2.5s ease-in-out infinite 0.3s;
}

.animate-scan {
  animation: scan 3s ease-in-out infinite;
}
</style>
