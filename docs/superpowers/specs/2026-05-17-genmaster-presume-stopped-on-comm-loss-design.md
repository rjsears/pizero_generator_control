# GenMaster — Show Generator Stopped When GenSlave Comms Lost

**Status:** Approved (simplified scope), ready for implementation plan
**Date:** 2026-05-17
**Scope:** GenMaster only — no GenSlave changes, no DB schema changes, no
new notifications, no run-record manipulation

## Problem

When GenSlave loses communication with GenMaster, GenSlave's failsafe
correctly kills the generator (relay OFF, disarm) after ~90–95 seconds of
no heartbeats. But GenMaster's API continues to report
`generator_running = true` because nothing in GenMaster reconciles the
display state with the loss of confirmation from GenSlave. The operator
sees "running" in the UI even though the generator has actually stopped.

## Goal

When GenSlave is offline, GenMaster should display the generator as
**not running**. When comms come back, normal operations resume via the
existing heartbeat-driven self-heal — no special recovery logic needed
because the relay state syncs to GenMaster's `state.generator_running`
on the next heartbeat.

## Non-goals (explicit)

These were considered and dropped per operator preference. They are
**not** part of this change:

- No closing of the active `GeneratorRun` record during the outage.
- No manipulation of `state.generator_running`, `state.current_run_id`,
  `state.run_trigger`, or `state.slave_relay_armed` during the outage.
- No new notification events.
- No guards added to `start_generator()` or `stop_generator()`.
- No DB schema migrations.
- No new event-log entry type.
- No frontend banner additions (existing offline indicators on the
  GenSlave-disconnected state remain as-is).

The reasoning: minimal blast radius. The operator's intent (armed,
running) is preserved in the DB across the outage, so the existing
heartbeat self-heal can restore actual operation when comms return.

## Design

### Single change: override `get_generator_status()` when disconnected

In `genmaster/backend/app/services/state_machine.py`, modify
`get_generator_status()` to return `running=False` when
`state.slave_connection_status == "disconnected"`:

```python
async def get_generator_status(self) -> GeneratorStatus:
    async with AsyncSessionLocal() as db:
        state = await self._get_state(db)

        # When GenSlave is unreachable we cannot confirm the generator
        # is actually running. Display it as stopped — GenSlave's own
        # failsafe will have killed the relay by ~90s of comm loss, and
        # we have no out-of-band way to verify. When comms restore, the
        # heartbeat sync re-asserts whatever state.generator_running
        # holds in the DB, so normal operation resumes automatically.
        if state.slave_connection_status == "disconnected":
            return GeneratorStatus(
                running=False,
                start_time=None,
                runtime_seconds=None,
                trigger=state.run_trigger,
                current_run_id=state.current_run_id,
            )

        runtime = None
        if state.generator_running and state.generator_start_time:
            runtime = int(time.time()) - state.generator_start_time

        return GeneratorStatus(
            running=state.generator_running,
            start_time=state.generator_start_time,
            runtime_seconds=runtime,
            trigger=state.run_trigger,
            current_run_id=state.current_run_id,
        )
```

`trigger` and `current_run_id` are passed through unchanged so the UI
can still display "what was running before we lost comms" in a tooltip
or detail view if it chooses.

### Why this is sufficient for the recovery path

When the next successful heartbeat arrives, the existing code at
`state_machine.py:1434-1469` sets
`state.slave_connection_status = "connected"`. From that point on,
`get_generator_status()` returns the real value of
`state.generator_running`.

If the operator's intent (`state.generator_running == True`,
`state.slave_relay_armed == True`) is still in the DB when comms
restore, then on the outbound heartbeat side
(`genmaster/backend/app/services/slave_status_service.py:_send_heartbeat`)
GenMaster sends `generator_running=true` to GenSlave. GenSlave's
`failsafe.record_heartbeat` (`genslave/app/services/failsafe.py:115-146`)
then:

1. Self-heals: re-arms because `genmaster_armed=true` but local
   `is_armed=false` (the failsafe disarmed it).
2. Syncs relay: sees `genmaster_running=true` but local `relay=false`,
   turns the relay ON.

