<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/GeneratorView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Generator Control</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Monitor and control the generator</p>
    </div>

    <!-- Runtime Lockout Banner -->
    <div
      v-if="runtimeLimitsStatus.lockout_active"
      class="rounded-xl p-4 border-2 border-amber-500 bg-gradient-to-r from-amber-500/20 to-amber-500/10"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="p-3 rounded-xl bg-amber-500/30">
            <ExclamationTriangleIcon class="h-8 w-8 text-amber-500" />
          </div>
          <div>
            <h2 class="text-xl font-bold text-amber-700 dark:text-amber-300">
              Runtime Lockout Active
            </h2>
            <p class="text-sm text-amber-600 dark:text-amber-400">
              Generator reached maximum runtime. Victron auto-start is disabled until you acknowledge.
            </p>
          </div>
        </div>
        <Button
          variant="warning"
          :loading="clearingLockout"
          @click="handleClearLockout"
        >
          Acknowledge &amp; Reset
        </Button>
      </div>
    </div>

    <!-- Cooldown Banner -->
    <div
      v-if="runtimeLimitsStatus.cooldown_active && !runtimeLimitsStatus.lockout_active"
      class="rounded-xl p-4 border-2 border-blue-500 bg-gradient-to-r from-blue-500/20 to-blue-500/10"
    >
      <div class="flex items-center gap-4">
        <div class="p-3 rounded-xl bg-blue-500/30">
          <ClockIcon class="h-8 w-8 text-blue-500" />
        </div>
        <div>
          <h2 class="text-xl font-bold text-blue-700 dark:text-blue-300">
            Cooldown Period Active
          </h2>
          <p class="text-sm text-blue-600 dark:text-blue-400">
            Generator reached maximum runtime. Victron auto-start will be allowed in
            <span class="font-bold">{{ formatCooldownRemaining(runtimeLimitsStatus.cooldown_remaining_seconds) }}</span>.
          </p>
        </div>
      </div>
    </div>

    <!-- Control Row: GenSlave | Relay | Generator | Emergency Stop -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- GenSlave Online Status -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'p-2 rounded-lg',
                slaveOnline ? 'bg-emerald-100 dark:bg-emerald-500/20' : 'bg-red-100 dark:bg-red-500/20'
              ]"
            >
              <ServerIcon
                :class="[
                  'h-5 w-5',
                  slaveOnline ? 'text-emerald-500' : 'text-red-500'
                ]"
              />
            </div>
            <div>
              <p class="text-sm text-secondary">GenSlave</p>
              <p
                :class="[
                  'text-xl font-bold',
                  slaveOnline ? 'text-emerald-500' : 'text-red-500'
                ]"
              >
                {{ slaveOnline ? 'Online' : 'Offline' }}
              </p>
            </div>
          </div>
        </div>
      </Card>

      <!-- Relay Armed Status (GenSlave) -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div
                :class="[
                  'p-2 rounded-lg',
                  relayStateLoading ? 'bg-gray-100 dark:bg-gray-500/20' :
                  relayArmed ? 'bg-amber-100 dark:bg-amber-500/20' : 'bg-gray-100 dark:bg-gray-500/20'
                ]"
              >
                <ShieldExclamationIcon
                  :class="[
                    'h-5 w-5',
                    relayStateLoading ? 'text-gray-400 animate-pulse' :
                    relayArmed ? 'text-amber-500' : 'text-gray-500'
                  ]"
                />
              </div>
              <div>
                <p class="text-sm text-secondary">Relay</p>
                <p
                  :class="[
                    'text-xl font-bold',
                    relayStateLoading ? 'text-gray-400' :
                    relayArmed ? 'text-amber-500' : 'text-gray-500'
                  ]"
                >
                  {{ relayStateLoading ? 'Loading...' : (relayArmed ? 'Armed' : 'Disarmed') }}
                </p>
              </div>
            </div>
            <button
              @click="toggleRelayArm"
              :disabled="togglingRelay || relayStateLoading || !slaveOnline"
              :class="[
                'relative inline-flex h-6 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                relayArmed
                  ? 'bg-amber-500 focus:ring-amber-500'
                  : 'bg-gray-400 focus:ring-gray-500',
                (togglingRelay || relayStateLoading || !slaveOnline) ? 'opacity-50 cursor-not-allowed' : ''
              ]"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform',
                  relayArmed ? 'translate-x-7' : 'translate-x-1'
                ]"
              />
            </button>
          </div>
        </div>
      </Card>

      <!-- Generator Start/Stop Toggle -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div
                :class="[
                  'p-2 rounded-lg',
                  generatorStore.isRunning ? 'bg-green-100 dark:bg-green-500/20' : 'bg-gray-100 dark:bg-gray-500/20'
                ]"
              >
                <BoltIcon
                  :class="[
                    'h-5 w-5',
                    generatorStore.isRunning ? 'text-green-500' : 'text-gray-500'
                  ]"
                />
              </div>
              <div>
                <p class="text-sm text-secondary">Generator</p>
                <p
                  :class="[
                    'text-xl font-bold',
                    generatorStore.isRunning ? 'text-green-500' : 'text-gray-500'
                  ]"
                >
                  {{ generatorStore.isRunning ? 'Running' : 'Stopped' }}
                </p>
              </div>
            </div>
            <button
              @click="handleQuickToggle"
              :disabled="generatorToggleLoading || relayStateLoading || !relayArmed"
              :class="[
                'relative inline-flex h-6 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                generatorStore.isRunning
                  ? 'bg-green-500 focus:ring-green-500'
                  : 'bg-gray-400 focus:ring-gray-500',
                (generatorToggleLoading || relayStateLoading || !relayArmed) ? 'opacity-50 cursor-not-allowed' : ''
              ]"
              :title="relayStateLoading ? 'Loading relay state...' : (!relayArmed ? 'Relay must be armed to control generator' : '')"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform',
                  generatorStore.isRunning ? 'translate-x-7' : 'translate-x-1'
                ]"
              />
            </button>
          </div>
        </div>
      </Card>

      <!-- Emergency Stop -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-red-100 dark:bg-red-500/20">
                <ExclamationTriangleIcon class="h-5 w-5 text-red-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Emergency</p>
                <p class="text-xl font-bold text-red-500">Stop</p>
              </div>
            </div>
            <button
              @click="handleEmergencyStop"
              :disabled="!generatorStore.isRunning || emergencyStopLoading"
              :class="[
                'px-4 py-2 rounded-lg font-bold text-sm text-white transition-all',
                generatorStore.isRunning && !emergencyStopLoading
                  ? 'bg-red-500 hover:bg-red-600 shadow-lg'
                  : 'bg-gray-400 cursor-not-allowed'
              ]"
            >
              <span v-if="emergencyStopLoading">...</span>
              <span v-else>STOP</span>
            </button>
          </div>
        </div>
      </Card>
    </div>

    <!-- Generator Status Row: Generator Status and Victron Command -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Generator Status - Enhanced with animated icon and controls -->
      <Card :padding="false">
        <div class="p-6">
          <div class="flex items-start gap-6">
            <!-- Animated Generator Icon -->
            <div
              :class="[
                'relative w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-500',
                generatorStore.isRunning ? 'bg-gradient-to-br from-green-400 to-green-600 shadow-lg shadow-green-500/30' : 'bg-gradient-to-br from-gray-400 to-gray-600'
              ]"
            >
              <!-- Pulsing ring when running -->
              <div
                v-if="generatorStore.isRunning"
                class="absolute inset-0 rounded-2xl bg-green-400 animate-ping opacity-20"
              />
              <!-- Spinning cog when running -->
              <CogIcon
                :class="[
                  'w-10 h-10 text-white relative z-10',
                  generatorStore.isRunning ? 'animate-spin-slow' : ''
                ]"
              />
            </div>

            <!-- Status Info -->
            <div class="flex-1">
              <p class="text-sm font-medium text-secondary uppercase tracking-wider">Generator Status</p>
              <p class="text-3xl font-black mt-1" :class="generatorStateClass">
                {{ generatorStateText }}
              </p>

              <!-- Trigger reason, runtime, and fuel usage -->
              <div class="mt-3 flex flex-wrap gap-3">
                <!-- Trigger Badge -->
                <div
                  v-if="generatorTrigger && generatorStore.isRunning"
                  :class="[
                    'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold',
                    triggerBadgeClass
                  ]"
                >
                  <component :is="triggerIcon" class="w-3.5 h-3.5" />
                  {{ triggerLabel }}
                </div>

                <!-- Runtime Badge -->
                <div
                  v-if="generatorStore.isRunning"
                  class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300"
                >
                  <ClockIcon class="w-3.5 h-3.5" />
                  {{ formatMinutes(localRunTimeMinutes) }}
                </div>

                <!-- Estimated Fuel Badge (when running) -->
                <div
                  v-if="generatorStore.isRunning && estimatedCurrentFuel > 0"
                  class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-orange-100 dark:bg-orange-500/20 text-orange-700 dark:text-orange-300"
                >
                  <FireIcon class="w-3.5 h-3.5" />
                  ~{{ estimatedCurrentFuel.toFixed(2) }} gal
                </div>
              </div>
            </div>
          </div>

          <!-- Runtime bar when running -->
          <div v-if="generatorStore.isRunning" class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between text-sm mb-2">
              <span class="text-secondary">Runtime</span>
              <span class="font-medium text-primary">{{ formatMinutes(localRunTimeMinutes) }}</span>
            </div>
            <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-green-400 to-green-600 rounded-full transition-all animate-pulse"
                :style="{ width: `${Math.min((localRunTimeMinutes / 120) * 100, 100)}%` }"
              />
            </div>
          </div>

          <!-- Control Buttons -->
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex gap-3">
            <Button
              :variant="canStart ? 'success' : 'secondary'"
              :disabled="!canStart || actionLoading"
              :loading="actionLoading"
              class="flex-1"
              @click="showStartModal = true"
            >
              <PlayIcon class="w-5 h-5 mr-2" />
              Start Generator
            </Button>
            <Button
              :variant="canStop ? 'danger' : 'secondary'"
              :disabled="!canStop || actionLoading"
              :loading="actionLoading"
              class="flex-1"
              @click="handleStop"
            >
              <StopIcon class="w-5 h-5 mr-2" />
              Stop Generator
            </Button>
          </div>
        </div>
      </Card>

      <!-- Victron Status - GPIO17 input from Victron Cerbo -->
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Victron Command</p>
            <p class="text-2xl font-bold mt-1" :class="victronActive ? 'text-green-500' : 'text-gray-500'">
              {{ victronActive ? 'Generator Run' : 'Generator Stop' }}
            </p>
          </div>
          <div :class="['w-12 h-12 rounded-full flex items-center justify-center', victronActive ? 'bg-green-500' : 'bg-gray-400']">
            <SignalIcon class="w-6 h-6 text-white" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p class="text-sm text-secondary">GPIO17 {{ victronActive ? 'HIGH' : 'LOW' }}</p>
        </div>
      </Card>
    </div>

    <!-- Fuel Usage Tracking -->
    <Card title="Fuel Usage Tracking">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-secondary">Total Fuel Used</p>
          <p class="text-4xl font-bold text-orange-500 mt-1">
            {{ totalFuelUsed.toFixed(2) }} <span class="text-lg text-secondary">gallons</span>
          </p>
          <p class="text-xs text-muted mt-1">Since {{ fuelResetDate }}</p>
        </div>
        <div class="flex flex-col items-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            @click="showFuelResetConfirm = true"
          >
            <ArrowPathIcon class="w-4 h-4 mr-1" />
            Reset
          </Button>
        </div>
      </div>
    </Card>

    <!-- Manual Override -->
    <Card title="Manual Override">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-gray-700 dark:text-gray-300">
            Override automatic Victron control
          </p>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            When enabled, the generator will not automatically start based on Victron signals.
          </p>
        </div>
        <Toggle
          v-model="overrideEnabled"
          @update:model-value="handleOverrideToggle"
        />
      </div>
    </Card>

    <!-- Run Time Limits -->
    <Card title="Run Time Limits">
      <!-- Enable/Disable Toggle -->
      <div class="flex items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <p class="font-medium text-primary">Enable Runtime Limits</p>
          <p class="text-sm text-secondary">
            Automatically stop the generator after maximum run time
          </p>
        </div>
        <Toggle
          v-model="runTimeConfig.runtime_limits_enabled"
        />
      </div>

      <!-- Min/Max Run Time Inputs -->
      <div :class="['grid grid-cols-1 sm:grid-cols-2 gap-6 transition-opacity', !runTimeConfig.runtime_limits_enabled ? 'opacity-50 pointer-events-none' : '']">
        <div>
          <Input
            v-model="runTimeConfig.min_run_minutes"
            type="number"
            label="Minimum Run Time (minutes)"
            :min="1"
            :max="60"
            :disabled="!runTimeConfig.runtime_limits_enabled"
          />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Minimum duration for each generator run
          </p>
        </div>
        <div>
          <Input
            v-model="runTimeConfig.max_run_minutes"
            type="number"
            label="Maximum Run Time (minutes)"
            :min="1"
            :max="1440"
            :disabled="!runTimeConfig.runtime_limits_enabled"
          />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Maximum duration before automatic shutdown
          </p>
        </div>
      </div>

      <!-- Action when max time reached -->
      <div :class="['mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 transition-opacity', !runTimeConfig.runtime_limits_enabled ? 'opacity-50 pointer-events-none' : '']">
        <p class="font-medium text-primary mb-3">When Maximum Time Reached</p>
        <div class="space-y-3">
          <button
            @click="runTimeConfig.max_runtime_action = 'manual_reset'"
            :disabled="!runTimeConfig.runtime_limits_enabled"
            :class="[
              'w-full p-4 rounded-lg border-2 text-left transition-all',
              runTimeConfig.max_runtime_action === 'manual_reset'
                ? 'border-amber-500 bg-amber-50 dark:bg-amber-500/10'
                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
            ]"
          >
            <div class="flex items-center gap-3">
              <div :class="['w-5 h-5 rounded-full border-2 flex items-center justify-center', runTimeConfig.max_runtime_action === 'manual_reset' ? 'border-amber-500' : 'border-gray-400']">
                <div v-if="runTimeConfig.max_runtime_action === 'manual_reset'" class="w-2.5 h-2.5 rounded-full bg-amber-500"></div>
              </div>
              <div>
                <p class="font-semibold text-primary">Require Manual Reset</p>
                <p class="text-sm text-secondary">Generator stays off until you manually acknowledge</p>
              </div>
            </div>
          </button>

          <button
            @click="runTimeConfig.max_runtime_action = 'cooldown'"
            :disabled="!runTimeConfig.runtime_limits_enabled"
            :class="[
              'w-full p-4 rounded-lg border-2 text-left transition-all',
              runTimeConfig.max_runtime_action === 'cooldown'
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-500/10'
                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
            ]"
          >
            <div class="flex items-center gap-3">
              <div :class="['w-5 h-5 rounded-full border-2 flex items-center justify-center', runTimeConfig.max_runtime_action === 'cooldown' ? 'border-blue-500' : 'border-gray-400']">
                <div v-if="runTimeConfig.max_runtime_action === 'cooldown'" class="w-2.5 h-2.5 rounded-full bg-blue-500"></div>
              </div>
              <div>
                <p class="font-semibold text-primary">Cooldown Period</p>
                <p class="text-sm text-secondary">Generator stays off for a set time, then Victron can restart it</p>
              </div>
            </div>
          </button>

          <!-- Cooldown Duration (shown only when cooldown selected) -->
          <div v-if="runTimeConfig.max_runtime_action === 'cooldown'" class="pl-8 mt-3 grid grid-cols-2 gap-4">
            <div>
              <Input
                v-model="cooldownHours"
                type="number"
                label="Hours"
                :min="0"
                :max="23"
                :disabled="!runTimeConfig.runtime_limits_enabled"
              />
            </div>
            <div>
              <Input
                v-model="cooldownMinutes"
                type="number"
                label="Minutes"
                :min="0"
                :max="59"
                :disabled="!runTimeConfig.runtime_limits_enabled"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-end mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button
          :loading="savingRunTimeConfig"
          @click="saveRunTimeConfig"
        >
          Save Run Time Settings
        </Button>
      </div>
    </Card>

    <!-- Statistics -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Total Runs (30 days)</p>
          <p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {{ stats?.total_runs || 0 }}
          </p>
        </div>
      </Card>
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Total Runtime (30 days)</p>
          <p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {{ formatDuration(stats?.total_runtime_hours || 0, 'hours') }}
          </p>
        </div>
      </Card>
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Avg Run Duration</p>
          <p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
            {{ formatDuration((stats?.average_runtime_seconds || 0) / 60, 'minutes') }}
          </p>
        </div>
      </Card>
    </div>

    <!-- Generator Information -->
    <GeneratorInfoCard />

    <!-- Exercise Schedule -->
    <ExerciseScheduleCard />

    <!-- Start Generator Modal -->
    <Modal v-model="showStartModal" title="Start Generator">
      <p class="text-gray-600 dark:text-gray-400 mb-4">
        How would you like to run the generator?
      </p>
      <div class="space-y-3">
        <button
          @click="selectedRunType = 'continuous'"
          :class="[
            'w-full p-4 rounded-lg border-2 text-left transition-all',
            selectedRunType === 'continuous'
              ? 'border-green-500 bg-green-50 dark:bg-green-500/10'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          ]"
        >
          <div class="flex items-center gap-3">
            <div :class="['w-5 h-5 rounded-full border-2 flex items-center justify-center', selectedRunType === 'continuous' ? 'border-green-500' : 'border-gray-400']">
              <div v-if="selectedRunType === 'continuous'" class="w-2.5 h-2.5 rounded-full bg-green-500"></div>
            </div>
            <div>
              <p class="font-semibold text-primary">Continuous Run</p>
              <p class="text-sm text-secondary">Run until manually stopped or max time reached</p>
            </div>
          </div>
        </button>

        <button
          @click="selectedRunType = 'timed'"
          :class="[
            'w-full p-4 rounded-lg border-2 text-left transition-all',
            selectedRunType === 'timed'
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-500/10'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          ]"
        >
          <div class="flex items-center gap-3">
            <div :class="['w-5 h-5 rounded-full border-2 flex items-center justify-center', selectedRunType === 'timed' ? 'border-blue-500' : 'border-gray-400']">
              <div v-if="selectedRunType === 'timed'" class="w-2.5 h-2.5 rounded-full bg-blue-500"></div>
            </div>
            <div>
              <p class="font-semibold text-primary">Timed Run</p>
              <p class="text-sm text-secondary">Run for a specific duration then auto-stop</p>
            </div>
          </div>
        </button>

        <!-- Duration input (shown only for timed run) -->
        <div v-if="selectedRunType === 'timed'" class="mt-4 pl-8">
          <Input
            v-model="timedDuration"
            type="number"
            label="Duration (minutes)"
            :min="1"
            :max="480"
            placeholder="30"
          />
        </div>
      </div>
      <template #footer>
        <Button variant="secondary" @click="showStartModal = false">Cancel</Button>
        <Button
          variant="success"
          :disabled="selectedRunType === 'timed' && (!timedDuration || timedDuration < 1)"
          @click="executeStart"
        >
          Start Generator
        </Button>
      </template>
    </Modal>

    <!-- Confirm Stop Modal -->
    <Modal v-model="showStopConfirm" title="Stop Generator">
      <p class="text-gray-600 dark:text-gray-400">Are you sure you want to stop the generator?</p>
      <template #footer>
        <Button variant="secondary" @click="showStopConfirm = false">Cancel</Button>
        <Button variant="warning" @click="executeStop">Stop</Button>
      </template>
    </Modal>

    <!-- Emergency Stop Confirm Modal -->
    <Modal v-model="showEmergencyConfirm" title="Emergency Stop">
      <p class="text-gray-600 dark:text-gray-400">This will immediately stop the generator without cooldown. Continue?</p>
      <template #footer>
        <Button variant="secondary" @click="showEmergencyConfirm = false">Cancel</Button>
        <Button variant="danger" @click="executeEmergencyStop">Emergency Stop</Button>
      </template>
    </Modal>

    <!-- Fuel Reset Confirm Modal -->
    <Modal v-model="showFuelResetConfirm" title="Reset Fuel Tracking">
      <p class="text-gray-600 dark:text-gray-400">This will reset the total fuel usage counter to zero. Continue?</p>
      <template #footer>
        <Button variant="secondary" @click="showFuelResetConfirm = false">Cancel</Button>
        <Button variant="warning" @click="executeFuelReset">Reset</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useGeneratorStore } from '@/stores/generator'
