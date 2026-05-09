<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/GenSlaveLoader.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 16th, 2026

  Animated loader for GenSlave health checks with rotating messages
  Inspired by n8n_nginx management console loaders

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="flex flex-col items-center justify-center py-12">
    <!-- Main animation container -->
    <div class="relative w-40 h-40">
      <!-- Outer rotating dashed ring -->
      <div class="absolute inset-0 rounded-full border-4 border-dashed border-cyan-500/30 animate-spin-slow"></div>

      <!-- Middle pulsing ring -->
      <div class="absolute inset-2 rounded-full border-2 border-cyan-400/50 animate-pulse-ring"></div>

      <!-- Inner glow ring -->
      <div class="absolute inset-4 rounded-full bg-gradient-to-br from-cyan-500/20 to-blue-600/20 animate-pulse"></div>

      <!-- Center Pi icon -->
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="relative">
          <!-- Raspberry Pi icon -->
          <svg class="w-16 h-16 text-cyan-500 animate-pulse-center" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
          <!-- Status indicator dot -->
          <div class="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full animate-blink shadow-lg shadow-green-500/50"></div>
        </div>
      </div>

      <!-- Orbiting signal particles -->
      <div class="absolute inset-0 animate-orbit">
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-cyan-400 rounded-full shadow-lg shadow-cyan-400/50"></div>
      </div>
      <div class="absolute inset-0 animate-orbit-reverse">
        <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-blue-400 rounded-full shadow-lg shadow-blue-400/50"></div>
      </div>
      <div class="absolute inset-0 animate-orbit-slow">
        <div class="absolute top-1/2 right-0 -translate-y-1/2 w-2 h-2 bg-emerald-400 rounded-full shadow-lg shadow-emerald-400/50"></div>
      </div>

      <!-- WiFi signal waves -->
      <div class="absolute -right-4 top-1/2 -translate-y-1/2 space-y-1">
        <div class="w-1 h-3 bg-cyan-400/80 rounded-full animate-wave-1"></div>
        <div class="w-1 h-5 bg-cyan-400/60 rounded-full animate-wave-2 ml-1"></div>
        <div class="w-1 h-7 bg-cyan-400/40 rounded-full animate-wave-3 ml-2"></div>
      </div>
    </div>

    <!-- Metric bars animation -->
    <div class="flex items-end space-x-1 mt-6 h-8">
      <div v-for="i in 8" :key="i"
           class="w-2 bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-t animate-bar"
           :style="{ animationDelay: `${i * 0.1}s` }">
      </div>
    </div>

    <!-- Rotating message -->
    <p class="mt-6 text-lg text-gray-600 dark:text-gray-300 font-medium transition-opacity duration-300">
      {{ currentMessage }}
    </p>

    <!-- Animated dots -->
    <div class="flex space-x-1 mt-2">
      <div class="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style="animation-delay: 0s"></div>
      <div class="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
      <div class="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
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
  'Connecting to GenSlave...',
  'Checking relay status...',
  'Reading temperature sensors...',
  'Measuring memory usage...',
  'Scanning disk utilization...',
  'Testing WiFi signal strength...',
  'Retrieving system metrics...',
  'Validating heartbeat connection...',
  'Gathering hardware diagnostics...',
  'Analyzing system health...',
  'Checking failsafe status...',
  'Reading LCD display state...',
  'Polling automation hat...',
  'Verifying I2C communication...',
  'Checking SPI interfaces...',
  'Almost there...'
]

const messageIndex = ref(0)
let messageInterval = null

const activeMessages = computed(() => {
  if (props.messages && props.messages.length > 0) {
    return props.messages
  }
  // Shuffle and pick 10 messages
  const shuffled = [...defaultMessages].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, 10)
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
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.05); opacity: 0.8; }
}

@keyframes pulse-center {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

@keyframes orbit {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes orbit-reverse {
  from { transform: rotate(360deg); }
  to { transform: rotate(0deg); }
}

@keyframes orbit-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes bar {
  0%, 100% { height: 0.5rem; }
  50% { height: 2rem; }
}

@keyframes wave-1 {
  0%, 100% { opacity: 0.3; height: 0.75rem; }
  50% { opacity: 1; height: 1rem; }
}

@keyframes wave-2 {
  0%, 100% { opacity: 0.3; height: 1rem; }
  50% { opacity: 1; height: 1.5rem; }
}

@keyframes wave-3 {
  0%, 100% { opacity: 0.3; height: 1.25rem; }
  50% { opacity: 1; height: 2rem; }
}

.animate-spin-slow {
  animation: spin-slow 8s linear infinite;
}

.animate-pulse-ring {
  animation: pulse-ring 2s ease-in-out infinite;
}

.animate-pulse-center {
  animation: pulse-center 2s ease-in-out infinite;
}

.animate-orbit {
  animation: orbit 3s linear infinite;
}

.animate-orbit-reverse {
  animation: orbit-reverse 4s linear infinite;
}

.animate-orbit-slow {
  animation: orbit-slow 6s linear infinite;
}

.animate-blink {
  animation: blink 1.5s ease-in-out infinite;
}

.animate-bar {
  animation: bar 1s ease-in-out infinite;
}

.animate-wave-1 {
  animation: wave-1 1.5s ease-in-out infinite;
}

.animate-wave-2 {
  animation: wave-2 1.5s ease-in-out infinite 0.2s;
}

.animate-wave-3 {
  animation: wave-3 1.5s ease-in-out infinite 0.4s;
}
</style>