Generator restarts. UI starts showing running again on the next status
fetch. No GenMaster-side recovery code needed.

### UI surface

The frontend already reads:
- `slave_connection_status` — drives the existing "GenSlave Offline"
  indicator in the system header.
- `generator_running` — drives the running/stopped display on the
  Generator page.
- `victron_signal_state` — drives the Victron input badge,
  independently of GenSlave state.

**Small addition** to the generator status box in `GeneratorView.vue`:
when the generator is displayed as stopped AND
`slave_connection_status === 'disconnected'`, show a short note inside
the box reading **"Lost communication with GenSlave"** so the operator
immediately understands why the display flipped to stopped.

The note clears automatically when comms restore (the disconnected
condition no longer holds).

With this single backend change + the small frontend note, the operator
sees:

- "GenSlave Offline" (existing system-header indicator)
- "Generator: Stopped — Lost communication with GenSlave" (new)
- "Victron: Active" or "Victron: Idle" — whatever it actually is

## Edge cases

1. **Brief outage (< 90s, failsafe didn't fire)**: UI shows stopped
   during the outage. On reconnect, `state.generator_running` is still
   True in the DB, GenSlave reports relay still ON, heartbeat confirms.
   UI flips back to running. No state lost.
2. **Outage past failsafe window**: UI shows stopped. On reconnect,
   self-heal re-energizes the relay (if armed and Victron-or-equivalent
   still calling). UI flips back to running.
3. **Victron drops during the outage**: `handle_victron_signal_change`
   fires `stop_generator("victron")`. The relay-off command to GenSlave
   fails silently (offline), but `state.generator_running = False` is
   committed to the DB. After reconnect, heartbeat tells GenSlave to
   stop. Run record gets a proper `stop_time` via the normal
   `stop_generator` path.
4. **GenSlave never returns**: UI stays "GenSlave Offline + Generator
   Stopped" until the operator intervenes. The DB retains the
   pre-outage state, ready to resume if comms ever come back.
5. **Operator clicks Stop during outage**: existing `stop_generator()`
   path runs — DB updated to not-running, relay command to GenSlave
   fails silently. UI shows stopped (same as before, just for a
   different reason now).
6. **Operator clicks Start during outage**: existing `start_generator()`
   path runs — it'll fail when trying to talk to GenSlave (3s HTTP
   timeout, then error). Out of scope to make this fail faster;
   operator will see the error.

## Known caveat (accepted)

If the GenSlave failsafe killed the generator but the operator never
manually intervened and comms never returned, the `GeneratorRun` record
stays open (no `stop_time`). Statistics that sum durations over open
runs may briefly misbehave. This matches pre-existing behavior for
permanently lost GenSlave and is not made worse by this change. A
future cleanup pass could close orphaned runs on long-term offline,
but that is out of scope here.

## Test plan (manual)

No automated tests are introduced (project does not currently maintain
a pytest suite for `genmaster/backend`).

Manual verification:

1. Start a generator run (manual or Victron-triggered). Confirm UI
   shows "Running".
2. Stop the `genslave` container on the GenSlave Pi
   (`docker stop genslave`).
3. Wait until `slave_connection_status` transitions to "disconnected"
   in the GenMaster UI (~90s with default settings).
4. Confirm the Generator page now shows "Stopped" while the existing
   GenSlave offline indicator is also showing.
5. Confirm the Victron badge still shows its actual signal state.
6. Restart `genslave` container (`docker start genslave`).
7. Confirm comms come back, UI returns to showing the real generator
   state, and if Victron was still calling for run, the generator
   restarts automatically within a heartbeat or two.

## Files affected

- `genmaster/backend/app/services/state_machine.py` — one method
  modified: `get_generator_status()`.
- `genmaster/frontend/src/views/GeneratorView.vue` — one small
  conditional note inside the generator status box.

That is the entire surface area of this change.

## Out of scope (deferred)

- Run-record cleanup for orphaned open runs on extended GenSlave
  outages.
- Pi-hung detection on the GenSlave side (separate failure mode
  requiring a hardware watchdog).
- Faster manual-start failure during disconnection (currently relies on
  3s HTTP timeout).
