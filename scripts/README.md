# Utility Scripts

This directory contains utility scripts for the RPi Generator Control system that run on the host (not in Docker).

## WiFi Watchdog

`wifi-watchdog.sh` monitors WiFi connectivity and automatically recovers from connection failures. Designed for both GenMaster (Pi5) and GenSlave (PiZero 2W).

### Features

- **Auto-detects gateway** - No hardcoded IPs; uses the current default gateway
- **Auto-detects WiFi interface** - Works with wlan0, wlp2s0, etc.
- **Escalating recovery** - Tries soft fixes before hard resets
- **Reboot protection** - Max one reboot per hour prevents loops
- **State persistence** - Remembers the last reboot time across restarts and reboots (the failure count restarts from zero on every start)
- **Works on both Pi5 and PiZero** - Adapts to available tools (nmcli vs wpa_cli)

### Recovery Sequence

| Consecutive Failures | Action |
|---------------------|--------|
| 1 | Log only (grace period, no action) |
| 2-4 | Soft WiFi reset (nmcli/wpa_cli) |
| 5-6 | Hard WiFi reset (ip link down/up) + service restart |
| 7+ | Long-outage mode: checks continue every 30 s, but recovery actions run only every `WATCHDOG_RECOVERY_INTERVAL` (default 300 s). Each action first tries a reboot (only after the minimum outage of 600 s, once per hour max, and only if the reboot guard allows it); if the reboot is not allowed, it runs a recovery sequence: soft reset, then hard reset, then network service restart, stopping as soon as the gateway answers |

Shown with the defaults. The grace period (`WATCHDOG_GRACE_FAILURES`) and the number of soft and hard resets (`WATCHDOG_MAX_SOFT_RESETS`, `WATCHDOG_MAX_HARD_RESETS`) are configurable.

### Safety Features

- **Checks gateway, not internet** - If your gateway is reachable but internet is down, no action is taken
- **Reboot cooldown** - Prevents reboot loops if the issue persists. Checked against both the saved last-reboot time and system uptime (`/proc/uptime`), so it still holds on a Pi with no RTC whose clock is wrong while the network is down
- **Persistent state** - State is kept in `/var/lib/wifi-watchdog/state` (not tmpfs), so the last reboot time survives the reboot. The failure counter resets on every start, so a fresh boot restarts from soft resets
- **Minimum outage before reboot** - No reboot until connectivity has been failing continuously for `WATCHDOG_MIN_OUTAGE_BEFORE_REBOOT` seconds (default 600). Measured with `/proc/uptime`, so it does not depend on the wall clock
- **SSID visibility logging** - Before each reboot decision, the watchdog runs a fresh WiFi scan (`nmcli`) and logs whether a configured WiFi network is visible, so the journal shows whether the access point was down (router reboot, power outage) or the Pi was stuck (network visible, or the scan itself failed). The result is for diagnosis only and does not block the reboot; with the hourly reboot as the backstop, an empty scan from a wedged WiFi chip can no longer stall recovery. Skipped when `nmcli` is not installed or no WiFi connection is configured
- **Long-outage mode** - Once the soft and hard resets are exhausted, the connectivity check still runs every 30 s (so recovery is noticed immediately), but recovery actions run only once every `WATCHDOG_RECOVERY_INTERVAL` seconds (default 300). Each action tries a reboot first, at most once per hour, and otherwise runs the soft reset, hard reset, network service restart sequence. The interface is not bounced every 30 s for hours
- **Reboot guard (optional)** - When `WATCHDOG_REBOOT_GUARD_URL` is set, the watchdog fetches that URL before rebooting and refuses to reboot unless it reports `"relay_state": false`. A `true` relay state, a failed request, or an unparseable response all block the reboot; the watchdog keeps running the recovery sequence instead
- **Graceful degradation** - If nmcli isn't available, uses wpa_cli; if neither, uses ip link directly

### Installation

The WiFi watchdog can be installed during GenMaster or GenSlave setup, or manually:

#### GenSlave Setup

`genslave/setup.sh` offers to install the watchdog (default yes). It copies the files from a repository checkout if present, otherwise downloads them from GitHub. It also installs a drop-in, `/etc/systemd/system/wifi-watchdog.service.d/genslave.conf`, that sets:

```ini
[Service]
Environment="WATCHDOG_REBOOT_GUARD_URL=http://localhost:8001/api/health"
```

so the Pi Zero never reboots while the generator relay is energized. GenSlave setup also disables WiFi power save via `/etc/NetworkManager/conf.d/wifi-powersave-off.conf`.

#### Manual Installation

```bash
# Copy script
sudo cp wifi-watchdog.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/wifi-watchdog.sh

# Copy service file
sudo cp wifi-watchdog.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable wifi-watchdog
sudo systemctl start wifi-watchdog
```

#### Check Status

```bash
# Service status
sudo systemctl status wifi-watchdog

# View logs
sudo journalctl -u wifi-watchdog -f

# View recent logs
sudo journalctl -u wifi-watchdog --since "1 hour ago"
```

### Configuration

Configuration is done via environment variables in the systemd service file. Edit `/etc/systemd/system/wifi-watchdog.service`:

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCHDOG_CHECK_INTERVAL` | 30 | Seconds between connectivity checks |
| `WATCHDOG_PING_TIMEOUT` | 5 | Ping timeout in seconds |
| `WATCHDOG_PING_COUNT` | 3 | Number of pings per check |
| `WATCHDOG_GRACE_FAILURES` | 1 | Failed checks tolerated before any recovery action |
| `WATCHDOG_MAX_SOFT_RESETS` | 3 | Soft resets before escalating |
| `WATCHDOG_MAX_HARD_RESETS` | 2 | Hard resets before reboot |
| `WATCHDOG_REBOOT_COOLDOWN` | 3600 | Minimum seconds between reboots (also the minimum uptime before a reboot) |
| `WATCHDOG_STATE_FILE` | `/var/lib/wifi-watchdog/state` | Persistent state file |
| `WATCHDOG_REBOOT_GUARD_URL` | (empty) | If set, refuse to reboot unless this URL reports `"relay_state": false` |
| `WATCHDOG_MIN_OUTAGE_BEFORE_REBOOT` | 600 | Seconds of continuous failure before a reboot is considered |
| `WATCHDOG_RECOVERY_INTERVAL` | 300 | Seconds between recovery sequences in long-outage mode |

After editing, reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart wifi-watchdog
```

### Uninstallation

```bash
sudo systemctl stop wifi-watchdog
sudo systemctl disable wifi-watchdog
sudo rm /etc/systemd/system/wifi-watchdog.service
sudo rm /usr/local/bin/wifi-watchdog.sh
sudo systemctl daemon-reload
```

### Troubleshooting

#### Watchdog keeps rebooting the system

The reboot cooldown (default 1 hour) should prevent this. If reboots are happening too frequently:

1. Check if you have a persistent hardware issue
2. Increase `WATCHDOG_REBOOT_COOLDOWN`
3. Increase `WATCHDOG_MAX_SOFT_RESETS` and `WATCHDOG_MAX_HARD_RESETS`

#### Watchdog not detecting WiFi interface

Check that you have a wireless interface:

```bash
iw dev
# or
ls /sys/class/net/*/wireless
```

#### Soft reset not working

The script tries nmcli first, then wpa_cli. Check which is available:

```bash
which nmcli
which wpa_cli
```

On PiZero with minimal install, you may only have wpa_cli. On Pi5 with full Raspberry Pi OS, nmcli (NetworkManager) is typically available.
