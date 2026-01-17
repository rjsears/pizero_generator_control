<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/ContainerStackLoader.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 16th, 2026

  Animated radar/sonar-style loader for container views
  with rotating messages and scanning effects.

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="flex flex-col items-center justify-center py-12">
    <!-- Radar animation container -->
    <div class="relative w-40 h-40">
      <!-- Pulsing rings -->
      <div
        v-for="i in 4"
        :key="i"
        class="absolute inset-0 rounded-full border-2 border-blue-500/30 animate-pulse-ring"
        :style="{ animationDelay: `${(i - 1) * 0.5}s` }"
      ></div>

      <!-- Center container icon -->
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center animate-pulse-center shadow-lg shadow-blue-500/30">
          <!-- Docker-style container icon -->
          <svg class="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
      </div>

      <!-- Rotating scan beam -->
      <div class="absolute inset-0 animate-radar-sweep origin-center">
        <div class="absolute top-1/2 left-1/2 w-1/2 h-0.5 bg-gradient-to-r from-blue-500 to-transparent origin-left"></div>
      </div>

      <!-- Detection dots -->
      <div class="absolute top-4 right-8 w-3 h-3 bg-green-500 rounded-full animate-blink-dot shadow-lg shadow-green-500/50"></div>
      <div class="absolute bottom-8 left-4 w-3 h-3 bg-green-500 rounded-full animate-blink-dot shadow-lg shadow-green-500/50" style="animation-delay: 0.5s"></div>
      <div class="absolute top-1/2 right-2 w-3 h-3 bg-green-500 rounded-full animate-blink-dot shadow-lg shadow-green-500/50" style="animation-delay: 1s"></div>
    </div>

    <!-- Rotating message -->
    <p class="mt-8 text-lg text-gray-600 dark:text-gray-300 font-medium transition-opacity duration-300">
      {{ currentMessage }}
    </p>

    <!-- Animated dots -->
    <div class="flex space-x-1 mt-2">
      <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0s"></div>
      <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
      <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
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
  'Scanning container landscape...',
  'Checking container health...',
  'Gathering resource metrics...',
  'Inspecting running services...',
  'Counting all the little boxes...',
  'Reading container logs...',
  'Checking network connections...',
  'Analyzing memory usage...',
  'Waking up the containers...',
  'Probing Docker engine...',
  'Mapping container topology...',
  'Almost there...'
]

const messageIndex = ref(0)
let messageInterval = null

const activeMessages = computed(() => {
  if (props.messages && props.messages.length > 0) {
    return props.messages
  }
  // Shuffle and pick 8 messages
  const shuffled = [...defaultMessages].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, 8)
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
@keyframes pulse-ring {
  0% {
    transform: scale(0.8);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

@keyframes pulse-center {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@keyframes radar-sweep {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes blink-dot {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.animate-pulse-ring {
  animation: pulse-ring 3s ease-out infinite;
}

.animate-pulse-center {
  animation: pulse-center 2s ease-in-out infinite;
}

.animate-radar-sweep {
  animation: radar-sweep 4s linear infinite;
}

.animate-blink-dot {
  animation: blink-dot 1.5s ease-in-out infinite;
}
</style>
