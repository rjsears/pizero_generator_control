<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/ScheduleView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Page header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Schedule</h1>
          <p class="text-gray-600 dark:text-gray-400 mt-1">Manage scheduled generator runs</p>
        </div>
        <Button variant="primary" @click="openCreateModal">
          <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Schedule
        </Button>
      </div>

      <!-- Loading state -->
      <div v-if="loading">
        <ScheduleLoader />
      </div>

      <!-- Empty state -->
      <Card v-else-if="schedules.length === 0">
        <div class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">No schedules</h3>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Get started by creating your first schedule.</p>
          <Button variant="primary" class="mt-4" @click="openCreateModal">
            Create Schedule
          </Button>
        </div>
      </Card>

      <!-- Schedules list -->
      <div v-else class="space-y-4">
        <Card v-for="schedule in schedules" :key="schedule.id">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
              <div :class="['w-12 h-12 rounded-lg flex items-center justify-center', schedule.enabled ? 'bg-green-100 dark:bg-green-900' : 'bg-gray-100 dark:bg-gray-700']">
                <svg class="w-6 h-6" :class="schedule.enabled ? 'text-green-600 dark:text-green-400' : 'text-gray-400'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 class="font-medium text-gray-900 dark:text-white">{{ schedule.name }}</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  {{ formatScheduleTime(schedule) }} - {{ schedule.duration_minutes }} minutes
                </p>
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <StatusBadge :status="schedule.enabled ? 'success' : 'gray'">
                {{ schedule.enabled ? 'Active' : 'Disabled' }}
              </StatusBadge>
              <div class="flex items-center space-x-2">
                <button
                  class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  @click="openEditModal(schedule)"
                >
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  class="p-2 text-gray-400 hover:text-red-600"
                  @click="confirmDelete(schedule)"
                >
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Modal v-model="showModal" :title="editingSchedule ? 'Edit Schedule' : 'Create Schedule'" size="lg">
      <form @submit.prevent="saveSchedule" class="space-y-4">
        <Input
          v-model="form.name"
          label="Name"
          placeholder="Morning run"
          required
        />

        <div class="grid grid-cols-2 gap-4">
          <Input
            v-model="form.start_time"
            type="time"
            label="Start Time"
            required
          />
          <Input
            v-model="form.duration_minutes"
            type="number"
            label="Duration (minutes)"
            :min="1"
            :max="480"
            required
          />
        </div>

        <div>
          <label class="label">Days of Week</label>
          <div class="flex flex-wrap gap-2 mt-2">
            <button
              v-for="(day, index) in daysOfWeek"
              :key="index"
              type="button"
              :class="[
                'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                form.days_of_week.includes(index)
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
              ]"
              @click="toggleDay(index)"
            >
              {{ day }}
            </button>
          </div>
        </div>

        <div class="flex items-center">
          <Toggle v-model="form.enabled" label="Enable schedule" />
        </div>
      </form>

      <template #footer>
        <Button variant="secondary" @click="showModal = false">Cancel</Button>
        <Button variant="primary" @click="saveSchedule" :loading="saving">
          {{ editingSchedule ? 'Update' : 'Create' }}
        </Button>
      </template>
    </Modal>

    <!-- Delete Confirmation Modal -->
    <Modal v-model="showDeleteConfirm" title="Delete Schedule">
      <p class="text-gray-600 dark:text-gray-400">
        Are you sure you want to delete "{{ deletingSchedule?.name }}"? This action cannot be undone.
      </p>
      <template #footer>
        <Button variant="secondary" @click="showDeleteConfirm = false">Cancel</Button>
        <Button variant="danger" @click="deleteSchedule" :loading="deleting">Delete</Button>
      </template>
    </Modal>
  </MainLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import scheduleService from '@/services/schedule'
import { useNotificationStore } from '@/stores/notifications'
import MainLayout from '@/components/layout/MainLayout.vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ScheduleLoader from '@/components/common/ScheduleLoader.vue'

const notifications = useNotificationStore()

const schedules = ref([])
const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)

const showModal = ref(false)
const showDeleteConfirm = ref(false)
const editingSchedule = ref(null)
const deletingSchedule = ref(null)

const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const defaultForm = {
  name: '',
  start_time: '06:00',
  duration_minutes: 30,
  days_of_week: [1, 2, 3, 4, 5], // Weekdays
  enabled: true,
}

const form = ref({ ...defaultForm })

onMounted(async () => {
  await loadSchedules()
})

async function loadSchedules() {
  loading.value = true
  try {
    schedules.value = await scheduleService.getAll()
  } catch {
    notifications.error('Failed to load schedules')
  } finally {
    loading.value = false
  }
}

function formatScheduleTime(schedule) {
  const days = schedule.days_of_week
    .map(d => daysOfWeek[d])
    .join(', ')
  return `${schedule.start_time} on ${days}`
}

function openCreateModal() {
  editingSchedule.value = null
  form.value = { ...defaultForm }
  showModal.value = true
}

function openEditModal(schedule) {
  editingSchedule.value = schedule
  form.value = {
    name: schedule.name,
    start_time: schedule.start_time,
    duration_minutes: schedule.duration_minutes,
    days_of_week: [...schedule.days_of_week],
    enabled: schedule.enabled,
  }
  showModal.value = true
}

function toggleDay(day) {
  const index = form.value.days_of_week.indexOf(day)
  if (index === -1) {
    form.value.days_of_week.push(day)
  } else {
    form.value.days_of_week.splice(index, 1)
  }
  form.value.days_of_week.sort()
}

async function saveSchedule() {
  if (form.value.days_of_week.length === 0) {
    notifications.warning('Please select at least one day')
    return
  }

  saving.value = true
  try {
    if (editingSchedule.value) {
      await scheduleService.update(editingSchedule.value.id, form.value)
      notifications.success('Schedule updated')
    } else {
      await scheduleService.create(form.value)
      notifications.success('Schedule created')
    }
    showModal.value = false
    await loadSchedules()
  } catch {
    notifications.error('Failed to save schedule')
  } finally {
    saving.value = false
  }
}

function confirmDelete(schedule) {
  deletingSchedule.value = schedule
  showDeleteConfirm.value = true
}

async function deleteSchedule() {
  if (!deletingSchedule.value) return

  deleting.value = true
  try {
    await scheduleService.delete(deletingSchedule.value.id)
    notifications.success('Schedule deleted')
    showDeleteConfirm.value = false
    await loadSchedules()
  } catch {
    notifications.error('Failed to delete schedule')
  } finally {
    deleting.value = false
  }
}
</script>