import { useSystemStore } from '@/stores/system'
import { useNotificationStore } from '@/stores/notifications'
import configService from '@/services/config'
import { genslaveApi, configApi, generatorApi } from '@/services/api'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'
import GeneratorInfoCard from '@/components/GeneratorInfoCard.vue'
import ExerciseScheduleCard from '@/components/ExerciseScheduleCard.vue'
import {
  BoltIcon,
  ServerIcon,
  SignalIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CogIcon,
  CalendarIcon,
  HandRaisedIcon,
  BoltSlashIcon,
  ClockIcon,
  FireIcon,
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline'

const generatorStore = useGeneratorStore()
const systemStore = useSystemStore()
const notificationStore = useNotificationStore()

// Loading states
const loading = ref(true)
const relayStateLoading = ref(true)
const togglingRelay = ref(false)
const generatorToggleLoading = ref(false)
const emergencyStopLoading = ref(false)

// Relay state
const relayArmed = ref(null)

// Real-time runtime tracking
const localRunTimeSeconds = ref(0)
const localRunTimeMinutes = computed(() => Math.floor(localRunTimeSeconds.value / 60))
let runtimeInterval = null
let refreshInterval = null

// Modal states
const showStartModal = ref(false)
const showStopConfirm = ref(false)
const showEmergencyConfirm = ref(false)
const showFuelResetConfirm = ref(false)

// Start options
const selectedRunType = ref('continuous')
const timedDuration = ref(30)

// Run time config state
const runTimeConfig = ref({
  runtime_limits_enabled: false,
  min_run_minutes: 5,
  max_run_minutes: 480,
  max_runtime_action: 'manual_reset',
  cooldown_duration_minutes: 60,
})
const savingRunTimeConfig = ref(false)

// Runtime limits status (lockout/cooldown state)
const runtimeLimitsStatus = ref({
  enabled: false,
  lockout_active: false,
  lockout_started: null,
  lockout_reason: null,
  cooldown_active: false,
  cooldown_end_time: null,
  cooldown_remaining_seconds: null,
})
const clearingLockout = ref(false)

// Cooldown hours/minutes for UI (computed from cooldown_duration_minutes)
const cooldownHours = computed({
  get: () => Math.floor(runTimeConfig.value.cooldown_duration_minutes / 60),
  set: (val) => {
    runTimeConfig.value.cooldown_duration_minutes = (val * 60) + (runTimeConfig.value.cooldown_duration_minutes % 60)
  }
})
const cooldownMinutes = computed({
  get: () => runTimeConfig.value.cooldown_duration_minutes % 60,
  set: (val) => {
    const hours = Math.floor(runTimeConfig.value.cooldown_duration_minutes / 60)
    runTimeConfig.value.cooldown_duration_minutes = (hours * 60) + val
  }
})

// Override state
const overrideEnabled = ref(false)

// Stats
const stats = ref(null)

// Fuel tracking
const totalFuelUsed = ref(0)
const fuelResetTimestamp = ref(0)
const fuelResetDate = computed(() => {
  if (!fuelResetTimestamp.value) return 'initial'
  return new Date(fuelResetTimestamp.value * 1000).toLocaleDateString()
})

// Generator info for fuel calculation
const generatorInfo = ref({
  fuel_consumption_50: 0,
  fuel_consumption_100: 0,
  load_expected: 50,
})

// Estimated current fuel usage (while running)
const estimatedCurrentFuel = computed(() => {
  if (!generatorStore.isRunning || localRunTimeMinutes.value === 0) return 0
  const rate = generatorInfo.value.load_expected === 100
    ? generatorInfo.value.fuel_consumption_100
    : generatorInfo.value.fuel_consumption_50
  if (!rate) return 0
  return (localRunTimeMinutes.value / 60) * rate
})

// Computed properties
const canStart = computed(() => generatorStore.canStart && relayArmed.value)
const canStop = computed(() => generatorStore.canStop)
const actionLoading = computed(() => generatorStore.actionLoading)

const slaveOnline = computed(() => systemStore.isSlaveOnline)
const victronActive = computed(() => systemStore.victronInputActive)

const generatorStateText = computed(() => {
  const states = {
    stopped: 'Stopped',
    starting: 'Starting',
    warmup: 'Warming Up',
    running: 'Running',
    stopping: 'Stopping',
    cooldown: 'Cooldown',
    error: 'Error',
    unknown: 'Unknown',
  }
  return states[generatorStore.currentState] || 'Unknown'
})

const generatorStateClass = computed(() => {
  const classes = {
    stopped: 'text-gray-500',
    starting: 'text-amber-500',
    warmup: 'text-amber-500',
    running: 'text-green-500',
    stopping: 'text-amber-500',
    cooldown: 'text-blue-500',
    error: 'text-red-500',
    unknown: 'text-gray-500',
  }
  return classes[generatorStore.currentState] || 'text-gray-500'
})

const generatorTrigger = computed(() => generatorStore.state?.trigger || 'idle')

const triggerLabel = computed(() => {
  const labels = {
    victron: 'Victron Request',
    manual: 'Manual Start',
    scheduled: 'Scheduled Run',
    exercise: 'Exercise Run',
    idle: 'Idle',
  }
  return labels[generatorTrigger.value] || generatorTrigger.value
})

const triggerBadgeClass = computed(() => {
  const classes = {
    victron: 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300',
    manual: 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300',
    scheduled: 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-300',
    exercise: 'bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300',
    idle: 'bg-gray-100 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300',
  }
  return classes[generatorTrigger.value] || classes.idle
})

const triggerIcon = computed(() => {
  const icons = {
    victron: BoltIcon,
    manual: HandRaisedIcon,
    scheduled: CalendarIcon,
    exercise: ClockIcon,
    idle: BoltSlashIcon,
  }
  return icons[generatorTrigger.value] || BoltSlashIcon
})

// Helper functions
function formatMinutes(minutes) {
  if (!minutes || minutes === 0) return '0m'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

function formatDuration(value, unit = 'minutes') {
  if (!value || value === 0) return '0m'
  if (unit === 'hours') {
    const hours = Math.floor(value)
    const mins = Math.round((value - hours) * 60)
    if (hours > 0) {
      return `${hours}h ${mins}m`
    }
    return `${mins}m`
  }
  const hours = Math.floor(value / 60)
  const mins = Math.round(value % 60)
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

// Sync runtime from store
function syncRuntimeFromStore() {
  if (generatorStore.state?.start_time && generatorStore.isRunning) {
    const now = Math.floor(Date.now() / 1000)
    localRunTimeSeconds.value = now - generatorStore.state.start_time
  } else if (generatorStore.state?.runtime_seconds) {
    localRunTimeSeconds.value = generatorStore.state.runtime_seconds
  } else {
    localRunTimeSeconds.value = 0
  }
}

// Update runtime timer
function updateRuntimeTimer() {
  if (runtimeInterval) {
    clearInterval(runtimeInterval)
    runtimeInterval = null
  }

  if (generatorStore.isRunning) {
    syncRuntimeFromStore()
    runtimeInterval = setInterval(() => {
      localRunTimeSeconds.value++
    }, 1000)
  }
}

// Fetch relay state
async function fetchRelayState() {
  relayStateLoading.value = true
  try {
    const response = await genslaveApi.getRelayState()
    relayArmed.value = response.data?.armed || false
  } catch (err) {
    console.error('Failed to fetch relay state:', err)
    relayArmed.value = false
  } finally {
    relayStateLoading.value = false
  }
}

// Toggle relay arm/disarm
async function toggleRelayArm() {
  togglingRelay.value = true
  try {
    if (relayArmed.value) {
      await genslaveApi.disarm()
      relayArmed.value = false
    } else {
      await genslaveApi.arm()
      relayArmed.value = true
    }
  } catch (err) {
    console.error('Failed to toggle relay arm state:', err)
  } finally {
    togglingRelay.value = false
  }
}

// Quick toggle generator (from top bar)
async function handleQuickToggle() {
  if (generatorStore.isRunning) {
    showStopConfirm.value = true
  } else {
    showStartModal.value = true
  }
}

// Handle stop button click
function handleStop() {
  showStopConfirm.value = true
}

// Handle emergency stop button click
function handleEmergencyStop() {
  showEmergencyConfirm.value = true
}

// Execute start
async function executeStart() {
  showStartModal.value = false
  const duration = selectedRunType.value === 'timed' ? timedDuration.value : null
  await generatorStore.start(duration, 'manual')
  await generatorStore.fetchState()
}

// Execute stop
async function executeStop() {
  showStopConfirm.value = false
  await generatorStore.stop('manual')
}

// Execute emergency stop
async function executeEmergencyStop() {
  showEmergencyConfirm.value = false
  emergencyStopLoading.value = true
  try {
    await generatorStore.emergencyStop()
  } catch (err) {
    console.error('Emergency stop failed:', err)
  } finally {
    emergencyStopLoading.value = false
  }
}

// Execute fuel reset
async function executeFuelReset() {
  showFuelResetConfirm.value = false
  try {
    await generatorApi.resetFuelTracking()
    totalFuelUsed.value = 0
    fuelResetTimestamp.value = Math.floor(Date.now() / 1000)
    notificationStore.success('Fuel tracking reset')
  } catch (err) {
    console.error('Failed to reset fuel tracking:', err)
    notificationStore.error('Failed to reset fuel tracking')
  }
}

// Fetch fuel usage
async function fetchFuelUsage() {
  try {
    const response = await generatorApi.getFuelUsage()
    totalFuelUsed.value = response.data?.total_fuel_used || 0
    fuelResetTimestamp.value = response.data?.reset_timestamp || 0
  } catch (err) {
    console.error('Failed to fetch fuel usage:', err)
  }
}

// Fetch generator info for fuel calculation
async function fetchGeneratorInfo() {
  try {
    const { generatorInfoApi } = await import('@/services/api')
    const response = await generatorInfoApi.get()
    if (response.data) {
      generatorInfo.value = {
        fuel_consumption_50: response.data.fuel_consumption_50 || 0,
        fuel_consumption_100: response.data.fuel_consumption_100 || 0,
        load_expected: response.data.load_expected || 50,
      }
    }
  } catch (err) {
    console.error('Failed to fetch generator info:', err)
  }
}

// Handle override toggle
async function handleOverrideToggle(enabled) {
  try {
    if (enabled) {
      await configService.enableOverride()
    } else {
      await configService.disableOverride()
    }
  } catch {
    overrideEnabled.value = !enabled
  }
}

// Save run time configuration
async function saveRunTimeConfig() {
  // Validate max > min
  if (runTimeConfig.value.max_run_minutes <= runTimeConfig.value.min_run_minutes) {
    notificationStore.error('Maximum run time must be greater than minimum run time')
    return
  }

  savingRunTimeConfig.value = true
  try {
    await configApi.update({
      runtime_limits_enabled: runTimeConfig.value.runtime_limits_enabled,
      min_run_minutes: runTimeConfig.value.min_run_minutes,
      max_run_minutes: runTimeConfig.value.max_run_minutes,
      max_runtime_action: runTimeConfig.value.max_runtime_action,
      cooldown_duration_minutes: runTimeConfig.value.cooldown_duration_minutes,
    })
    notificationStore.success('Run time settings saved')
    // Refresh runtime limits status in case lockout/cooldown was cleared
    await fetchRuntimeLimitsStatus()
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to save run time settings'
    notificationStore.error(message)
  } finally {
    savingRunTimeConfig.value = false
  }
}

// Fetch runtime limits status
async function fetchRuntimeLimitsStatus() {
  try {
    const response = await generatorApi.getRuntimeLimitsStatus()
    if (response.data) {
      runtimeLimitsStatus.value = response.data
    }
  } catch (err) {
    console.error('Failed to fetch runtime limits status:', err)
  }
}

// Handle clear lockout
async function handleClearLockout() {
  clearingLockout.value = true
  try {
    await generatorApi.clearLockout(true)
    notificationStore.success('Runtime lockout cleared')
    await fetchRuntimeLimitsStatus()
  } catch (err) {
    const message = err.response?.data?.detail || 'Failed to clear lockout'
    notificationStore.error(message)
  } finally {
    clearingLockout.value = false
  }
}

// Format cooldown remaining time
function formatCooldownRemaining(seconds) {
  if (!seconds || seconds <= 0) return '0m'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

// Watch for generator running state changes
watch(() => generatorStore.isRunning, (isRunning) => {
  if (isRunning) {
    syncRuntimeFromStore()
    updateRuntimeTimer()
  } else {
    if (runtimeInterval) {
      clearInterval(runtimeInterval)
      runtimeInterval = null
    }
    localRunTimeSeconds.value = 0
    // Refresh fuel usage when generator stops
    fetchFuelUsage()
  }
})

// Lifecycle
onMounted(async () => {
  // Fetch relay state and generator state immediately
  fetchRelayState()
  generatorStore.fetchState()

  try {
    await Promise.all([
      generatorStore.fetchStats(),
      systemStore.fetchHealth(),
      systemStore.fetchSlaveHealth(),
      systemStore.fetchVictronStatus(),
      fetchFuelUsage(),
      fetchGeneratorInfo(),
    ])
    stats.value = generatorStore.stats

    // Initialize runtime timer if generator is already running
    updateRuntimeTimer()
  } catch (err) {
    console.error('Failed to load data:', err)
  } finally {
    loading.value = false
  }

  // Load override state
  try {
    const override = await configService.getOverride()
    overrideEnabled.value = override.enabled
  } catch {
    // Ignore errors
  }

  // Load run time config
  try {
    const configRes = await configApi.get()
    if (configRes.data) {
      runTimeConfig.value.runtime_limits_enabled = configRes.data.runtime_limits_enabled || false
      runTimeConfig.value.min_run_minutes = configRes.data.min_run_minutes || 5
      runTimeConfig.value.max_run_minutes = configRes.data.max_run_minutes || 480
      runTimeConfig.value.max_runtime_action = configRes.data.max_runtime_action || 'manual_reset'
      runTimeConfig.value.cooldown_duration_minutes = configRes.data.cooldown_duration_minutes || 60
    }
  } catch {
    // Use defaults
  }

  // Load runtime limits status (lockout/cooldown state)
  await fetchRuntimeLimitsStatus()

  // Refresh every 60 seconds
  refreshInterval = setInterval(async () => {
    await Promise.all([
      systemStore.fetchHealth(),
      systemStore.fetchSlaveHealth(),
      systemStore.fetchVictronStatus(),
      fetchRelayState(),
      fetchFuelUsage(),
      fetchRuntimeLimitsStatus(),
    ])
  }, 60000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (runtimeInterval) {
    clearInterval(runtimeInterval)
  }
})
</script>

<style scoped>
/* Slow spin animation for generator cog when running */
@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}
</style>
