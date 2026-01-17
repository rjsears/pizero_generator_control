<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/layouts/HorizontalLayout.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import {
  HomeIcon,
  BoltIcon,
  GlobeAltIcon,
  CalendarIcon,
  ClockIcon,
  ServerStackIcon,
  CpuChipIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  SunIcon,
  MoonIcon,
  InformationCircleIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

// Dialog states
const showAbout = ref(false)

const navItems = [
  { name: 'Dashboard', route: 'dashboard', icon: HomeIcon },
  { name: 'Generator', route: 'generator', icon: BoltIcon },
  { name: 'GenSlave', route: 'genslave', icon: GlobeAltIcon },
  { name: 'Schedule', route: 'schedule', icon: CalendarIcon },
  { name: 'History', route: 'history', icon: ClockIcon },
  { name: 'Containers', route: 'containers', icon: ServerStackIcon },
  { name: 'System', route: 'system', icon: CpuChipIcon },
  { name: 'Settings', route: 'settings', icon: Cog6ToothIcon },
]

const isActive = (routeName) => route.name === routeName

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen bg-background-primary">
    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-[100] border-b border-gray-400 dark:border-black bg-surface backdrop-blur-sm bg-opacity-95 dark:bg-opacity-95">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center justify-between">
          <!-- Logo -->
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <span class="text-xl font-bold text-primary">Gen</span>
              <span class="text-xl font-light text-secondary ml-1">Master</span>
            </div>
          </div>

          <!-- Navigation -->
          <nav class="hidden md:flex items-center space-x-1">
            <router-link
              v-for="item in navItems"
              :key="item.route"
              :to="{ name: item.route }"
              :class="[
                'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                isActive(item.route)
                  ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                  : 'text-secondary hover:text-primary hover:bg-surface-hover'
              ]"
            >
              <component :is="item.icon" class="h-5 w-5 mr-1.5" />
              {{ item.name }}
            </router-link>
          </nav>

          <!-- Right side -->
          <div class="flex items-center space-x-3">
            <!-- About button -->
            <button
              @click="showAbout = true"
              class="p-2 rounded-lg text-secondary hover:text-primary hover:bg-surface-hover transition-colors"
              title="About"
            >
              <InformationCircleIcon class="h-5 w-5" />
            </button>

            <!-- Theme toggle -->
            <button
              @click="themeStore.toggleColorMode"
              class="p-2 rounded-lg text-secondary hover:text-primary hover:bg-surface-hover transition-colors"
            >
              <SunIcon v-if="themeStore.isDark" class="h-5 w-5" />
              <MoonIcon v-else class="h-5 w-5" />
            </button>

            <!-- User menu -->
            <div class="flex items-center space-x-2">
              <span class="text-sm text-secondary hidden sm:block">
                {{ authStore.username }}
              </span>
              <button
                @click="handleLogout"
                class="p-2 rounded-lg text-secondary hover:text-red-500 hover:bg-red-500/10 transition-colors"
                title="Logout"
              >
                <ArrowRightOnRectangleIcon class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>

    <!-- About Dialog -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showAbout"
          class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          <div class="absolute inset-0 bg-black/50" @click="showAbout = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full border border-gray-400 dark:border-gray-700">
            <div class="px-6 py-4 border-b border-gray-400 dark:border-gray-700">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <BoltIcon class="h-6 w-6 text-blue-500" />
                </div>
                <div>
                  <h3 class="text-lg font-semibold text-primary">GenMaster</h3>
                  <p class="text-sm text-secondary">RPi Generator Control Suite</p>
                </div>
              </div>
            </div>
            <div class="px-6 py-4 space-y-3">
              <p class="text-sm text-secondary">Version 1.0.0</p>
              <p class="text-sm text-secondary">January 15th, 2026</p>
              <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
                <p class="text-sm text-primary font-medium">Richard J. Sears</p>
                <p class="text-sm text-secondary">richardjsears@protonmail.com</p>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-gray-400 dark:border-gray-700">
              <button @click="showAbout = false" class="w-full btn-secondary">Close</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
