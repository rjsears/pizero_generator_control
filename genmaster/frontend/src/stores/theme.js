// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/theme.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'genmaster-theme'

export const useThemeStore = defineStore('theme', () => {
  // State
  const theme = ref('system') // 'light', 'dark', or 'system'

  // Getters
  const isDark = computed(() => {
    if (theme.value === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return theme.value === 'dark'
  })

  const currentTheme = computed(() => theme.value)

  // Actions
  function initialize() {
    // Load saved preference
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && ['light', 'dark', 'system'].includes(saved)) {
      theme.value = saved
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      // Force reactivity update when system preference changes
      if (theme.value === 'system') {
        theme.value = 'system'
      }
    })

    // Apply initial theme
    applyTheme()
  }

  function setTheme(newTheme) {
    if (['light', 'dark', 'system'].includes(newTheme)) {
      theme.value = newTheme
      localStorage.setItem(STORAGE_KEY, newTheme)
      applyTheme()
    }
  }

  function toggleTheme() {
    const themes = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme.value)
    const nextIndex = (currentIndex + 1) % themes.length
    setTheme(themes[nextIndex])
  }

  function applyTheme() {
    const root = document.documentElement

    if (isDark.value) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }

  // Watch for theme changes
  watch(isDark, () => {
    applyTheme()
  })

  return {
    // State
    theme,

    // Getters
    isDark,
    currentTheme,

    // Actions
    initialize,
    setTheme,
    toggleTheme,
  }
})
