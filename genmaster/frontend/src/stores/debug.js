// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/debug.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 17th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useDebugStore = defineStore('debug', () => {
  const isEnabled = ref(false)
  const loading = ref(false)

  async function loadDebugMode() {
    try {
      const response = await api.get('/settings/debug_mode')
      isEnabled.value = response.data?.value ?? false
    } catch {
      // Setting might not exist yet, default to false
      isEnabled.value = false
    }
  }

  async function toggleDebugMode() {
    loading.value = true
    try {
      const newValue = !isEnabled.value
      await api.put('/settings/debug_mode', {
        value: newValue,
        description: 'Enable debug mode for verbose logging',
      })
      isEnabled.value = newValue
    } catch (error) {
      console.error('Failed to toggle debug mode:', error)
    } finally {
      loading.value = false
    }
  }

  async function setDebugMode(enabled) {
    loading.value = true
    try {
      await api.put('/settings/debug_mode', {
        value: enabled,
        description: 'Enable debug mode for verbose logging',
      })
      isEnabled.value = enabled
    } catch (error) {
      console.error('Failed to set debug mode:', error)
    } finally {
      loading.value = false
    }
  }

  return {
    isEnabled,
    loading,
    loadDebugMode,
    toggleDebugMode,
    setDebugMode,
  }
})
