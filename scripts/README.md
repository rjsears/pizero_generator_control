# Utility Scripts

This directory contains utility scripts for the RPi Generator Control system that run on the host (not in Docker).

## WiFi Watchdog

`wifi-watchdog.sh` monitors WiFi connectivity and automatically recovers from connection failures. Designed for both GenMaster (Pi5) and GenSlave (PiZero 2W).

### Features

- **Auto-detects gateway** - No hardcoded IPs; uses the current default gateway
- **Auto-detects WiFi interface** - Works with wlan0, wlp2s0, etc.
- **Escalating recovery** - Tries soft fixes before hard resets
- **Reboot protection** - Max one reboot per hour prevents loops
- **State persistence** - Remembers failure count across restarts
- **Works on both Pi5 and PiZero** - Adapts to available tools (nmcli vs wpa_cli)

### Recovery Sequence

| Consecutive Failures | Action |
|---------------------|--------|
| 1-3 | Soft WiFi reset (nmcli/wpa_cli) |
| 4-5 | Hard WiFi reset (ip link down/up) + service restart |
| 6+ | System reboot (once per hour max) |

### Safety Features

- **Checks gateway, not internet** - If your gateway is reachable but internet is down, no action is taken
- **Reboot cooldown** - Prevents reboot loops if the issue persists
- **Graceful degradation** - If nmcli isn't available, uses wpa_cli; if neither, uses ip link directly

### Installation

The WiFi watchdog can be installed during GenMaster or GenSlave setup, or manually:

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
| `WATCHDOG_PING_COUNT` | 2 | Number of pings per check |
| `WATCHDOG_MAX_SOFT_RESETS` | 3 | Soft resets before escalating |
| `WATCHDOG_MAX_HARD_RESETS` | 2 | Hard resets before reboot |
| `WATCHDOG_REBOOT_COOLDOWN` | 3600 | Minimum seconds between reboots |

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
