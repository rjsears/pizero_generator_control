    # GenMaster — Show Generator Stopped When GenSlave Comms Lost — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When GenSlave is unreachable, GenMaster's API and UI display the generator as stopped (with a clear note explaining why). When comms restore, existing heartbeat self-heal returns operation to normal automatically — no extra recovery code needed.

**Architecture:** Two targeted changes. (1) Override the API `get_generator_status()` to return `running=False` when `slave_connection_status == "disconnected"`. (2) Add a small conditional note inside the generator status card in `GeneratorView.vue` that reads "Lost communication with GenSlave" when the generator is shown stopped because GenSlave is offline. No DB writes during the outage. No new notifications. No new migrations. No GenSlave changes.

**Tech Stack:** Python (FastAPI, SQLAlchemy async, Pydantic v2) on the backend. Vue 3 + Pinia + Tailwind on the frontend. Docker Compose for deployment.

**Note on commits:** Per project policy, this plan does **not** run `git add` / `git commit` / `git push`. Commit points are noted as user actions — review the diff and commit when you're satisfied.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `genmaster/backend/app/services/state_machine.py` | Single source of truth for generator state + API surface for status getters | Modify `get_generator_status()` to short-circuit to `running=False` when GenSlave is disconnected |
| `genmaster/frontend/src/views/GeneratorView.vue` | Generator page UI — status card, controls, banners | Add one conditional `<p>` inside the status card that shows "Lost communication with GenSlave" when stopped + slave offline |

That is the entire surface area. No new files. No DB migrations. No notification config. No GenSlave changes.

---

## Task 1: Backend — Override `get_generator_status()` when GenSlave is disconnected

**Files:**
- Modify: `genmaster/backend/app/services/state_machine.py` (around lines 1508–1523, the existing `get_generator_status()` method)

**Why this works:** The DB still holds the operator's intent (`state.generator_running`, `state.slave_relay_armed`, the open `GeneratorRun` record, etc.). We just don't *display* the generator as running while we can't confirm it. On reconnect, `slave_connection_status` flips back to `"connected"` and the method returns the real DB value. The existing heartbeat self-heal (`genslave/app/services/failsafe.py:115-146`) reconciles the relay state to match GenMaster's `generator_running`, so if the generator was killed by GenSlave's failsafe and Victron is still calling, the relay re-energizes within one heartbeat cycle.

- [ ] **Step 1: Read the current `get_generator_status()` implementation to confirm exact context**

Run:
```bash
sed -n '1508,1525p' "genmaster/backend/app/services/state_machine.py"
```

Expected: a method that returns `GeneratorStatus(running=state.generator_running, ...)` with no offline check.

- [ ] **Step 2: Replace `get_generator_status()` with the offline-aware version**

Open `genmaster/backend/app/services/state_machine.py` and find the existing method (currently around line 1508). Replace it with:

