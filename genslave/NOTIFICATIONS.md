# GenSlave Notifications Guide

GenSlave uses [Apprise](https://github.com/caronc/apprise) for notifications, giving you access to **80+ notification services** including SMS, push notifications, email, and chat platforms.

---

## Table of Contents

- [Overview](#overview)
- [Notification Types](#notification-types)
- [Configuration](#configuration)
  - [Via API](#via-api)
  - [Common Services](#common-services)
- [Service-Specific Setup](#service-specific-setup)
  - [Telegram](#telegram)
  - [Pushover](#pushover)
  - [SMS (Twilio)](#sms-twilio)
  - [Email (SMTP)](#email-smtp)
  - [Slack](#slack)
  - [Discord](#discord)
- [Testing](#testing)
- [Enabling/Disabling](#enablingdisabling)
- [Troubleshooting](#troubleshooting)

---

## Overview

GenSlave sends notifications for critical events:

1. **Failsafe Triggered** - When communication with GenMaster is lost and the relay is turned OFF
2. **Communication Restored** - When GenMaster reconnects after a failsafe, reminding you to re-arm
3. **Test Notifications** - Manual tests to verify your configuration

Notifications are optional but highly recommended for safety monitoring.

---

## Notification Types

### Failsafe Triggered (Critical)

Sent when the failsafe system activates due to lost GenMaster communication.

**Title:** `GenSlave FAILSAFE TRIGGERED`

**Body:**
```
Generator relay has been turned OFF due to lost communication with GenMaster.

No heartbeat received for 30 seconds.

Please check GenMaster connectivity and re-arm the relay when communication is restored.
```

### Communication Restored (Warning)

Sent when GenMaster reconnects after a failsafe event, but the relay is still disarmed.

**Title:** `GenSlave Communication Restored`

**Body:**
```
Communication with GenMaster has been restored.

The relay is currently DISARMED after the failsafe event.

Please re-arm the relay from the GenMaster dashboard to resume generator control.
```

### Test Notification (Info)

Sent when you manually test your notification configuration.

**Title:** `GenSlave Test Notification`

**Body:**
```
This is a test notification from GenSlave.

If you received this, your notification configuration is working correctly.
```

---

## Configuration

### Via API

Configure notifications using the GenSlave API:

```bash
# Set notification URLs
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["tgram://bottoken/chatid"]}' \
  http://genslave:8001/api/system/notifications

# Test the configuration
curl -X POST -H "X-API-Key: YOUR_KEY" \
  http://genslave:8001/api/system/notifications/test

# Check current configuration
curl -H "X-API-Key: YOUR_KEY" \
  http://genslave:8001/api/system/notifications
```

### Via GenMaster UI

You can also configure GenSlave notifications through the GenMaster web interface:
1. Go to **Settings** > **GenSlave**
2. Scroll to the **Notifications** section
3. Add your Apprise URLs
4. Click **Test** to verify

### Common Services

| Service | URL Format | Notes |
|---------|------------|-------|
| Telegram | `tgram://bottoken/chatid` | Best for instant mobile alerts |
| Pushover | `pover://userkey@apitoken` | Reliable push notifications |
| Twilio SMS | `twilio://sid:token@from/to` | Text messages (paid) |
| Email | `mailto://user:pass@gmail.com` | Free but may be slow |
| Slack | `slack://token/channel` | Good for team alerts |
| Discord | `discord://webhook_id/token` | Good for team alerts |

---

## Service-Specific Setup

### Telegram

Telegram is recommended for its reliability and instant delivery.

**1. Create a Bot:**
- Message [@BotFather](https://t.me/BotFather) on Telegram
- Send `/newbot` and follow the prompts
- Save the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**2. Get Your Chat ID:**
- Start a chat with your new bot
- Send any message to it
- Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- Find your `chat_id` in the response

**3. Configure GenSlave:**
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["tgram://123456789:ABCdefGHIjklMNOpqrsTUVwxyz/987654321"]}' \
  http://genslave:8001/api/system/notifications
```

**URL Format:** `tgram://BOT_TOKEN/CHAT_ID`

---

### Pushover

Pushover provides reliable push notifications with priority levels.

**1. Create Account:**
- Sign up at [pushover.net](https://pushover.net)
- Note your **User Key** from the dashboard

**2. Create Application:**
- Go to [Create Application](https://pushover.net/apps/build)
- Note the **API Token**

**3. Configure GenSlave:**
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["pover://USER_KEY@API_TOKEN"]}' \
  http://genslave:8001/api/system/notifications
```

**URL Format:** `pover://USER_KEY@API_TOKEN`

**With Priority:**
```
pover://USER_KEY@API_TOKEN?priority=high
```

---

### SMS (Twilio)

Twilio allows sending SMS messages (requires paid account).

**1. Create Account:**
- Sign up at [twilio.com](https://www.twilio.com)
- Note your **Account SID** and **Auth Token**
- Get a phone number

**2. Configure GenSlave:**
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["twilio://ACCOUNT_SID:AUTH_TOKEN@FROM_PHONE/TO_PHONE"]}' \
  http://genslave:8001/api/system/notifications
```

**URL Format:** `twilio://SID:TOKEN@+15551234567/+15559876543`

> **Note:** Phone numbers must include country code (e.g., `+1` for US)

---

### Email (SMTP)

Send notifications via email using any SMTP provider.

**Gmail Example:**

1. Enable "App Passwords" in your Google Account (requires 2FA)
2. Generate an App Password for "Mail"

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["mailto://your.email:APP_PASSWORD@gmail.com?to=recipient@email.com"]}' \
  http://genslave:8001/api/system/notifications
```

**URL Format:** `mailto://USER:PASSWORD@SMTP_HOST?to=RECIPIENT`

**Generic SMTP:**
```
mailtos://user:password@smtp.example.com:587?to=recipient@email.com
```

---

### Slack

Send notifications to a Slack channel.

**1. Create Incoming Webhook:**
- Go to your Slack workspace settings
- Apps > Manage > Custom Integrations > Incoming Webhooks
- Add a new webhook and select a channel

**2. Configure GenSlave:**
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["slack://TOKEN_A/TOKEN_B/TOKEN_C/#channel"]}' \
  http://genslave:8001/api/system/notifications
```

The webhook URL `https://hooks.slack.com/services/T.../B.../xxx` becomes `slack://T.../B.../xxx/#channel`

---

### Discord

Send notifications to a Discord channel.

**1. Create Webhook:**
- In Discord, go to Server Settings > Integrations > Webhooks
- Create a new webhook for your channel
- Copy the webhook URL

**2. Configure GenSlave:**

The webhook URL `https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN` becomes:

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"apprise_urls": ["discord://WEBHOOK_ID/WEBHOOK_TOKEN"]}' \
  http://genslave:8001/api/system/notifications
```

---

## Testing

Always test your notification configuration after setting it up:

```bash
# Send a test notification
curl -X POST -H "X-API-Key: YOUR_KEY" \
  http://genslave:8001/api/system/notifications/test
```

**Response:**
```json
{
  "success": true,
  "message": "Test notification sent successfully",
  "configured_services": 1
}
```

If `success` is `false`, check:
- Your URL format is correct
- API tokens/credentials are valid
- The service is reachable from the Pi

---

## Enabling/Disabling

You can temporarily disable notifications without removing the configuration:

```bash
# Disable notifications
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}' \
  http://genslave:8001/api/system/notifications/enable

# Re-enable notifications
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}' \
  http://genslave:8001/api/system/notifications/enable
```

When disabled:
- No automatic notifications are sent
- Test notifications still work (to verify config)
- Your configuration is preserved

---

## Troubleshooting

### Notifications Not Sending

1. **Check configuration:**
   ```bash
   curl -H "X-API-Key: YOUR_KEY" http://genslave:8001/api/system/notifications
   ```
   - Is `configured` true?
   - Is `enabled` true?

2. **Test the notification:**
   ```bash
   curl -X POST -H "X-API-Key: YOUR_KEY" \
     http://genslave:8001/api/system/notifications/test
   ```

3. **Check GenSlave logs:**
   ```bash
   docker logs genslave 2>&1 | grep -i notif
   ```

### Common Issues

| Issue | Solution |
|-------|----------|
| Invalid URL format | Check Apprise docs for correct syntax |
| Authentication failed | Verify tokens/passwords are correct |
| Connection refused | Check network/firewall settings |
| Test works but failsafe doesn't | Ensure notifications are enabled |

### URL Validation

Apprise URLs must be properly formatted. Common mistakes:

| Wrong | Right |
|-------|-------|
| `telegram://...` | `tgram://...` |
| `pushover://...` | `pover://...` |
| Missing `@` in Pushover | `pover://user@token` |
| Spaces in URL | URL-encode or remove |

---

## Multiple Services

You can configure multiple notification services for redundancy:

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "apprise_urls": [
      "tgram://bottoken/chatid",
      "pover://userkey@apitoken",
      "mailto://user:pass@gmail.com?to=backup@email.com"
    ]
  }' \
  http://genslave:8001/api/system/notifications
```

All configured services will receive notifications.

---

## Full Apprise Documentation

For a complete list of supported services and URL formats, see the official Apprise documentation:

- **GitHub:** https://github.com/caronc/apprise
- **Wiki (all services):** https://github.com/caronc/apprise/wiki
