// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/config/constants.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

export const POLLING = {
  CONTAINERS: 15000,      // Container refresh rate
  DASHBOARD_METRICS: 30000, // Dashboard metrics refresh
  GENERATOR_STATUS: 5000,   // Generator status refresh
  SYSTEM_HEALTH: 60000,     // System health refresh
}

export const TIMEOUTS = {
  DEFAULT: 30000,
  LONG_RUNNING: 300000, // 5 minutes
}

export const PAGINATION = {
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
  DEFAULT_PAGE_SIZE: 10,
}

// Generator states
export const GENERATOR_STATES = {
  STOPPED: 'stopped',
  STARTING: 'starting',
  RUNNING: 'running',
  STOPPING: 'stopping',
  COOLDOWN: 'cooldown',
  ERROR: 'error',
}
