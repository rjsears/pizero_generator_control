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
import { ref, computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Internal state
  const _colorMode = ref('dark') // 'light' or 'dark'
  const _layoutMode = ref('sidebar') // 'horizontal' or 'sidebar'
  const _sidebarCollapsed = ref(false)

  // Read-only getters
  const isDark = computed(() => _colorMode.value === 'dark')
  const isSidebar = computed(() => _layoutMode.value === 'sidebar')
  const sidebarCollapsed = computed(() => _sidebarCollapsed.value)

  // For compatibility
  const currentPreset = computed(() => {
    return _colorMode.value === 'dark' ? 'modern_dark' : 'modern_light'
  })

  // Theme classes for App.vue root element
  const themeClasses = computed(() => {
    const classes = []
    if (isDark.value) classes.push('dark')
    if (isSidebar.value) classes.push('layout-sidebar')
    else classes.push('layout-horizontal')
    return classes.join(' ')
  })

  // Writable computed for v-model binding
  const colorMode = computed({
    get: () => _colorMode.value,
    set: (val) => setColorMode(val)
  })

  const layout = computed({
    get: () => _layoutMode.value,
    set: (val) => setLayoutMode(val)
  })

  // Apply theme to DOM
  function applyTheme() {
    const html = document.documentElement
    const body = document.body

    // Reset classes
    html.classList.remove('dark', 'layout-sidebar', 'layout-horizontal')
    body.classList.remove('dark', 'layout-sidebar', 'layout-horizontal')

    // Apply dark mode
    if (isDark.value) {
      html.classList.add('dark')
      body.classList.add('dark')
    }

    // Apply layout
    if (isSidebar.value) {
      html.classList.add('layout-sidebar')
      body.classList.add('layout-sidebar')
    } else {
      html.classList.add('layout-horizontal')
      body.classList.add('layout-horizontal')
    }
  }

  // Actions
  function setColorMode(mode) {
    _colorMode.value = mode
    localStorage.setItem('color_mode', mode)
    applyTheme()
  }

  function setLayoutMode(mode) {
    _layoutMode.value = mode
    localStorage.setItem('layout_mode', mode)
    applyTheme()
  }

  function setPreset(presetName) {
    // For compatibility - presets just set color mode
    if (presetName === 'modern_dark') {
      setColorMode('dark')
    } else {
      setColorMode('light')
    }
  }

  function toggleColorMode() {
    setColorMode(_colorMode.value === 'light' ? 'dark' : 'light')
  }

  function toggleTheme() {
    toggleColorMode()
  }

  function toggleSidebar() {
    _sidebarCollapsed.value = !_sidebarCollapsed.value
    localStorage.setItem('sidebar_collapsed', _sidebarCollapsed.value)
  }

  function init() {
    // Load from local storage
    const savedColorMode = localStorage.getItem('color_mode')
    const savedLayout = localStorage.getItem('layout_mode')
    const savedCollapsed = localStorage.getItem('sidebar_collapsed')

    if (savedColorMode) {
      _colorMode.value = savedColorMode
    } else {
      // System preference
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        _colorMode.value = 'dark'
      }
    }

    if (savedLayout) {
      _layoutMode.value = savedLayout
    }

    if (savedCollapsed !== null) {
      _sidebarCollapsed.value = savedCollapsed === 'true'
    }

    applyTheme()
  }

  // Alias for backwards compatibility
  function initialize() {
    init()
  }

  return {
    // Read-only state
    currentPreset,
    sidebarCollapsed,
    themeClasses,
    // Computed getters
    isDark,
    isSidebar,
    // Writable computed for v-model binding
    colorMode,
    layout,
    // Legacy compatibility
    layoutMode: _layoutMode,
    theme: _colorMode,
    // Actions
    setPreset,
    applyPreset: setPreset,
    setColorMode,
    setLayoutMode,
    toggleColorMode,
    toggleTheme,
    toggleSidebar,
    applyTheme,
    init,
    initialize,
  }
})
