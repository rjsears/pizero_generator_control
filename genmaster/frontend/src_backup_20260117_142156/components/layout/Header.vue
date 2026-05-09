<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/layout/Header.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <header class="sticky top-0 z-30 flex items-center h-16 px-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
    <!-- Mobile menu button -->
    <button
      type="button"
      class="lg:hidden p-2 -ml-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      @click="$emit('toggle-sidebar')"
    >
      <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <!-- Generator status indicator -->
    <div class="flex items-center ml-4 lg:ml-0">
      <StatusBadge :status="generatorStatusColor" :pulse="isGeneratorRunning">
        {{ generatorStatusText }}
      </StatusBadge>
    </div>

    <!-- Spacer -->
    <div class="flex-1"></div>

    <!-- Right side actions -->
    <div class="flex items-center space-x-4">
      <!-- Theme toggle -->
      <button
        type="button"
        class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        @click="toggleTheme"
      >
        <svg v-if="isDark" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>

      <!-- User menu -->
      <div class="relative">
        <button
          type="button"
          class="flex items-center space-x-2 p-2 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          @click="showUserMenu = !showUserMenu"
        >
          <div class="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
            <span class="text-sm font-medium text-white">
              {{ userInitial }}
            </span>
          </div>
          <span class="hidden sm:block text-sm font-medium">{{ username }}</span>
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- Dropdown menu -->
        <Transition name="fade">
          <div
            v-if="showUserMenu"
            class="absolute right-0 mt-2 w-48 py-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          >
            <div class="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
              <p class="text-sm font-medium text-gray-900 dark:text-white">{{ username }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ isAdmin ? 'Administrator' : 'User' }}
              </p>
            </div>
            <button
              type="button"
              class="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
              @click="handleLogout"
            >
              Sign out
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Click outside to close menu -->
    <div
      v-if="showUserMenu"
      class="fixed inset-0 z-[-1]"
      @click="showUserMenu = false"
    ></div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGeneratorStore } from '@/stores/generator'
import { useThemeStore } from '@/stores/theme'
import StatusBadge from '@/components/common/StatusBadge.vue'

defineEmits(['toggle-sidebar'])

const router = useRouter()
const authStore = useAuthStore()
const generatorStore = useGeneratorStore()
const themeStore = useThemeStore()

const showUserMenu = ref(false)

const username = computed(() => authStore.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isAdmin = computed(() => authStore.isAdmin)
const isDark = computed(() => themeStore.isDark)

const generatorState = computed(() => generatorStore.currentState)
const isGeneratorRunning = computed(() => generatorStore.isRunning)

const generatorStatusText = computed(() => {
  const states = {
    stopped: 'Generator Stopped',
    starting: 'Starting...',
    warmup: 'Warming Up',
    running: 'Running',
    stopping: 'Stopping...',
    cooldown: 'Cooling Down',
    error: 'Error',
    unknown: 'Unknown',
  }
  return states[generatorState.value] || 'Unknown'
})

const generatorStatusColor = computed(() => {
  const colors = {
    stopped: 'gray',
    starting: 'amber',
    warmup: 'amber',
    running: 'green',
    stopping: 'amber',
    cooldown: 'blue',
    error: 'red',
    unknown: 'gray',
  }
  return colors[generatorState.value] || 'gray'
})

function toggleTheme() {
  themeStore.toggleTheme()
}

async function handleLogout() {
  showUserMenu.value = false
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