```python
    async def get_generator_status(self) -> GeneratorStatus:
        """Get current generator status.

        When GenSlave is unreachable (slave_connection_status ==
        "disconnected") we report running=False. We cannot confirm the
        generator is actually running while comms are down, and GenSlave's
        own failsafe will have killed the relay by ~90s of comm loss. The
        DB still holds the operator's intent — when comms restore, the
        existing heartbeat sync re-asserts that intent to GenSlave, so
        normal operation resumes automatically without any code here.
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

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

The `trigger` and `current_run_id` pass-through is intentional — the frontend may want to show "what was running" detail even while the running flag is False. If you prefer to clear those too during an outage, change the disconnected branch to pass `trigger="idle"` and `current_run_id=None` — but the current spec says preserve them.

- [ ] **Step 3: Quick static check (no syntax errors / no broken imports)**

Run:
```bash
cd "genmaster/backend" && python -c "from app.services.state_machine import StateMachine; print('import OK')"
```

Expected: `import OK`. If you see an import error or syntax error, fix it before proceeding.

- [ ] **Step 4: Deploy and smoke-test**

On the GenMaster Pi:

```bash
cd /root/pizero_generator_control/genmaster
docker compose pull   # only needed if you've already pushed to the image registry
docker compose up -d genmaster
docker compose logs --tail=50 genmaster
```

Expected: container starts cleanly, no exception traces in the logs related to `state_machine`.

If you're iterating locally without the registry round-trip, mount the file or rebuild the image per your normal dev loop.

- [ ] **Step 5: Manual verify the backend behavior end-to-end**

With both Pis online and the generator running:

```bash
# Confirm running=True via the API
curl -s http://<genmaster-ip>/api/generator/status | python -m json.tool
```

Expected: `"running": true`.

Then on the GenSlave Pi:
```bash
docker stop genslave
```

Wait ~90s for `slave_connection_status` to transition to `"disconnected"` (default `heartbeat_failure_threshold=3` × 30s heartbeat = ~90s).

```bash
curl -s http://<genmaster-ip>/api/generator/status | python -m json.tool
curl -s http://<genmaster-ip>/api/system/slave-health | python -m json.tool
```

Expected: `generator/status` returns `"running": false` and `slave-health` shows `connection_status: "disconnected"`.

Bring GenSlave back:
```bash
docker start genslave
```

Wait one heartbeat cycle (~30s):
```bash
curl -s http://<genmaster-ip>/api/generator/status | python -m json.tool
```

Expected: `"running"` returns to the real value (True if the underlying `state.generator_running` is still set; False if Victron dropped during the outage and the regular handler ran).

- [ ] **Step 6: Commit point (user action — do not run automatically)**

Review the diff:
```bash
git diff genmaster/backend/app/services/state_machine.py
```

When satisfied, commit yourself.

---

## Task 2: Frontend — Add "Lost communication with GenSlave" note inside the generator status card

**Files:**
- Modify: `genmaster/frontend/src/views/GeneratorView.vue` (around lines 390–429, inside the "Status Info" block of the generator status card)

**Note on data wiring:** `GeneratorView.vue` already exposes a `slaveOnline` computed at line 1564 (`const slaveOnline = computed(() => systemStore.isSlaveOnline)`). Reuse it — do not add a new store read.

- [ ] **Step 1: Locate the insertion point**

Open `genmaster/frontend/src/views/GeneratorView.vue` and find the Status Info block (currently around lines 390–429). It contains the "Generator Status" label and the big `generatorStateText` line. The insertion point is immediately AFTER the closing `</p>` of `generatorStateText` (currently line 395) and BEFORE the "Trigger reason, runtime, and fuel usage" wrapper div (currently line 397).

The exact spot in the existing file:

```vue
              <p class="text-3xl font-black mt-1" :class="generatorStateClass">
                {{ generatorStateText }}
              </p>

              <!-- Trigger reason, runtime, and fuel usage -->
              <div class="mt-3 flex flex-wrap gap-3">
```

- [ ] **Step 2: Insert the offline note**

Add this block between the `</p>` and the `<!-- Trigger reason... -->` comment:

```vue
              <!-- Comm-loss explainer: shows when the generator is
                   displayed as stopped because GenSlave is offline.
                   The API forces running=false during a disconnect; this
                   note tells the operator why. Clears automatically on
                   reconnect. -->
              <p
                v-if="!slaveOnline && !generatorStore.isRunning"
                class="mt-2 text-sm font-medium text-amber-700 dark:text-amber-300"
              >
                Lost communication with GenSlave
              </p>
