# Emergency Quick Reference

**Print this page. Laminate it. Keep one copy at the generator panel and one at the operator location.** Everything you need to know about the EPO and HOA switches in 60 seconds.

For the full operator guide see [Hardware Switches](hardware-switches.md).

---

## If something's wrong RIGHT NOW

| Situation | Do this |
|-----------|---------|
| **Generator is running and you need it OFF immediately, and you're at the generator** | Press the red EPO mushroom button. Generator stops physically. Twist clockwise to release when safe. |
| **Generator is running and you need it OFF, and you're at the operator location** | Web UI → Generator page → **Emergency Stop** (big red STOP button, top-right). |
| **You can't reach the web UI** | Press the EPO at the generator. Hardware always works, even if every Pi is offline. |
| **EPO is engaged and you don't know why** | Look at the generator. If someone is servicing it, **leave the EPO engaged**. Only release if you know nobody is at the generator. |

---

## The EPO mushroom button (at the generator)

A red push-button on the generator panel. **Press = lock the generator off. Twist clockwise = unlock.**

- The button physically opens the start-relay wire. The generator cannot start while it's pressed — not by automation, not by manual web start, not by anything.
- When the EPO is engaged: the web UI shows a pulsing red banner, the Start Generator button is greyed out, and the GenSlave LCD reads `EPO SAFETY ON`.
- When you release the EPO: automation resumes within **~60 seconds** (the heartbeat cycle). If Victron is still asking for the generator, GenMaster will start it on the next tick. There is no "rearm" step.
- **You must twist the head clockwise to release.** Pulling won't work — it's designed that way.

If the EPO won't release: it may be stuck in the cocked position. Press it once more, then twist clockwise firmly. If still stuck, the contact block has failed — call for service. The generator will remain unable to start (this is the safe failure mode).

---

## The HOA selector (at the operator location)

A 3-position rotary knob: **Quiet / Auto / Run** (counter-clockwise to clockwise).

| Position | What it does |
|----------|--------------|
| **Quiet** (CCW) | Suppresses automatic runs (Victron, scheduled, exercise). Manual web starts still work. Use overnight or when you want silence. |
| **Auto** (center) | Normal operation. Automation runs as configured. Default position. |
| **Run** (CW) | Operator is explicitly asking for the generator. GenMaster starts it and keeps it running until you turn the selector back to Auto. |

**The HOA is NOT a safety device.** It's an operator-side mode selector. If you need to physically guarantee the generator can't start, use the **EPO at the generator**, not the HOA.

If the HOA cable is cut or both contacts read closed at the same time: the system reports a fault on the web UI and treats the selector as Auto. Automation continues. Check the wiring; fault clears when the condition is resolved.

---

## Quiet override (one-off bypass without leaving Quiet)

If the selector is in Quiet but you need automation to fire **just this once** (e.g. Victron wants 15 minutes to top up the batteries):

1. Open the GenMaster web UI → Generator page
2. On the blue Quiet banner, click **Override**
3. Pick a duration in minutes
4. Automation fires normally until the timer expires (or until you turn the selector out of Quiet, which auto-clears the override)

Click **Cancel Override** on the banner to end it early.

---

## Combined states

When **both** the EPO and the HOA are active:

- The EPO always wins — generator cannot start.
- The HOA banner changes its wording to acknowledge the EPO (e.g. "Quiet Mode — EPO Active", "Run Mode — Held by EPO").
- In the Quiet + EPO case, the Override button is hidden — you can't override Quiet while the EPO is engaged because there's nothing to override.

When the EPO releases:

- If HOA is in Run: GenMaster starts the generator on the next heartbeat.
- If HOA is in Quiet (no override): automation stays suppressed; manual starts available.
- If HOA is in Auto: automation resumes per Victron / schedule / exercise.

---

## When in doubt, EPO

If you're not sure what to do, **engage the EPO at the generator**. The system always fails safe from that state. You can release it once you know what's going on.

---

## Contact info — fill in for your install

| Role | Name | Phone | Notes |
|------|------|-------|-------|
| **System owner** | _____________________ | _____________________ | Knows the install end-to-end |
| **Generator service** | _____________________ | _____________________ | Generator manufacturer's service line |
| **Electrician** | _____________________ | _____________________ | Wired the panel — for hardware issues |
| **Solar/Inverter installer** | _____________________ | _____________________ | If Victron behavior is unexpected |

**Web UI**: `___________________________________________` (fill in your Cloudflare tunnel hostname or Tailscale name)

**SSH to GenMaster** (last-resort access): `___________________________________________`
