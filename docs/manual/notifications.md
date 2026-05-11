# Notifications

The Notifications page is where you configure how GenMaster tells you about generator events — start/stop, scheduled run results, failsafe trips, system warnings, and more. It uses [Apprise](https://github.com/caronc/apprise) under the hood, which means 80+ notification services are supported (Telegram, Slack, Discord, Email, ntfy, Pushover, Microsoft Teams, etc.).

![Notifications page overview](images/screenshots/notifications-01-overview.png)

## Overview row

Four stat cards at the top show:

| Card | Meaning |
|------|---------|
| **Total Channels** | How many notification destinations are configured. |
| **Active** | How many of those are currently enabled. |
| **Groups** | Number of channel groups (collections of channels). |
| **Sent (24h)** | Total notifications dispatched in the last 24 hours across all channels. |

## Sub-tabs

The page is organized into four tabs:

### Channels

The Channels tab is the default view. The **Notification Channels** card collapses by default — click it to expand and see all configured channels.

![Notification Channels — expanded list](images/screenshots/notifications-01-overview-expanded.png)

Each row in the expanded list shows: an icon (envelope for Email, bell/etc. for Apprise types), the channel name, the channel type (`Email`, `Apprise`), a **Success/Failed** badge from the most recent test, and a row of action icons:

| Icon | Action |
|------|--------|
| ▷ (test) | Send a test notification to this channel only. |
| ✏ (edit) | Open the **Edit Channel** dialog. |
| 🗑 (delete) | Remove the channel. |
| Toggle | Enable / disable the channel without deleting it. |

#### Editing an Email channel

Clicking the edit (pencil) icon on an Email channel opens this form:

![Edit Channel dialog — Email type](images/screenshots/notifications-06-edit-email-modal.png)

| Field | Notes |
|-------|-------|
| **Channel Name** | Friendly label, e.g. `Ops Email`. |
| **Channel Type** | Toggle between **Apprise** and **Email**. Email gives you direct SMTP fields (below); Apprise gives you a single URL field for any of 80+ services. |
| **SMTP Host** | Mail server hostname, e.g. `mail.gandi.net`, `smtp.gmail.com`. |
| **SMTP Port** | Typically `465` (SSL) or `587` (STARTTLS). |
| **Username** / **Password** | SMTP authentication credentials. |
| **From Address** | The `From:` header on outgoing alerts. |
| **To Addresses** | Comma-separated list of recipients. |
| **Use TLS encryption** | Toggle. Should be on for production mail servers. |
| **Description (optional)** | A note for yourself (e.g. "Alerts for critical generator events"). |
| **Enable this channel** | Master on/off. Disabled channels are kept but skipped. |

!!! example "Sensitive data"
    SMTP credentials and recipient addresses are sensitive. Never share unmasked screenshots of this dialog.

#### Editing an Apprise channel

Apprise channels use a single URL string that encodes the destination service and credentials.

![Edit Channel dialog — Apprise type](images/screenshots/notifications-07-edit-apprise-modal.png)

| Field | Notes |
|-------|-------|
| **Apprise URL** | Single URL string, e.g. `tgram://bottoken/chatid`, `slack://TokenA/TokenB/TokenC`, `discord://webhook_id/webhook_token`, `twilio://AccountSID:AuthToken@FromNumber/ToNumber`. |
| **Examples row** | The dialog shows quick-start prefixes: `discord://`, `tgram://`, `slack://`, `pover://`, `mailto://`. |
| **Apprise Wiki** | Linked from the form for the full URL syntax of all supported services. |

!!! tip "Quick service URL reference"
    - **Telegram**: `tgram://BOT_TOKEN/CHAT_ID`
    - **Discord**: `discord://WEBHOOK_ID/WEBHOOK_TOKEN`
    - **Slack**: `slack://TokenA/TokenB/TokenC` (or webhooks with `slack://hooks.slack.com/services/...`)
    - **Pushover**: `pover://USER_KEY@APP_TOKEN`
    - **ntfy**: `ntfy://TOPIC` (public) or `ntfys://USERNAME:PASSWORD@HOST/TOPIC` (private)
    - **Twilio SMS**: `twilio://ACCOUNT_SID:AUTH_TOKEN@FROM_NUMBER/TO_NUMBER`
    - **Email**: `mailto://USER:PASS@SMTP_HOST?from=FROM&to=TO`
    - **Microsoft Teams**: `msteams://TOKEN_A/TOKEN_B/TOKEN_C/`
    - See the full list at the [Apprise wiki](https://github.com/caronc/apprise/wiki). Each channel has:

- A **name** (your label, e.g. "My Telegram", "Ops Email").
- An **Apprise URL** — see [Apprise URL formats](https://github.com/caronc/apprise/wiki). Examples:
    - Telegram: `tgram://bottoken/chatid`
    - Slack: `slack://TokenA/TokenB/TokenC/`
    - Discord: `discord://webhook_id/webhook_token`
    - Email: `mailto://user:pass@gmail.com`
    - ntfy: `ntfy://topic-name`
- A **status toggle** — enable/disable without deleting.
- A **test** button — fires a test notification to that channel only.

The **Add Channel** button opens a modal where you fill in name + URL + initial enabled state.

![Add Channel dialog](images/screenshots/notifications-05-add-channel-modal.png)

!!! example "Sensitive data"
    Apprise URLs frequently contain bot tokens, webhook secrets, or passwords. Treat the Channels tab as sensitive — mask URLs before sharing screenshots.

### Groups

![Notifications — Groups tab](images/screenshots/notifications-02-groups.png)

Groups let you bundle channels and address them as one unit when configuring rules. For example, an `Ops Team` group might contain a Slack channel, two emails, and a Telegram bot — and you'd then send `Generator Failure` events to the whole group at once.

Each group has:

- A **name**.
- A **list of member channels**.
- An **edit / delete** action.

Use **Add Group** to create a new one and pick its members from your existing channels.

### Configure

![Notifications — Configure tab](images/screenshots/notifications-03-configure.png)

The rule engine. The Configure tab is split into three areas: a row of **status tiles**, four collapsible **event categories**, and a **Global Settings** block at the bottom (with a separate "GenSlave Remote" section in between for forwarded notifications).

#### Status tiles

| Tile | Meaning |
|------|---------|
| **Total Channels** | Count of configured channel destinations. |
| **Active** | How many of those are currently enabled. |
| **Groups** | Count of channel groups. |
| **Sent (24h)** | Notifications delivered in the last 24 hours. |
| **Maintenance** | Click to enable maintenance mode (suppresses all notifications). |
| **Quiet Hours** | Click to schedule a daily window where non-critical alerts are suppressed. |
| **N/27 Events Enabled** | How many of the 27 individual event types currently have at least one target. |
| **N/50 This Hour** | Notifications sent in the current hour vs. the [Rate Limiting](#rate-limiting) ceiling. |

#### Maintenance mode

Click the **Maintenance** tile to open the modal:

![Maintenance mode modal](images/screenshots/notifications-08-maintenance-modal.png)

| Field | Purpose |
|-------|---------|
| **Duration** | Pick how long maintenance lasts: 1, 2, 4, 8, 12, or 24 hours, or **Until I disable** for an open-ended window. |
| **Reason (optional)** | Free-text label so future-you remembers why you turned alerts off. |
| **Cancel** | Close without enabling. |
| **Enable Maintenance Mode** | Suppress all notifications for the chosen duration. |

!!! danger "Maintenance disables ALL alerts"
    While maintenance mode is active, **every** notification — including critical and failsafe events — is completely stopped. They're not queued or delivered later; they're discarded. Only use this for short, intentional windows where you'll generate alerts you don't want to be paged for.

#### Quiet Hours

Click the **Quiet Hours** tile to open the modal:

![Quiet Hours modal](images/screenshots/notifications-09-quiet-hours-modal.png)

| Field | Purpose |
|-------|---------|
| **Start Time** | When quiet hours begin (24-hour format). |
| **End Time** | When quiet hours end (next day if End ≤ Start). |
| **Quick Presets** | One-click options: Night (10pm – 7am), Late Night (11pm – 6am), Midnight (12am – 8am). |
| **Cancel** | Close without saving. |
| **Enable Quiet Hours** | Activate the schedule. |

Unlike maintenance mode, quiet hours **only suppress non-critical events** — `critical` severity alerts (like failsafe triggers and communication loss) still come through.

#### Event categories

Each category is a collapsible row that lists every event type GenMaster knows how to fire. Click a row to expand it and see the events it contains. Each event row has:

- A **toggle** on the right to enable/disable the event entirely.
- A **target count** ("1 target", "0 targets") showing how many channels/groups will receive it.
- A **severity badge** (`info`, `warning`, `critical`).
- A **chevron `>`** to open the per-event detail panel where you pick channels/groups and optionally edit the message template.

Each category also shows a **Quick Setup** row with an **Apply to All Events** button — use this to add the same channel target to every event in the category in one click.

##### Container Events (5 events)

![Container Events expanded](images/screenshots/notifications-10-container-events-expanded.png)

Docker container health and status alerts. By default these are off (0/5 enabled).

| Event | Severity | Triggers when |
|-------|----------|---------------|
| **Container High CPU** | warning | A container's CPU usage exceeds the configured threshold. |
| **Container High Memory** | warning | A container's memory usage exceeds the configured threshold. |
| **Container Restarted** | info | A container was automatically restarted (e.g. after a crash). |
| **Container Stopped** | warning | A container has stopped unexpectedly. |
| **Container Unhealthy** | warning | A container's healthcheck has failed. |

##### Generator Events (10 events)

![Generator Events expanded](images/screenshots/notifications-11-generator-events-expanded.png)

The core operational events around the generator itself.

| Event | Severity | Triggers when |
|-------|----------|---------------|
| **Failsafe Triggered** | critical | GenSlave's failsafe fired and forced the relay off due to communication loss. |
| **Generator Relay Disabled** | warning | The relay was disarmed (automatic operations now blocked). |
| **Generator Relay Enabled** | info | The relay was armed (automatic operations now allowed). |
| **Generator Started** | info | The generator entered the running state. |
| **Generator Stopped** | info | The generator entered the stopped state. |
| **Max Runtime — Cooldown Active** | warning | Max runtime hit; cooldown window in progress. |
| **Max Runtime — Manual Reset Required** | critical | Max runtime hit and the policy requires manual re-arm before the generator can run again. |
| **Override Disabled** | info | Manual override turned off (returning to automatic Victron control). |
| **Override Enabled** | warning | Manual override turned on (Victron signal ignored). |
| **Relay Disarmed on Boot (Fail-Safe)** | warning | The fail-safe boot policy automatically disarmed the relay after a GenMaster restart. See [Boot Arming Policy](generator.md#boot-arming-policy). |

##### GenMaster Events (4 events)

![GenMaster Events expanded](images/screenshots/notifications-12-genmaster-events-expanded.png)

Resource health for the GenMaster Pi 5 host itself.

| Event | Severity | Triggers when |
|-------|----------|---------------|
| **GenMaster Disk Space Low** | warning | Free disk space on the GenMaster host falls below threshold. |
| **GenMaster High CPU Temperature** | warning | CPU core temperature is high (typically >75°C). |
| **GenMaster High CPU Usage** | warning | Sustained high CPU utilization. |
| **GenMaster High Memory Usage** | warning | RAM usage exceeds the configured threshold. |

All four are enabled by default (4/4) — these are the canary alerts that tell you the master controller itself is in trouble.

##### GenSlave Events (6 events)

![GenSlave Events expanded](images/screenshots/notifications-13-genslave-events-expanded.png)

Communication status and resource health for the remote GenSlave Pi Zero.

| Event | Severity | Triggers when |
|-------|----------|---------------|
| **GenSlave Communication Lost** | critical | GenMaster has stopped receiving heartbeats from GenSlave. |
| **GenSlave Communication Restored** | info | Heartbeats have resumed after an outage. |
| **GenSlave Disk Space Low** | warning | Free disk space on the GenSlave SD card is low. |
| **GenSlave High CPU Temperature** | warning | GenSlave CPU temperature is high. |
| **GenSlave High CPU Usage** | warning | Sustained high CPU utilization on the slave. |
| **GenSlave High Memory Usage** | warning | RAM usage on the slave (only 416MB total) is high. |

All six are enabled by default (6/6).

#### GenSlave Remote — Notification Forwarding

Below the four event categories the page shows a **GenSlave Remote** divider followed by a single row:

- **GenSlave Notification Forwarding** *(Coming Soon)* — When enabled, this will forward GenMaster's outbound notifications through GenSlave's independent network path, so alerts go out even if GenMaster's primary network is down. Currently shows a "Coming Soon" badge.

#### Global Settings

Two collapsible cards at the very bottom of the page control system-wide notification limits:

![Global Settings — Rate Limiting + Daily Digest](images/screenshots/notifications-14-global-settings.png)

##### Rate Limiting

Default: **50/hour** (Medium preset).

| Field | Purpose |
|-------|---------|
| **Maximum Notifications Per Hour** | Slider from 10 to 500. Default 50. Once the hourly cap is hit, additional notifications are queued and delivered after the limit resets. |
| **Presets** | One-click: Low (25), Medium (50), Standard (100), High (200), Maximum (500). |
| **Emergency Contact** | Optional channel that gets a single alert when the rate limit is exceeded — so you know throttling is in effect. Defaults to "No emergency contact configured". |

!!! tip "Why rate limiting matters"
    Without a cap, a runaway loop (a container flapping unhealthy/restarted every 30 seconds, for example) could push thousands of notifications to your phone in an hour. The rate limiter throttles outbound delivery so a single failure mode can't drown your inbox or get you SMS-blocked by your carrier.

##### Daily Digest

Default: **Disabled**.

| Field | Purpose |
|-------|---------|
| **Enable Daily Digest** | Toggle. When on, low-priority (`info`) events are batched. |
| | Info-level events are collected throughout the day and sent as a single digest email at the configured time, rather than one notification per event. |

Use Daily Digest if your `info`-level events are noisy (lots of starts/stops/heartbeats) and you'd rather see a once-a-day summary than each one individually. `warning` and `critical` events bypass the digest and fire immediately.

### History

![Notifications — History tab](images/screenshots/notifications-04-history.png)

A log of every notification sent: timestamp, event type, target channel, status (delivered / failed / queued), and a preview of the rendered message body.

Use this to:

- Confirm an alert actually fired during a recent incident.
- Debug a channel that's silently failing (look for repeated `failed` rows).
- Verify your channel routing is what you expected.

## Two notification systems, one app

It's worth understanding that **GenMaster** and **GenSlave** maintain separate notification configurations:

- **GenMaster notifications** — what you configure on this page. Sent from the master Pi 5 over the host's network. If GenMaster is down, these don't fire.
- **GenSlave notifications** — configured on the [GenSlave](genslave.md#notification-settings) page. Sent independently from the Pi Zero. **These fire even when GenMaster is down**, which is the whole point of the failsafe.

For the most resilient setup, configure at least one channel on **both** sides — they're your two independent paths to find out something is wrong.

## What's next

- Set up the slave-side independent failsafe alerts: [GenSlave → Notification Settings](genslave.md#notification-settings).
- Read more about Apprise URL formats: [Apprise wiki](https://github.com/caronc/apprise/wiki).
- For the older webhook-based notification approach, see [Notifications guide](../NOTIFICATIONS.md).