```

The two-part condition `!slaveOnline && !generatorStore.isRunning` is deliberately redundant — the backend forces `isRunning=false` when offline, but this UI guard makes the intent explicit and is safe even if the backend behavior is ever changed.

- [ ] **Step 3: Build the frontend**

From the frontend directory:

```bash
cd genmaster/frontend
npm run build
```

Expected: build completes with no errors. If you're using the dev server during iteration, `npm run dev` and refresh the browser instead.

- [ ] **Step 4: Deploy the built bundle**

Per your normal deploy flow — either rebuild the genmaster image and `docker compose up -d genmaster`, or whatever your local dev iteration uses.

- [ ] **Step 5: Visual verify**

In the browser, with GenSlave online and the generator running:
- Generator status card shows "RUNNING" (or similar) with the green spinning icon, no offline note.

Stop GenSlave (`docker stop genslave` on the GenSlave Pi), wait ~90s for comms-lost to register:
- Generator status card shows "STOPPED" with the grey idle icon.
- The amber **"Lost communication with GenSlave"** note appears directly under the status text.
- The Victron badge elsewhere on the page still shows its actual signal state, unchanged.

Start GenSlave (`docker start genslave`), wait one heartbeat (~30s):
- The amber note disappears.
- The status card returns to showing the real generator state — running again if Victron was still calling, stopped if not.

- [ ] **Step 6: Commit point (user action — do not run automatically)**

Review:
```bash
git diff genmaster/frontend/src/views/GeneratorView.vue
```

Commit yourself when satisfied.

---

## Task 3: Full integration verification

This task has no code changes — it's a single end-to-end exercise that simulates the real incident the change was written for.

**Files:** none (verification only)

- [ ] **Step 1: Set up baseline state**

- Both Pis online, GenSlave reachable.
- Generator is running (use a manual start from the UI, or wait for a real Victron trigger).
- Confirm in the UI: "Running", trigger badge visible, runtime ticking, GenSlave online indicator green.

- [ ] **Step 2: Simulate GenSlave outage**

On the GenSlave Pi:
```bash
docker stop genslave
```

- [ ] **Step 3: Observe within the failsafe window (first ~90s)**

In the GenMaster UI:
- The system-header GenSlave online indicator should turn red/offline within ~90s (the `heartbeat_failure_threshold` × `heartbeat_interval_seconds`).
- At the same moment the generator status card flips to "STOPPED" with the amber "Lost communication with GenSlave" note.

On the GenSlave Pi side, during this window the failsafe in the (now-stopped) container can't run because we just stopped the container — that's exactly the simulated "GenSlave dead" scenario. The actual relay state is whatever the AutoHat held when the container stopped (likely still energized, generator still physically running) — but the UI correctly reflects "we don't know, presumed stopped".

- [ ] **Step 4: Bring GenSlave back**

```bash
docker start genslave
```

Within one heartbeat cycle (~30s):

- System-header GenSlave indicator returns to green.
- The amber comm-loss note disappears.
- The generator status card returns to showing the real state.
- If Victron was still calling for run during the outage: the relay re-energizes via existing heartbeat sync, and the UI flips back to "Running" automatically — no manual intervention. Watch `docker compose logs --tail=200 genmaster` for "Syncing armed state from GenMaster: re-arming" and "Heartbeat sync: turning relay ON to match GenMaster" log lines from GenSlave's side, mirrored back in GenMaster's heartbeat-response handling.

- [ ] **Step 5: Negative case — Victron drops during the outage**

Run a separate trial:
- Generator running on Victron trigger.
- Stop GenSlave (`docker stop genslave`), wait for offline indicator.
- Drop the Victron signal at the source (or unplug the input if testing physically).
- Bring GenSlave back (`docker start genslave`).

Expected: when comms restore, the normal Victron handler has already set `state.generator_running = False` during the outage (its relay-off call to GenSlave silently failed but the DB committed). On the next heartbeat, GenSlave gets `generator_running=false` and turns the relay OFF (if it isn't already). UI shows "Stopped" with no comm-loss note (because GenSlave is now online).

- [ ] **Step 6: Brief outage (< 90s) — no UI flicker expected**

Run a separate trial:
- Generator running.
- Stop GenSlave for ~60 seconds (less than the `heartbeat_failure_threshold` × `heartbeat_interval_seconds` window).
- Restart GenSlave before the offline indicator fires.

Expected: no UI change at all. `slave_connection_status` never reaches `"disconnected"`, so the override never kicks in. The comm-loss note never appears.

- [ ] **Step 7: Document any deviations**

If any of the above does not behave as described, capture:
- Exact `docker compose logs --tail=200 genmaster` output around the transition.
- `curl http://<genmaster-ip>/api/system/slave-health` snapshot at the moment of the deviation.
- Browser-console screenshots of the UI state.

Then either reopen the design discussion or file a follow-up.

---

## Self-review notes (already applied)

- Spec section 1 ("Single change: override `get_generator_status()`") → Task 1, Step 2 contains the exact replacement method body.
- Spec UI surface section ("Lost communication with GenSlave") → Task 2 contains the exact `<p>` to insert with the correct condition (`!slaveOnline && !generatorStore.isRunning`) and the precise insertion point in `GeneratorView.vue`.
- Spec "edge cases" sections 1, 2, 3, 6 → Task 3 covers them explicitly (steps 3, 4, 5, 6).
- Spec "non-goals" → reflected by the absence of tasks for run-record manipulation, new notifications, new migrations, new event types, or guards on `start_generator` / `stop_generator`.
- No placeholders, no "TBD", no "similar to Task N" — each step has the full code or command it needs.
- Type/identifier consistency: the field name `slave_connection_status` matches the column on `SystemState`; the computed `slaveOnline` matches the existing one already imported and used in `GeneratorView.vue:1564`; `generatorStore.isRunning` matches existing usage throughout the component.
