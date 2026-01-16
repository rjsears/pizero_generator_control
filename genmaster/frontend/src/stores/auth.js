// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/auth.js
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
import authService from '@/services/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin || false)
  const username = computed(() => user.value?.username || '')

  // Actions
  async function login(credentials) {
    loading.value = true
    error.value = null

    try {
      const response = await authService.login(credentials)
      token.value = response.token.access_token
      user.value = response.user
      localStorage.setItem('token', token.value)
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authService.logout()
    } catch {
      // Ignore logout errors
    } finally {
      token.value = null
      user.value = null
      localStorage.removeItem('token')
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) return

    loading.value = true
    try {
      const userData = await authService.getCurrentUser()
      user.value = userData
    } catch {
      // Token might be invalid, clear it
      token.value = null
      user.value = null
      localStorage.removeItem('token')
    } finally {
      loading.value = false
    }
  }

  async function changePassword(currentPassword, newPassword) {
    loading.value = true
    error.value = null

    try {
      await authService.changePassword(currentPassword, newPassword)
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Password change failed'
      return false
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    user,
    token,
    loading,
    error,

    // Getters
    isAuthenticated,
    isAdmin,
    username,

    // Actions
    login,
    logout,
    fetchCurrentUser,
    changePassword,
    clearError,
  }
})
