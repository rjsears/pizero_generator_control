# GenSlave API Reference

Complete API documentation for GenSlave - the generator relay control component.

**Base URL:** `http://genslave:8001` (or your configured host/port)

**API Version:** 1.0.0

---

## Table of Contents

- [Authentication](#authentication)
- [Health & Monitoring](#health--monitoring)
  - [GET / - Service Info](#get----service-info-public)
  - [GET /api/health - Health Check](#get-apihealth---health-check)
  - [GET /api/failsafe - Failsafe Status](#get-apifailsafe---failsafe-status)
  - [POST /api/heartbeat - Receive Heartbeat](#post-apiheartbeat---receive-heartbeat)
- [Relay Control](#relay-control)
  - [GET /api/relay/state - Get Relay State](#get-apirelaystate---get-relay-state)
  - [POST /api/relay/on - Turn Relay ON](#post-apirelayon---turn-relay-on)
  - [POST /api/relay/off - Turn Relay OFF](#post-apirelayoff---turn-relay-off)
  - [GET /api/relay/arm - Get Arm Status](#get-apirelayarm---get-arm-status)
  - [POST /api/relay/arm - Arm Relay](#post-apirelayarm---arm-relay)
  - [POST /api/relay/disarm - Disarm Relay](#post-apirelaydisarm---disarm-relay)
- [System Information](#system-information)
  - [GET /api/system - System Info](#get-apisystem---system-info)
  - [POST /api/system/config - Update Config](#post-apisystemconfig---update-config)
  - [POST /api/system/rotate-key - Rotate API Key](#post-apisystemrotate-key---rotate-api-key)
- [Notifications](#notifications)
  - [GET /api/system/notifications - Get Config](#get-apisystemnotifications---get-notification-config)
  - [POST /api/system/notifications - Update Config](#post-apisystemnotifications---update-notification-config)
  - [POST /api/system/notifications/test - Send Test](#post-apisystemnotificationstest---send-test-notification)
  - [POST /api/system/notifications/enable - Enable/Disable](#post-apisystemnotificationsenable---enabledisable-notifications)
- [Error Responses](#error-responses)

---

## Authentication

All `/api/*` endpoints require authentication via the `X-API-Key` header.

### Request Format

```bash
curl -H "X-API-Key: your-api-secret" http://genslave:8001/api/health
```

### Authentication Responses

| Status Code | Meaning |
|-------------|---------|
| `200 OK` | Request authenticated and processed |
| `401 Unauthorized` | Missing `X-API-Key` header |
| `403 Forbidden` | Invalid API key |

### Example Error Response

```json
{
  "detail": "Invalid API key"
}
```

---

## Health & Monitoring

### GET `/` - Service Info (Public)

Basic service information. **No authentication required.**

**Response:**
```json
{
  "service": "GenSlave",
  "version": "1.0.0",
  "status": "running",
  "armed": false,
  "relay_state": false
}
```

---

### GET `/api/health` - Health Check

Detailed health status for monitoring systems.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "relay_state": false,
  "failsafe_active": false,
  "armed": false,
  "mock_mode": false
}
```

**Status Values:**
| Status | Description |
|--------|-------------|
| `healthy` | All systems normal |
| `degraded` | Failsafe triggered or hardware issue |
| `unhealthy` | Critical error |

---

### GET `/api/failsafe` - Failsafe Status

Current state of the failsafe monitor.

**Response:**
```json
{
  "running": true,
  "last_heartbeat": 1705612800,
  "seconds_since_heartbeat": 5,
  "heartbeat_count": 1234,
  "failsafe_triggered": false,
  "failsafe_triggered_at": null,
  "timeout_seconds": 30,
  "heartbeat_interval": 10,
  "timeout_source": "genmaster"
}
```

**Fields:**
| Field | Description |
|-------|-------------|
| `running` | Whether the failsafe monitor is active |
| `last_heartbeat` | Unix timestamp of last heartbeat received |
| `seconds_since_heartbeat` | Seconds since last heartbeat |
| `heartbeat_count` | Total heartbeats received since startup |
| `failsafe_triggered` | Whether failsafe is currently active |
| `failsafe_triggered_at` | When failsafe was triggered (unix timestamp) |
| `timeout_seconds` | Current failsafe timeout threshold |
| `heartbeat_interval` | GenMaster's heartbeat interval (if known) |
| `timeout_source` | `"genmaster"` if dynamic, `"config"` if using default |

---

### POST `/api/heartbeat` - Receive Heartbeat

Called by GenMaster to maintain connection and send commands.

**Request Body:**
```json
{
  "timestamp": 1705612800,
  "generator_running": false,
  "command": "none",
  "armed": true,
  "heartbeat_interval": 10
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | integer | Yes | Unix timestamp from GenMaster |
| `generator_running` | boolean | Yes | GenMaster's view of generator state |
| `command` | string | No | Command to execute: `"none"`, `"start"`, `"stop"` |
| `armed` | boolean | No | Sync armed state from GenMaster |
| `heartbeat_interval` | integer | No | GenMaster's heartbeat interval (used for dynamic timeout) |

**Response:**
```json
{
  "relay_state": false,
  "uptime": 3600,
  "failsafe_active": false,
  "heartbeat_count": 1235,
  "armed": true
}
```

---

## Relay Control

### GET `/api/relay/state` - Get Relay State

Current relay and arming status.

**Response:**
```json
{
  "relay_state": false,
  "last_change": 1705612000,
  "change_count": 5,
  "mock_mode": false,
  "armed": true,
  "armed_at": 1705610000
}
```

---

### POST `/api/relay/on` - Turn Relay ON

Activates the relay to start the generator.

**Request Body (optional):**
```json
{
  "force": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `force` | boolean | `false` | If `true`, bypasses armed check |

**Success Response:**
```json
{
  "success": true,
  "relay_state": true,
  "message": "Relay turned ON - generator starting"
}
```

**Error Response (403 - Not Armed):**
```json
{
  "detail": "Relay not armed - cannot turn relay ON"
}
```

---

### POST `/api/relay/off` - Turn Relay OFF

Deactivates the relay to stop the generator.

**Request Body (optional):**
```json
{
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "relay_state": false,
  "message": "Relay turned OFF - generator stopping"
}
```

> **Note:** OFF is always allowed for safety, even when not armed.

---

### GET `/api/relay/arm` - Get Arm Status

Get current arming status.

**Response:**
```json
{
  "success": true,
  "armed": true,
  "message": "Armed",
  "armed_at": 1705610000
}
```

---

### POST `/api/relay/arm` - Arm Relay

Arm the relay system to allow generator control.

**Request Body (optional):**
```json
{
  "source": "api"
}
```

**Response:**
```json
{
  "success": true,
  "armed": true,
  "message": "Relay armed",
  "armed_at": 1705612800
}
```

---

### POST `/api/relay/disarm` - Disarm Relay

Disarm the relay system. Prevents accidental activation.

**Request Body (optional):**
```json
{
  "source": "api"
}
```

**Response:**
```json
{
  "success": true,
  "armed": false,
  "message": "Relay disarmed",
  "relay_state": false,
  "warning": "Relay state unchanged - use explicit off command if needed"
}
```

> **Note:** Disarming does NOT automatically turn off the relay. If the relay is ON when you disarm, it will stay ON. Use `/api/relay/off` explicitly if needed.

---

## System Information

### GET `/api/system` - System Info

Comprehensive system metrics including CPU, memory, disk, temperature, and network.

**Response:**
```json
{
  "hostname": "genslave",
  "platform": "linux",
  "cpu_percent": 12.5,
  "ram_total_mb": 512,
  "ram_used_mb": 256,
  "ram_available_mb": 256,
  "ram_percent": 50.0,
  "disk_total_gb": 14.5,
  "disk_used_gb": 3.2,
  "disk_free_gb": 11.3,
  "disk_percent": 22.0,
  "temperature_celsius": 45.0,
  "temperature_fahrenheit": 113.0,
  "uptime_seconds": 86400,
  "ip_address": "192.168.1.100",
  "default_gateway": "192.168.1.1",
  "dns_servers": ["8.8.8.8", "8.8.4.4"],
  "network_interfaces": [
    {
      "interface": "wlan0",
      "ip_address": "192.168.1.100",
      "netmask": "255.255.255.0",
      "mac_address": "b8:27:eb:xx:xx:xx",
      "is_wifi": true,
      "wifi_ssid": "MyNetwork",
      "wifi_signal_dbm": -45,
      "wifi_signal_percent": 75
    }
  ],
  "status": "healthy",
  "warnings": []
}
```

**Status Thresholds:**
| Resource | Warning | Critical |
|----------|---------|----------|
| CPU | > 80% | > 90% |
| RAM | > 80% | > 90% |
| Disk | > 85% | > 95% |
| Temperature | > 70°C | > 80°C |

---

### POST `/api/system/config` - Update Config

Allows GenMaster to push configuration changes.

**Request Body:**
```json
{
  "failsafe_timeout_seconds": 60,
  "webhook_url": "https://example.com/webhook",
  "webhook_secret": "secret123"
}
```

All fields are optional. Only specified fields will be updated.

**Response:**
```json
{
  "success": true,
  "message": "Updated: failsafe_timeout=60, webhook_url updated"
}
```

> **Note:** Changes are applied in memory only and do not persist across container restarts.

---

### POST `/api/system/rotate-key` - Rotate API Key

Rotate the API secret key without restarting the container.

**Request Body:**
```json
{
  "new_key": "your-new-api-key-minimum-16-characters"
}
```

| Field | Type | Requirements |
|-------|------|--------------|
| `new_key` | string | 16-128 characters |

**Response:**
```json
{
  "success": true,
  "message": "API key rotated successfully. New key is now active."
}
```

> **Important:** After this call succeeds, all subsequent API calls must use the new key immediately. The old key will no longer work.

---

## Notifications

GenSlave uses [Apprise](https://github.com/caronc/apprise) for notifications, supporting 80+ services including:

- Telegram, Slack, Discord
- SMS (Twilio, Nexmo)
- Email (SMTP, Gmail)
- Push notifications (Pushover, Pushbullet)
- And many more

See [NOTIFICATIONS.md](NOTIFICATIONS.md) for detailed setup instructions.

### GET `/api/system/notifications` - Get Notification Config

Get current notification configuration.

**Response:**
```json
{
  "apprise_urls": ["tgram://****/12345..."],
  "configured": true,
  "enabled": true
}
```

> **Note:** URLs are masked for security. The actual tokens/credentials are hidden.

---

### POST `/api/system/notifications` - Update Notification Config

Configure notification services.

**Request Body:**
```json
{
  "apprise_urls": [
    "tgram://bottoken/chatid",
    "pover://userkey@apitoken"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Notification configuration updated. 2 service(s) configured."
}
```

**Common URL Formats:**
| Service | URL Format |
|---------|------------|
| Telegram | `tgram://bottoken/chatid` |
| Pushover | `pover://userkey@apitoken` |
| Slack | `slack://tokenA/tokenB/tokenC/channel` |
| Discord | `discord://webhook_id/webhook_token` |
| Email | `mailto://user:pass@gmail.com` |
| Twilio SMS | `twilio://sid:token@from_phone/to_phone` |

---

### POST `/api/system/notifications/test` - Send Test Notification

Send a test notification to all configured services.

**Response:**
```json
{
  "success": true,
  "message": "Test notification sent successfully",
  "configured_services": 2
}
```

---

### POST `/api/system/notifications/enable` - Enable/Disable Notifications

Enable or disable notifications globally.

**Request Body:**
```json
{
  "enabled": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Notifications disabled"
}
```

> **Note:** When disabled, no notifications are sent except test notifications. This allows temporarily muting alerts without removing the configuration.

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message here"
}
```

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Missing API key |
| `403` | Forbidden - Invalid API key or operation not allowed |
| `404` | Not Found - Endpoint doesn't exist |
| `500` | Internal Server Error |
| `503` | Service Unavailable - Hardware not available |

---

## Quick Reference

### cURL Examples

```bash
# Health check
curl -H "X-API-Key: SECRET" http://genslave:8001/api/health

# Get relay state
curl -H "X-API-Key: SECRET" http://genslave:8001/api/relay/state

# Arm the relay
curl -X POST -H "X-API-Key: SECRET" http://genslave:8001/api/relay/arm

# Turn relay ON
curl -X POST -H "X-API-Key: SECRET" http://genslave:8001/api/relay/on

# Turn relay OFF
curl -X POST -H "X-API-Key: SECRET" http://genslave:8001/api/relay/off

# Get system info
curl -H "X-API-Key: SECRET" http://genslave:8001/api/system

# Send test notification
curl -X POST -H "X-API-Key: SECRET" http://genslave:8001/api/system/notifications/test
```

### Python Example

```python
import httpx

GENSLAVE_URL = "http://genslave:8001"
API_KEY = "your-api-secret"

headers = {"X-API-Key": API_KEY}

# Get health
response = httpx.get(f"{GENSLAVE_URL}/api/health", headers=headers)
print(response.json())

# Arm and start generator
httpx.post(f"{GENSLAVE_URL}/api/relay/arm", headers=headers)
httpx.post(f"{GENSLAVE_URL}/api/relay/on", headers=headers)
```
