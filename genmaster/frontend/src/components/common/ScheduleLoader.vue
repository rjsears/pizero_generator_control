<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/ScheduleLoader.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 16th, 2026

  Animated clock-style loader for schedule views
  with rotating messages and time-based animations.

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="flex flex-col items-center justify-center py-12">
    <!-- Clock animation container -->
    <div class="relative w-36 h-36">
      <!-- Outer ring -->
      <div class="absolute inset-0 rounded-full border-4 border-amber-500/30"></div>

      <!-- Clock face -->
      <div class="absolute inset-2 rounded-full bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/20 dark:to-amber-800/20 shadow-inner">
        <!-- Hour markers -->
        <div v-for="i in 12" :key="i" class="absolute inset-0">
          <div
            class="absolute top-2 left-1/2 w-1 h-2 bg-amber-600/50 rounded-full -translate-x-1/2"
            :style="{ transform: `rotate(${i * 30}deg) translateX(-50%)`, transformOrigin: 'center 62px' }"
          ></div>
        </div>

        <!-- Clock hands -->
        <div class="absolute inset-0 flex items-center justify-center">
          <!-- Hour hand -->
          <div class="absolute w-1 h-8 bg-amber-700 rounded-full origin-bottom animate-hour-hand" style="bottom: 50%"></div>
          <!-- Minute hand -->
          <div class="absolute w-0.5 h-10 bg-amber-600 rounded-full origin-bottom animate-minute-hand" style="bottom: 50%"></div>
          <!-- Second hand -->
          <div class="absolute w-0.5 h-12 bg-red-500 rounded-full origin-bottom animate-second-hand" style="bottom: 50%"></div>
          <!-- Center dot -->
          <div class="absolute w-3 h-3 bg-amber-600 rounded-full shadow-lg"></div>
        </div>
      </div>

      <!-- Orbiting schedule icons -->
      <div class="absolute inset-0 animate-orbit-slow">
        <div class="absolute -top-2 left-1/2 -translate-x-1/2">
          <div class="w-6 h-6 bg-amber-500 rounded-md flex items-center justify-center shadow-lg">
            <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Rotating message -->
    <p class="mt-8 text-lg text-gray-600 dark:text-gray-300 font-medium transition-opacity duration-300">
      {{ currentMessage }}
    </p>

    <!-- Animated dots -->
    <div class="flex space-x-1 mt-2">
      <div class="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style="animation-delay: 0s"></div>
      <div class="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
      <div class="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
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
  'Loading scheduled runs...',
  'Checking upcoming events...',
  'Reading schedule configuration...',
  'Calculating next run times...',
  'Parsing cron expressions...',
  'Syncing with calendar...',
  'Loading time slots...',
  'Almost ready...'
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
@keyframes hour-hand {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes minute-hand {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes second-hand {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes orbit-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-hour-hand {
  animation: hour-hand 12s linear infinite;
}

.animate-minute-hand {
  animation: minute-hand 4s linear infinite;
}

.animate-second-hand {
  animation: second-hand 2s linear infinite;
}

.animate-orbit-slow {
  animation: orbit-slow 8s linear infinite;
}
</style>
