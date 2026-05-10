# Generator Control Guide

This guide covers how to start, stop, and monitor your generator using the RPi Generator Control system.

## Table of Contents

- [Overview](#overview)
- [Understanding Generator States](#understanding-generator-states)
- [Arming the System](#arming-the-system)
- [Starting the Generator](#starting-the-generator)
- [Stopping the Generator](#stopping-the-generator)
- [Override System](#override-system)
- [Runtime Limits](#runtime-limits)
- [Fuel Tracking](#fuel-tracking)
- [Run History](#run-history)
- [API Reference](#api-reference)

---

## Overview

The generator control system uses a **master-slave architecture** where GenMaster coordinates all operations and GenSlave physically controls the relay connected to your generator's two-wire start input.

### Key Principles

1. **GenMaster is the source of truth** - The PostgreSQL database on GenMaster maintains the authoritative state of whether the generator should be running.

2. **Heartbeat synchronization** - GenMaster sends heartbeats to GenSlave every 10 seconds. If GenSlave's relay state doesn't match GenMaster's intended state, the heartbeat corrects it.

3. **Safety first** - The system defaults to a safe state:
   - Relay is **disarmed** on every GenMaster boot under the default `fail_safe` policy (operator must re-arm — see [Boot Arming Policy](#boot-arming-policy))
   - Generator can always be **stopped** even when disarmed
   - GenSlave has an independent **failsafe** that stops the generator if communication is lost

---

## Understanding Generator States

The state machine tracks the generator through several states:

### Generator Running States

| State | Description |
|-------|-------------|
| `idle` | Generator is off, system is waiting |
| `running` | Generator is actively running |

### Trigger Types

When the generator starts, the system records what triggered it:

| Trigger | Description |
|---------|-------------|
| `victron` | Started automatically by Victron Cerbo GX signal (low battery) |
| `manual` | Started manually via web UI or API |
| `scheduled` | Started by a scheduled run |
| `exercise` | Started by an exercise schedule for maintenance |

### Stop Reasons

When the generator stops, the system records why:

| Reason | Description |
|--------|-------------|
| `victron` | Victron signal went inactive (battery charged) |
| `manual` | Stopped manually via web UI or API |
| `scheduled_end` | Scheduled run duration completed |
| `exercise_end` | Exercise run completed |
| `comm_loss` | GenSlave lost communication with GenMaster |
| `override` | Force-stop override activated |
| `error` | An error occurred |
| `max_runtime` | Maximum runtime limit exceeded |

---

## Arming the System

The **arming system** is a safety feature that prevents accidental generator starts.

### Why Arming?

- **Prevents unintended starts** during maintenance
- **Requires explicit operator action** to enable automation
- **Disarmed by default** on system boot under the `fail_safe` boot policy (see [Boot Arming Policy](#boot-arming-policy) below for the alternative `preserve_state` mode)

### Arming Behavior

| State | Can Start (Auto) | Can Start (Manual) | Can Stop |
|-------|------------------|-------------------|----------|
| **Disarmed** | No | No | Yes |
| **Armed** | Yes | Yes | Yes |

> **Note:** The generator can always be stopped for safety, regardless of arm state.

### How to Arm

**Via Web UI:**
1. Navigate to the Generator dashboard
2. Click the **Arm** button in the control panel
3. The status indicator will change to show "Armed"

**Via API:**
```bash
# Arm the relay
curl -X POST https://your-genmaster/api/generator/arm \
  -H "Authorization: Bearer YOUR_TOKEN"

# Disarm the relay
curl -X POST https://your-genmaster/api/generator/disarm \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Auto-Arm on Connection Restore

If enabled via `AUTO_ARM_RELAY_ON_CONNECT=true`, the system will automatically arm the relay when GenSlave connection is restored after an outage. This feature respects manual disarms:

- If you manually disarmed via the UI, auto-arm will **not** override your choice
- If you manually arm via the UI, the "manual disarm" flag is cleared
- Auto-arm only triggers when connection is restored, not on every heartbeat

### Boot Arming Policy

Operator-selectable behavior for what happens to the relay's armed state when GenMaster restarts. Configure in **Generator → Boot Arming Policy** in the UI, or via the `BOOT_ARMING_POLICY` env var.

| Policy | Behavior on GenMaster boot | When to use |
|--------|---------------------------|-------------|
| `fail_safe` (default) | If the relay was armed pre-boot, **disarms it** and sets `manual_disarm_active = True` so boot-time auto-arm is suppressed. Fires the `boot_disarmed_failsafe` notification so the operator knows they need to re-arm. | Default for safety. Required when unsupervised auto-restart after a power event would be unsafe or undesirable. |
| `preserve_state` | Keeps the prior `slave_relay_armed` value across the reboot. Combined with auto-arm, the system can resume operation automatically after an outage. | Only when your installation can safely auto-resume (proper ATS, weatherproofing, fuel/CO safety). Requires confirming a UI warning before enabling. |

**Independence from runtime auto-arm:** The `boot_arming_policy` only affects the **boot path**. Runtime auto-arm-on-connect (when GenSlave drops out and reconnects during normal operation) still works exactly as configured by `auto_arm_relay_on_connect` regardless of the boot policy.

**Notification on disarm:** When the `fail_safe` policy disarms the relay, GenMaster fires the `boot_disarmed_failsafe` notification event. Configure the channels/groups that receive it under **Notifications → Configure → Generator Events**. Default message text reads:

> Generator Disarmed After Reboot — Action Required
>
> GenMaster restarted with the fail-safe boot policy enabled. The generator relay has been automatically DISARMED for safety. The generator WILL NOT START automatically until you log in and re-arm it from the web interface.

---

## Starting the Generator

### Automatic Start (Victron)

When Victron sends a "generator needed" signal (GPIO17 goes HIGH):

1. System checks if relay is **armed**
2. System checks for active **override** (force_stop blocks auto-start)
3. System checks for **runtime lockout** or **cooldown**
4. If all checks pass, generator starts

### Manual Start

**Via Web UI:**
1. Ensure the system is **armed**
2. Click **Start Generator**
3. Optionally set a duration for auto-stop
4. Confirm the action

**Via API:**
```bash
curl -X POST https://your-genmaster/api/generator/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 60, "notes": "Testing"}'
```

### What Happens on Start

1. **Database updated first** - GenMaster sets `generator_running = true`
2. **Relay command sent** - GenMaster tells GenSlave to turn relay ON
3. **Run record created** - Start time, trigger type, and fuel info logged
4. **Webhooks fired** - `generator.started.{trigger}` event sent
5. **Notifications sent** - If configured, push notification goes out

Even if the relay command fails (network issue), the next heartbeat will synchronize GenSlave with GenMaster's state.

---

## Stopping the Generator

### Automatic Stop (Victron)

When the Victron signal goes LOW (battery charged):
- System checks if the current run was triggered by Victron
- If yes, generator stops automatically
- If run was manual/scheduled, Victron signal is ignored

### Manual Stop

**Via Web UI:**
Click **Stop Generator** - works even when disarmed.

**Via API:**
```bash
curl -X POST https://your-genmaster/api/generator/stop \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Maintenance needed"}'
```

### What Happens on Stop

1. **Database updated first** - GenMaster sets `generator_running = false`
2. **Relay command sent** - GenMaster tells GenSlave to turn relay OFF
3. **Run record completed** - Stop time, duration, fuel usage calculated
4. **Auto-stop jobs cancelled** - Any scheduled auto-stop is removed
5. **Webhooks fired** - `generator.stopped.{reason}` event sent
6. **Notifications sent** - Runtime and fuel usage included in notification

---

## Override System

Overrides let you force the generator into a specific state, ignoring normal triggers.

### Override Types

| Type | Effect |
|------|--------|
| `force_run` | Keeps generator running, ignores Victron "stop" signal |
| `force_stop` | Keeps generator stopped, blocks automatic Victron starts |

### Important Notes

- **force_stop** only blocks **automatic** (Victron) starts
- Manual and scheduled starts still work with force_stop active
- Overrides persist until explicitly disabled

### Using Overrides

**Via Web UI:**
1. Navigate to Generator dashboard
2. Toggle the **Override** switch
3. Select override type (Force Run or Force Stop)

**Via API:**
```bash
# Enable force_run override
curl -X POST https://your-genmaster/api/override/enable \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"override_type": "force_run"}'

# Disable override
curl -X POST https://your-genmaster/api/override/disable \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Runtime Limits

Protect your generator from excessive runtime with configurable limits.

### Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `runtime_limits_enabled` | Enable/disable the feature | `false` |
| `max_run_minutes` | Maximum continuous runtime | `480` (8 hours) |
| `cooldown_minutes` | Required rest after max runtime | `60` |
| `lockout_on_max_runtime` | Require acknowledgment after max | `true` |

### How It Works

1. When generator reaches `max_run_minutes`, it automatically stops
2. Stop reason is recorded as `max_runtime`
3. If `lockout_on_max_runtime` is enabled:
   - A **lockout** is activated
   - Generator cannot restart until operator **acknowledges** the event
4. If only cooldown is active:
   - Generator waits `cooldown_minutes` before allowing restart
   - Manual starts bypass cooldown

### Clearing Lockout

**Via Web UI:**
1. A banner appears indicating max runtime was reached
2. Click **Acknowledge & Clear Lockout**

**Via API:**
```bash
curl -X POST https://your-genmaster/api/generator/clear-lockout \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"acknowledge": true}'
```

---

## Fuel Tracking

The system tracks estimated fuel consumption for each run.

### Configuration

Set these in **Settings > Generator Info**:

| Field | Description |
|-------|-------------|
| Fuel Type | `lpg` (Propane), `natural_gas`, or `diesel` |
| Expected Load | `50` or `100` percent |
| Consumption @ 50% | Gallons per hour at 50% load |
| Consumption @ 100% | Gallons per hour at 100% load |

### How It's Calculated

```
estimated_fuel_used = (runtime_seconds / 3600) × fuel_consumption_rate
```

The consumption rate used is based on the expected load setting at the time the run started.

### Viewing Fuel Usage

**Via Web UI:**
- Dashboard shows total fuel used since last reset
- Each run in history shows individual fuel consumption

**Via API:**
```bash
# Get fuel usage
curl https://your-genmaster/api/generator/fuel-usage \
  -H "Authorization: Bearer YOUR_TOKEN"

# Reset fuel tracking (e.g., after refueling)
curl -X POST https://your-genmaster/api/generator/fuel-usage/reset \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Run History

Every generator run is logged with detailed information.

### What's Recorded

| Field | Description |
|-------|-------------|
| `start_time` | Unix timestamp when started |
| `stop_time` | Unix timestamp when stopped |
| `duration_seconds` | Total runtime |
| `trigger_type` | What started it (victron/manual/scheduled/exercise) |
| `stop_reason` | Why it stopped |
| `notes` | Optional user notes |
| `fuel_type_at_run` | Fuel type when run started |
| `load_at_run` | Load setting when run started |
| `estimated_fuel_used` | Calculated fuel consumption |

### Viewing History

**Via Web UI:**
Navigate to **Generator > History** to see all runs with filtering options.

**Via API:**
```bash
# Get last 50 runs
curl "https://your-genmaster/api/generator/history?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by trigger type
curl "https://your-genmaster/api/generator/history?trigger_type=victron" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Statistics

Get aggregate statistics for a time period:

```bash
# Last 30 days (default)
curl "https://your-genmaster/api/generator/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Last 90 days
curl "https://your-genmaster/api/generator/stats?days=90" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Returns:
- Total runs
- Total runtime (hours)
- Average runtime per run
- Breakdown by trigger type

---

## API Reference

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/generator/state` | Get current generator status |
| POST | `/api/generator/start` | Start the generator |
| POST | `/api/generator/stop` | Stop the generator |
| POST | `/api/generator/arm` | Arm the relay |
| POST | `/api/generator/disarm` | Disarm the relay |
| GET | `/api/generator/history` | Get run history |
| GET | `/api/generator/stats` | Get runtime statistics |
| GET | `/api/generator/fuel-usage` | Get fuel usage since reset |
| POST | `/api/generator/fuel-usage/reset` | Reset fuel tracking |
| GET | `/api/generator/runtime-limits` | Get runtime limits status |
| POST | `/api/generator/clear-lockout` | Clear runtime lockout |
| POST | `/api/override/enable` | Enable override |
| POST | `/api/override/disable` | Disable override |
| GET | `/api/override/status` | Get override status |

### Response Examples

**GET /api/generator/state**
```json
{
  "running": true,
  "state": "running",
  "current_run_id": 42,
  "start_time": 1714567890,
  "runtime_seconds": 3600,
  "trigger": "victron",
  "armed": true,
  "slave_connected": true
}
```

**GET /api/generator/stats**
```json
{
  "period_days": 30,
  "total_runs": 15,
  "total_runtime_seconds": 54000,
  "total_runtime_hours": 15.0,
  "average_runtime_seconds": 3600,
  "runs_by_trigger": {
    "victron": 10,
    "manual": 3,
    "scheduled": 2
  },
  "runtime_by_trigger": {
    "victron": 36000,
    "manual": 10800,
    "scheduled": 7200
  }
}
```

---

## Safety Features Summary

| Feature | Purpose |
|---------|---------|
| **Arming** | Prevents accidental starts, requires explicit operator action |
| **Heartbeat Sync** | Ensures GenSlave always matches GenMaster's intended state |
| **GenSlave Failsafe** | Independent watchdog stops generator if communication lost |
| **Runtime Limits** | Prevents generator damage from excessive continuous operation |
| **Lockout System** | Requires human acknowledgment after max runtime events |
| **Override Safety** | force_stop still allows manual intervention |
| **Relay OFF Always Works** | Can always stop generator regardless of arm state |

---

## Next Steps

- [Scheduling Guide](SCHEDULING.md) - Set up automated and exercise runs
- [Victron Integration](VICTRON.md) - Configure GPIO signal monitoring
- [Notifications](NOTIFICATIONS.md) - Set up alerts for generator events
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
