<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/GeneratorInfoCard.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <Card title="Generator Information">
    <template #actions>
      <Button
        variant="secondary"
        size="sm"
        @click="showEditModal = true"
      >
        <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        Edit
      </Button>
    </template>

    <div v-if="loading" class="text-center py-8">
      <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
      <p class="text-sm text-gray-500 mt-2">Loading generator info...</p>
    </div>

    <div v-else class="space-y-4">
      <!-- Generator Identity -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Manufacturer</p>
          <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
            {{ info.manufacturer || 'Not set' }}
          </p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Model</p>
          <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
            {{ info.model_number || 'Not set' }}
          </p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Serial Number</p>
          <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
            {{ info.serial_number || 'Not set' }}
          </p>
        </div>
      </div>

      <!-- Fuel Configuration -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Fuel Configuration</h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Fuel Type</p>
            <p class="text-sm font-semibold mt-1">
              <span :class="fuelTypeBadgeClass">
                {{ formatFuelType(info.fuel_type) }}
              </span>
            </p>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Expected Load</p>
            <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
              {{ info.load_expected ? `${info.load_expected}%` : 'Not set' }}
            </p>
          </div>
          <div>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Current Rate</p>
            <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
              {{ currentConsumptionRate }} gal/hr
            </p>
          </div>
        </div>
      </div>

      <!-- Consumption Rates -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Fuel Consumption Rates</h4>
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400">At 50% Load</p>
            <p class="text-lg font-bold text-gray-900 dark:text-white mt-1">
              {{ info.fuel_consumption_50 !== null ? `${info.fuel_consumption_50} gal/hr` : 'Not set' }}
            </p>
          </div>
          <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400">At 100% Load</p>
            <p class="text-lg font-bold text-gray-900 dark:text-white mt-1">
              {{ info.fuel_consumption_100 !== null ? `${info.fuel_consumption_100} gal/hr` : 'Not set' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <GeneratorInfoEditModal
      v-model="showEditModal"
      :info="info"
      @saved="handleSaved"
    />
  </Card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import GeneratorInfoEditModal from '@/components/GeneratorInfoEditModal.vue'
import generatorInfoService from '@/services/generatorInfo'

const loading = ref(true)
const showEditModal = ref(false)
const info = ref({
  manufacturer: null,
  model_number: null,
  serial_number: null,
  fuel_type: null,
  load_expected: null,
  fuel_consumption_50: null,
  fuel_consumption_100: null,
})

const fuelTypeBadgeClass = computed(() => {
  const type = info.value.fuel_type
  const baseClasses = 'px-2 py-0.5 text-xs font-medium rounded-full'
  switch (type) {
    case 'lpg':
      return `${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400`
    case 'natural_gas':
      return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400`
    case 'diesel':
      return `${baseClasses} bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400`
    default:
      return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400`
  }
})

const currentConsumptionRate = computed(() => {
  if (info.value.load_expected === 50 && info.value.fuel_consumption_50 !== null) {
    return info.value.fuel_consumption_50
  } else if (info.value.load_expected === 100 && info.value.fuel_consumption_100 !== null) {
    return info.value.fuel_consumption_100
  }
  return 'N/A'
})

function formatFuelType(type) {
  const types = {
    lpg: 'LPG (Propane)',
    natural_gas: 'Natural Gas',
    diesel: 'Diesel',
  }
  return types[type] || 'Not set'
}

async function fetchInfo() {
  loading.value = true
  try {
    const response = await generatorInfoService.get()
    info.value = response.data
  } catch (error) {
    console.error('Failed to fetch generator info:', error)
  } finally {
    loading.value = false
  }
}

function handleSaved(updatedInfo) {
  info.value = updatedInfo
}

onMounted(() => {
  fetchInfo()
})
</script>
