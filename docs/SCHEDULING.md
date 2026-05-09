# Scheduling Guide

This guide covers how to set up automated and exercise generator runs.

## Table of Contents

- [Overview](#overview)
- [Scheduled Runs](#scheduled-runs)
- [Exercise Runs](#exercise-runs)
- [How Scheduling Works](#how-scheduling-works)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)

---

## Overview

The RPi Generator Control system supports two types of automated runs:

| Type | Purpose | Typical Use Case |
|------|---------|------------------|
| **Scheduled Runs** | Run generator at specific times | Preemptive charging before expected demand |
| **Exercise Runs** | Regular maintenance runs | Keep generator healthy, prevent fuel degradation |

Both types:
- Require the relay to be **armed** before they'll execute
- Create full run records with history and fuel tracking
- Support **auto-stop** after a configured duration
- Can be configured via the web UI or API

---

## Scheduled Runs

Scheduled runs let you define recurring generator runs at specific times on specific days.

### Creating a Schedule

**Via Web UI:**

1. Navigate to **Settings > Schedules**
2. Click **Add Schedule**
3. Configure:
   - **Name**: A descriptive name (e.g., "Morning Pre-Charge")
   - **Start Time**: When to start (HH:MM format, 24-hour)
   - **Duration**: How long to run (minutes)
   - **Days**: Which days of the week
   - **Enabled**: Toggle on/off without deleting

**Via API:**
```bash
curl -X POST https://your-genmaster/api/schedule \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Pre-Charge",
    "start_time": "06:30",
    "duration_minutes": 60,
    "days_of_week": [1, 2, 3, 4, 5],
    "enabled": true
  }'
```

### Days of Week Format

Days are specified as an array of integers:

| Value | Day |
|-------|-----|
| 0 | Sunday |
| 1 | Monday |
| 2 | Tuesday |
| 3 | Wednesday |
| 4 | Thursday |
| 5 | Friday |
| 6 | Saturday |

**Examples:**
- Weekdays only: `[1, 2, 3, 4, 5]`
- Weekends only: `[0, 6]`
- Every day: `[0, 1, 2, 3, 4, 5, 6]`
- Mon/Wed/Fri: `[1, 3, 5]`

### Managing Schedules

**List all schedules:**
```bash
curl https://your-genmaster/api/schedule \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Update a schedule:**
```bash
curl -X PUT https://your-genmaster/api/schedule/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_minutes": 90,
    "enabled": false
  }'
```

**Delete a schedule:**
```bash
curl -X DELETE https://your-genmaster/api/schedule/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Schedule Execution

When a schedule triggers:

1. System checks if relay is **armed**
2. System checks if generator is **not already running**
3. If checks pass, generator starts with trigger type `scheduled`
4. Auto-stop is scheduled for the configured duration
5. Schedule tracking is updated (last_executed, next_execution, execution_count)

If the relay is not armed or generator is already running, the schedule is skipped and will try again at the next scheduled time.

---

## Exercise Runs

Exercise runs are designed for generator maintenance - running the generator periodically to:

- Prevent fuel degradation (especially important for stored diesel/gasoline)
- Keep engine components lubricated
- Verify the generator is ready when needed
- Charge the starter battery

### Configuring Exercise

**Via Web UI:**

1. Navigate to **Settings > Generator Info**
2. Find the **Exercise Schedule** section
3. Configure:
   - **Enabled**: Toggle exercise runs on/off
   - **Frequency**: How often (in days)
   - **Start Time**: When to run (HH:MM, 24-hour)
   - **Duration**: How long to run (minutes)

**Via API:**
```bash
curl -X PATCH https://your-genmaster/api/exercise \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency_days": 14,
    "start_time": "10:00",
    "duration_minutes": 30
  }'
```

### Recommended Settings

| Generator Type | Frequency | Duration |
|---------------|-----------|----------|
| Standby (Natural Gas) | 7-14 days | 15-30 minutes |
| Standby (Propane/LPG) | 14-30 days | 20-30 minutes |
| Portable (Gasoline) | 7 days | 15-20 minutes |
| Diesel | 14-30 days | 30-60 minutes |

> **Note:** Consult your generator's manual for manufacturer recommendations.

### Exercise Tracking

The system tracks:

| Field | Description |
|-------|-------------|
| `last_exercise_date` | When the last exercise ran |
| `next_exercise_date` | When the next exercise is scheduled |

After each exercise:
- `last_exercise_date` is updated to today
- `next_exercise_date` is recalculated (today + frequency_days)

### Manual Exercise

You can trigger an exercise run immediately:

**Via Web UI:**
1. Navigate to **Settings > Generator Info**
2. Click **Run Exercise Now**

**Via API:**
```bash
curl -X POST https://your-genmaster/api/exercise/run-now \
  -H "Authorization: Bearer YOUR_TOKEN"
```

This will:
- Start the generator with trigger type `exercise`
- Use the configured exercise duration for auto-stop
- Update exercise tracking (last/next dates)

---

## How Scheduling Works

### APScheduler Backend

Schedules are managed using [APScheduler](https://apscheduler.readthedocs.io/) (AsyncIOScheduler), which provides:

- Reliable cron-like scheduling
- Persistent across container restarts (schedules are stored in PostgreSQL)
- Timezone-aware execution

### Schedule Loading

On startup:
1. Scheduler service initializes
2. All enabled schedules are loaded from the database
3. Each schedule is added as an APScheduler job with a CronTrigger
4. Exercise scheduler background task starts (checks every minute)

### Auto-Stop

When a scheduled/exercise run starts, an auto-stop is scheduled:

1. **DateTrigger** is created for `now + duration_minutes`
2. Job is added to APScheduler
3. When triggered, generator stops with reason `scheduled_end` or `exercise_end`
4. If generator is manually stopped before auto-stop, the job is cancelled

### Runtime Limits Integration

If runtime limits are enabled:
- Scheduled runs respect `max_run_minutes` (will stop early if exceeded)
- Lockout can prevent scheduled runs from starting
- Cooldown period applies between runs

---

## API Reference

### Scheduled Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/schedule` | List all schedules |
| POST | `/api/schedule` | Create a schedule |
| GET | `/api/schedule/{id}` | Get a specific schedule |
| PUT | `/api/schedule/{id}` | Update a schedule |
| DELETE | `/api/schedule/{id}` | Delete a schedule |

### Exercise

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/exercise` | Get exercise configuration |
| PATCH | `/api/exercise` | Update exercise configuration |
| POST | `/api/exercise/run-now` | Trigger immediate exercise |

### Request/Response Examples

**Create Schedule Request:**
```json
{
  "name": "Weekend Evening Run",
  "start_time": "18:00",
  "duration_minutes": 120,
  "days_of_week": [0, 6],
  "enabled": true
}
```

**Schedule Response:**
```json
{
  "id": 1,
  "name": "Weekend Evening Run",
  "start_time": "18:00",
  "duration_minutes": 120,
  "days_of_week": [0, 6],
  "enabled": true,
  "last_executed": 1714567890,
  "next_execution": 1714654290,
  "execution_count": 5,
  "created_at": "2026-01-15T10:30:00",
  "updated_at": "2026-04-01T18:00:00"
}
```

**Exercise Configuration Response:**
```json
{
  "enabled": true,
  "frequency_days": 14,
  "start_time": "10:00",
  "duration_minutes": 30,
  "last_exercise_date": "2026-04-15",
  "next_exercise_date": "2026-04-29",
  "updated_at": "2026-04-15T10:32:00"
}
```

---

## Best Practices

### 1. Coordinate with Victron

If you're using Victron automatic triggering, schedule runs during times when:
- Battery is typically above the trigger threshold
- Solar production is minimal (evening/night/early morning)
- Grid outages are less likely

This prevents conflicts where both Victron and schedule try to control the generator.

### 2. Consider Runtime Limits

Set your schedule durations to be less than `max_run_minutes` if runtime limits are enabled. This prevents unexpected lockouts.

### 3. Stagger Multiple Schedules

If you have multiple schedules, ensure they don't overlap:

```
Schedule A: 06:00-08:00 (2 hours)
Schedule B: 10:00-11:00 (1 hour)  ← Good: 2-hour gap
```

### 4. Exercise Timing

Schedule exercise runs for:
- Times when you're available to respond if issues occur
- Not during peak solar production (wastes solar energy)
- Not during expected power outages

### 5. Monitor Execution

Check the run history regularly to verify schedules are executing:

```bash
curl "https://your-genmaster/api/generator/history?trigger_type=scheduled" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Arm Before Expected Runs

Scheduled runs require the relay to be armed. If you regularly disarm for maintenance:
- Set a calendar reminder to re-arm before scheduled runs
- Consider using `AUTO_ARM_RELAY_ON_CONNECT=true` for automatic re-arming

---

## Troubleshooting

### Schedule Not Executing

1. **Check if armed**: Schedules require armed relay
2. **Check if enabled**: Verify schedule is enabled in UI/API
3. **Check time zone**: Ensure server time matches expected schedule time
4. **Check for conflicts**: Generator already running will block schedule
5. **Check logs**: `docker compose logs genmaster | grep -i schedule`

### Exercise Not Running

1. **Check if enabled**: Exercise must be enabled
2. **Check `next_exercise_date`**: If in the future, exercise won't run
3. **Check relay armed**: Same as scheduled runs
4. **Force immediate run**: Use **Run Exercise Now** to test

### Auto-Stop Not Working

1. **Check duration**: Verify duration is set correctly
2. **Check logs**: Look for auto-stop scheduling messages
3. **Manual stops**: If you manually stopped, auto-stop is cancelled

---

## Next Steps

- [Generator Controls](GENERATOR.md) - Manual start/stop and arming
- [Notifications](NOTIFICATIONS.md) - Get alerts for scheduled runs
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
