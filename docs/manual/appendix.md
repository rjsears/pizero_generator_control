# Appendix

Comprehensive reference material for GenMaster operators — troubleshooting tables, command cheat sheets, state machine details, file locations, and recovery procedures.

---

## Troubleshooting

### Generator won't start

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Start button is grayed out | System is **disarmed** | Toggle **Generator Run Relay** to Armed on the [Generator Control](generator.md#top-status-row) page. |
| Click Start, nothing happens | GenSlave is **offline** | Check [GenSlave](genslave.md) for ONLINE status. Restart the slave container or fix WiFi. |
| Start command returns error toast | API secret mismatch | Re-save secret on both ends via [GenSlave → Connection Settings](genslave.md#connection-settings). |
| Generator starts then stops within seconds | Run Time Limits min-time set high but Victron released signal early | Check [Run Time Limits](generator.md#run-time-limits). |
| Generator starts but won't pull load | Hardware issue (transfer switch, wiring) | Outside GenMaster's scope — check generator + ATS manuals. |

### Generator won't stop

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Stop button does nothing | GenSlave offline | Use **Emergency Stop** which bypasses normal flow. If that fails too, manually open the breaker. |
| Generator restarts after stop | Victron signal still HIGH | Enable [Manual Override](generator.md#fuel-usage-and-manual-override) until Victron releases. |
| Stop command 200 but generator runs | Relay wired NC instead of NO, or relay stuck | Check Pimoroni Automation Hat Mini wiring; replace if a relay contact is welded. |

### GenSlave shows OFFLINE

| Likely cause | Action |
|--------------|--------|
| Pi Zero powered off | Verify physical power, indicator LEDs. |
| WiFi dropped | Check router for the `genslave` device; check WiFi Watchdog status in [System](system.md#wifi-watchdog) and on GenSlave page. |
| API secret rotation drift | Re-save secret on both ends from [GenSlave → Connection Settings](genslave.md#connection-settings). |
| Tailscale issue (if used) | `tailscale status` on both ends. |
| Heartbeat firewall block | Verify nothing on the network is blocking outbound TCP from GenMaster to the slave's `:8001`. |
| Container crashed | SSH the slave: `cd /opt/genslave && docker compose logs --tail=100 genslave`. |

### Victron signal not detected

| Likely cause | Action |
|--------------|--------|
| Wiring loose | Reseat Cerbo GX Relay 1/2 to GPIO17 + GND on the Pi 5. |
| Wrong relay polarity | In Cerbo settings, **Relay function** should be `Generator start/stop`. The contact should close on `Generator wanted`. |
| GPIO permissions | Verify GenMaster container has `privileged: true` and `/dev/gpiochip0` mapped. |
| GPIO17 in use elsewhere | No other process or HAT should be claiming GPIO17. |
| Cerbo SOC threshold not crossed | Check Cerbo's battery monitor — if SOC is above the trigger threshold, the relay won't close. |

### Database connection failed

| Likely cause | Action |
|--------------|--------|
| `genmaster_db` container not running | [Containers](containers.md) → start `genmaster_db`. |
| `DATABASE_PASSWORD` mismatch | Verify in [Settings → Environment](settings.md#environment); should match `genmaster_db`'s `POSTGRES_PASSWORD`. |
| Postgres data volume corrupt | Restore from backup downloaded earlier — see [Backup / restore](#backup--restore) below. |
| Disk full | Check [System → Health](system.md) Host Disk metric; clear old logs/Docker images. |

### Web UI inaccessible

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Browser timeout | Cloudflare tunnel down or Tailscale down | Try the LAN IP directly. Check `genmaster_cloudflared` and `genmaster_tailscale` containers. |
| HTTPS cert error | Let's Encrypt cert expired | [System → Health → SSL Certificates](system.md#ssl-certificates) → Force Renew. |
| 502 Bad Gateway | `genmaster` API container down/unhealthy | Restart `genmaster` from [Containers](containers.md). |
| 403 Forbidden | Your IP isn't in the allowed Access Control list | Add your IP via [Settings → Access Control](settings.md#access-control) (or temporarily disable geo-block for diagnosis). |
| Stuck "loading..." spinner | Backend reachable but DB query hung | Restart `genmaster_db`, then `genmaster`. |

### Notifications not arriving

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| No notifications, channels show ✓ Success | Cooldown timers active | [GenSlave → Notification Settings → Clear cooldown timers](genslave.md#notification-settings) (master cooldowns are similar). |
| Channel shows × Failed | Wrong URL, expired token, blocked sender | Click the test (▷) button on that channel to see the error message. |
| Email channel keeps failing | TLS misconfig or auth issue | Confirm SMTP host/port and that the username has SMTP-send permissions (some providers require an app password). |
| Apprise URL not working | Service-specific URL syntax | See the [Apprise wiki](https://github.com/caronc/apprise/wiki) for the exact format. |

### Schedules not firing

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Schedule status shows `Pending` long after expected fire time | System was disarmed at trigger time | Re-arm and wait for next occurrence. The skip is recorded in [Run History](history.md). |
| Schedule fires but generator doesn't run | GenSlave offline | Same as "GenSlave shows OFFLINE" above. |
| Wrong day or wrong time | Server timezone mismatch | Check `TZ` env var on `genmaster` container — should match your physical location. |

---

## State machine reference

GenMaster's state machine has these states. Transitions are driven by Victron, schedules, manual commands, and timeouts.

| State | Description | Typical exit conditions |
|-------|-------------|-------------------------|
| **idle** | Generator off, no run in progress. | Victron signal goes HIGH, schedule fires, or manual start. |
| **starting** | Start command sent to GenSlave. Waiting for relay confirmation. | Relay confirmed (→ running) or timeout (→ failed). |
| **running** | Generator is on. Heartbeat continues, runtime accumulates. | Victron signal goes LOW, schedule duration elapsed, manual stop, or runtime limit hit. |
| **stopping** | Stop command sent. Waiting for relay to open. | Relay confirmed off (→ cooldown) or timeout (→ failed). |
| **cooldown** | Brief post-stop period (configurable, default 60s). Prevents short-cycling. | Cooldown elapsed → idle. |
| **failed** | Start or stop returned an error. State persists until acknowledged. | Manual reset via API or UI clears to idle. |

A **run** is recorded when the state machine transitions `starting → running` and closed when it transitions out of `running` (to `stopping` or `failed`).

---

## Event types reference

Events that can fire notifications (configurable on the [Notifications → Configure](notifications.md#configure) tab):

| Event | Fires when |
|-------|------------|
| `generator.starting` | Start command issued. |
| `generator.started` | Generator confirmed running. |
| `generator.stopping` | Stop command issued. |
| `generator.stopped` | Generator confirmed off. |
| `generator.failed` | Start or stop command returned an error. |
| `generator.exercise_started` | An exercise run kicked off. |
| `generator.exercise_completed` | An exercise run finished normally. |
| `system.armed` | Operator armed the system. |
| `system.disarmed` | Operator disarmed. |
| `system.boot_reset` | GenMaster booted and reset state to safe defaults. |
| `slave.online` | Heartbeat resumed after being lost. |
| `slave.offline` | Heartbeat lost (configurable threshold). |
| `slave.failsafe_triggered` | Slave's independent failsafe forced relay OFF. |
| `victron.signal_high` | GPIO17 went HIGH (Victron requesting generator). |
| `victron.signal_low` | GPIO17 went LOW (Victron releasing). |
| `victron.signal_ignored` | Signal received while disarmed (logged-only). |
| `scheduled_run.fired` | Schedule trigger fired. |
| `scheduled_run.skipped` | Schedule fired but was skipped (disarmed, slave offline, etc.). |
| `scheduled_run.completed` | Scheduled run completed. |
| `notification.test` | Operator triggered a test notification. |
| `system.cert_expiring` | SSL cert is within 14 days of expiring. |
| `system.disk_low` | Host disk usage above 90%. |
| `system.memory_high` | Host memory usage above 90% sustained for >60s. |

---

## Default ports

| Service | Internal port | External access | Notes |
|---------|---------------|-----------------|-------|
| Nginx | 443 | Yes (HTTPS only) | Main entry point. HTTP→HTTPS redirect on 80. |
| FastAPI (GenMaster) | 8000 | No (internal) | Reverse-proxied through Nginx. |
| PostgreSQL | 5432 | No (internal) | Container-only. |
| Redis | 6379 | No (internal) | Container-only. |
| GenSlave API | 8001 | LAN / Tailscale only | Pi Zero 2W. Never expose publicly. |
| Portainer | 9000 | `/portainer/` path | Optional, gated by Nginx. |
| Cloudflared | (outbound) | Tunnel-only | Outbound HTTPS to Cloudflare edge; no incoming port. |
| Tailscale | UDP 41641 | (mesh) | WireGuard-based. |
| WiFi Watchdog | (host service) | None | Local-only systemd service. |

---

## File and directory locations

### On the GenMaster host

| Path | Purpose |
|------|---------|
| `/root/pizero_generator_control/genmaster/` | Compose stack root. `docker-compose.yaml`, `.env`, scripts. |
| `/root/pizero_generator_control/genmaster/.env` | Environment configuration (DB password, API secrets, Cloudflare token, etc.). |
| `/var/lib/docker/volumes/genmaster_postgres_data/` | Postgres data directory. |
| `/var/lib/docker/volumes/genmaster_redis_data/` | Redis persistence. |
| `/var/lib/docker/volumes/genmaster_nginx_certs/` | Let's Encrypt certificates. |
| `/var/lib/docker/volumes/genmaster_app_logs/` | Application log files. |
| `/var/lib/docker/volumes/genmaster_backups/` | Database / config backups. |

### Inside the `genmaster` container

| Path | Purpose |
|------|---------|
| `/app/` | Backend Python source. |
| `/app/logs/` | Application logs (mounted from host volume). |
| `/app/data/` | Runtime SQLite cache (if used). |
| `/app/alembic/` | Database migration scripts. |

### On the GenSlave host

| Path | Purpose |
|------|---------|
| `/opt/genslave/` | Compose root. |
| `/opt/genslave/.env` | Slave-side env (must contain matching `API_SECRET`). |
| `/opt/genslave/data/` | Optional SQLite cache. |
| `/opt/genslave/logs/` | Slave application logs. |

---

## Useful commands

### GenMaster host (SSH'd to the Pi 5)

```bash
# View logs from each service
docker compose logs --tail=100 genmaster
docker compose logs --tail=100 genmaster_nginx
docker compose logs --tail=100 genmaster_db

# Restart a single service
docker compose restart genmaster

# Restart the entire stack
docker compose down && docker compose up -d

# Pull new image and recreate (after a release)
docker compose pull genmaster
docker compose up -d --force-recreate genmaster

# Apply pending DB migrations
docker compose exec genmaster alembic upgrade head

# Reset admin password
docker compose exec genmaster python -m app.cli reset_password admin

# Open a Postgres shell
docker compose exec genmaster_db psql -U genmaster -d genmaster

# Tail nginx access log
docker compose exec genmaster_nginx tail -f /var/log/nginx/access.log

# Force renew Let's Encrypt certs
docker compose exec genmaster_certbot certbot renew --force-renewal

# Check Tailscale status
docker compose exec genmaster_tailscale tailscale status

# Check Cloudflare tunnel
docker compose logs --tail=50 genmaster_cloudflared
```

### GenSlave host (SSH'd to the Pi Zero)

```bash
cd /opt/genslave

# View logs
docker compose logs --tail=100 genslave

# Restart slave
docker compose restart genslave

# Pull new image
docker compose pull && docker compose up -d

# Check relay GPIO state directly (bypass API)
gpioget gpiochip0 16
```

### From GenMaster, addressing the slave

```bash
# Test heartbeat reachability
curl -H "X-API-Key: $SLAVE_API_SECRET" http://genslave.local:8001/api/health

# Force relay OFF (bypasses normal arming flow)
curl -X POST -H "X-API-Key: $SLAVE_API_SECRET" \
     http://genslave.local:8001/api/relay/off \
     -d '{"force": true}'
```

---

## Backup / restore

### Creating a backup

GenMaster includes a one-click backup at [Settings → Environment → Download Full Backup](settings.md#environment) (gated behind the Danger Zone confirmation). The backup is a tar.gz containing:

- The Postgres database dump.
- The current `.env` file (sensitive — store securely).
- The current `nginx.conf` and any custom Access Control rules.
- A `restore.sh` script that walks the operator through restoration.

Backups are timestamped: `genmaster_full_backup_YYYY-MM-DDTHH-MM-SS.tar.gz`.

You can also trigger a database-only backup from the host:

```bash
docker compose exec -T genmaster_db pg_dump -U genmaster -F c genmaster > genmaster_$(date +%Y%m%d).dump
```

### Restoring

For a full system restore from a backup archive:

```bash
# 1. Stop the stack
cd /root/pizero_generator_control/genmaster
docker compose down

# 2. Extract backup
tar -xzf genmaster_full_backup_YYYY-MM-DD.tar.gz -C /tmp/restore

# 3. Run the included restore.sh (it walks you through DB + .env + nginx.conf restore)
sudo bash /tmp/restore/restore.sh

# 4. Start the stack
docker compose up -d
```

For a database-only restore:

```bash
docker compose exec -T genmaster_db psql -U genmaster -d genmaster -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec -T genmaster_db pg_restore -U genmaster -d genmaster < genmaster_20260115.dump
docker compose restart genmaster
```

---

## Recovery from unbootable web UI

If you've broken the web UI (e.g. typo in `.env`, bad nginx config) and can no longer reach `/`, here's the recovery flow. SSH access is required.

```bash
# 1. SSH to the GenMaster host
ssh user@genmaster.local   # or its Tailscale name

# 2. Navigate to the install directory
cd /root/pizero_generator_control/genmaster

# 3. Identify what's broken
docker compose ps                  # which containers are unhealthy?
docker compose logs --tail=100 genmaster
docker compose logs --tail=100 genmaster_nginx

# 4. If .env was the problem, restore from your last backup:
ls /var/lib/docker/volumes/genmaster_backups/_data/
cp /var/lib/docker/volumes/genmaster_backups/_data/genmaster_full_backup_<timestamp>.tar.gz /tmp/
tar -xzf /tmp/genmaster_full_backup_<timestamp>.tar.gz -C /tmp/restore
cp /tmp/restore/.env /root/pizero_generator_control/genmaster/.env

# 5. Restart
docker compose down && docker compose up -d
```

---

## Performance tuning

### When GenMaster is sluggish

| Symptom | Tuning |
|---------|--------|
| Web UI slow to load | Check [System → Host Resources](system.md#host-system-resources) — if CPU >80% sustained, restart `genmaster`. |
| Frequent timeouts | Default [Heartbeat Interval](genslave.md#connection-settings) is 10s (failsafe at 30s). Raise it if you're seeing network noise; lower (e.g. 5s) for faster failure detection. Failsafe scales as 3× the interval. |
| Database slow | `VACUUM FULL` rarely needed but can help: `docker compose exec genmaster_db psql -U genmaster -d genmaster -c 'VACUUM FULL ANALYZE;'` |
| Disk filling up | Old run history accumulates. Either purge from the DB or increase disk. The run-history table is the largest contributor. |

### Tuning the Pi Zero 2W (GenSlave)

The Pi Zero 2W has only 416MB usable RAM. Watch for:

- Memory above 80% for sustained periods → reboot (or add a swap file).
- WiFi signal below -75 dBm → relocate or add an antenna.
- CPU temp above 70°C → improve airflow / add a small heatsink.

The slave's stat panel on [GenSlave](genslave.md#at-a-glance-health-cpu-memory-disk-temp) shows all of these live.

---

## Glossary

| Term | Definition |
|------|------------|
| **Apprise** | Notification library supporting 80+ services via URL strings. See [Apprise wiki](https://github.com/caronc/apprise/wiki). |
| **Armed / Disarmed** | Whether GenMaster will respond to automation triggers. Disarmed = read-only / monitoring mode. |
| **APScheduler** | Python scheduling library used for the cron-driven run scheduler. |
| **ATS** | Automatic Transfer Switch — the device that switches loads between grid/generator. Outside GenMaster's scope. |
| **Cerbo GX** | Victron Energy's central monitoring/control device for off-grid solar systems. Provides the GPIO signal that asks GenMaster to start the generator. |
| **Cooldown** | A short post-stop period before the state machine will accept a new start command, preventing rapid cycling. Default 60s. |
| **Failsafe** | Independent watchdog on GenSlave that forces the relay OFF if it stops hearing from GenMaster for a configured timeout. |
| **GenMaster** | The Raspberry Pi 5 running the FastAPI backend, web UI, scheduler, and Victron GPIO listener. The "brain". |
| **GenSlave** | The Raspberry Pi Zero 2W running the relay controller and failsafe. The "muscle". |
| **GPIO17** | The Pi 5 pin (physical pin 11) that listens for the Victron Cerbo GX relay signal. |
| **Heartbeat** | Periodic message GenMaster sends to GenSlave to confirm liveness and sync arming state. Default interval 10s; GenSlave's failsafe trips at 3× this (30s by default). |
| **HMAC** | Hash-based message authentication code; used to sign webhook payloads so receivers can verify they came from GenMaster. |
| **HAT (Pimoroni Automation Hat Mini)** | The add-on board on GenSlave that provides the physical relay and small LCD. |
| **Manual Override** | Mode where GenMaster ignores the Victron GPIO signal completely. Use during maintenance or when Victron is misreporting. |
| **mock GPIO** | Development mode where GenMaster simulates GPIO signals via API endpoints (no real Pi hardware needed). |
| **Run** | A single instance of the generator being on, from start command to stop. Recorded in [Run History](history.md). |
| **SOC** | State of Charge — battery percentage. Cerbo GX uses SOC thresholds to decide when to ask for the generator. |
| **State machine** | The backend logic that transitions the system through `idle → starting → running → stopping → cooldown → idle`. |
| **Tailscale** | Mesh VPN used to give GenMaster, GenSlave, and your phone secure access to each other from anywhere. |
| **Trigger** | What caused a run to start: `Victron Auto-Start`, `Scheduled Run`, `Manual Start`, `Exercise Run`. |
| **WAL (Write-Ahead Log)** | Postgres's crash-safety mechanism. Don't disable it. |
| **WiFi Watchdog** | Host service on GenMaster that pings a known target and bounces the WiFi interface on connectivity loss. |

---

## Security flag index

The following pages contain screenshots or fields with sensitive values you may want to mask before sharing externally:

| Page | What to mask |
|------|--------------|
| [GenSlave](genslave.md) | LAN IP, Tailscale IP, MAC address, WiFi SSID, API secret, Apprise URLs. |
| [Generator Control](generator.md) | Generator serial number (some manufacturers use it as a service-portal credential). |
| [Notifications → Channels (expanded)](notifications.md#channels) | Apprise URLs always contain bot tokens / webhook secrets. SMTP credentials in Email channels. To/From addresses. |
| [System → Network](system.md#network-sub-tab) | All IPs, MAC addresses, SSIDs. |
| [System → SSL Certificates](system.md#ssl-certificates) | Domain name (not strictly secret, but identifies your deployment). |
| [Settings → Access Control](settings.md#access-control) | External IP CIDRs (your home/office public IP). |
| [Settings → Environment](settings.md#environment) | Database password, API secrets, Cloudflare tunnel token, Tailscale auth key, webhook URLs. |
| [Settings → Account](settings.md#account) | Username (less sensitive but identifies your account). |
| [Containers → Logs](containers.md#logs-dialog) | Logs frequently include IPs, request paths, occasionally tokens. |

If you share screenshots externally, blur:

1. Any IP address ending in numbers other than `.0`/`.255`.
2. Any string starting with `tskey-`, `eyJh`, `tgram://`, `slack://`, `discord://`, `twilio://`, `mailto://`, `https://*/webhook`.
3. Email addresses other than your own.
4. Generator serial numbers.
5. Hostnames that identify your deployment (e.g. `mymachine.example.com`).

---

## API reference (selected endpoints)

GenMaster's full OpenAPI spec is available at `https://your-domain/docs` (Swagger) or `/redoc` (ReDoc). Key endpoints:

### Generator control

```
GET    /api/status              Current state, runtime, last heartbeat
GET    /api/generator/state     Just the state (lighter weight)
POST   /api/generator/start     {"trigger": "manual"} | {"trigger": "exercise"}
POST   /api/generator/stop
POST   /api/generator/emergency-stop
```

### System / arming

```
GET    /api/system/arm          Returns {armed: bool, armed_at, armed_by, slave_connection}
POST   /api/system/arm          {"source": "api"|"ui"|"webhook"}
POST   /api/system/disarm
GET    /api/system/health
GET    /api/system/slave        GenSlave heartbeat status
POST   /api/system/host/reboot  Requires admin
POST   /api/system/host/shutdown Requires admin
```

### Schedules

```
GET    /api/schedule
POST   /api/schedule            {name, start_time, duration_minutes, days_of_week[], enabled}
PATCH  /api/schedule/{id}
DELETE /api/schedule/{id}
```

### Run history

```
GET    /api/runs?start_date&end_date&limit&offset
GET    /api/runs/stats          30-day summary
```

### Notifications

```
GET    /api/notifications/channels
POST   /api/notifications/channels
PATCH  /api/notifications/channels/{id}
DELETE /api/notifications/channels/{id}
POST   /api/notifications/channels/{id}/test
GET    /api/notifications/groups
GET    /api/notifications/rules
GET    /api/notifications/history
```

### Containers

```
GET    /api/containers
POST   /api/containers/{name}/start
POST   /api/containers/{name}/stop
POST   /api/containers/{name}/restart
GET    /api/containers/{name}/logs?lines=200&since=
GET    /api/containers/{name}/inspect
```

### Settings

```
GET    /api/settings                  All settings (filtered by role)
PATCH  /api/settings/security
PATCH  /api/settings/access-control
PATCH  /api/settings/environment       Requires admin + danger-zone confirmation
PATCH  /api/settings/account
```

### Development (mock GPIO mode only)

```
GET    /api/dev/status
GET    /api/dev/gpio/state
POST   /api/dev/gpio/victron-signal    {"active": true|false}
POST   /api/dev/gpio/toggle
POST   /api/dev/webhook/test
```

All authenticated endpoints require either:

- A session cookie (after web login), or
- An `Authorization: Bearer <jwt>` header (for programmatic access), or
- An `X-API-Key: <secret>` header (for the slave-side endpoints).

---

## Hardware compatibility

### Tested generator types

| Type | Notes |
|------|-------|
| LPG (propane) | Most common in off-grid. Use 2-wire start input. |
| Natural Gas | Same wiring as LPG. |
| Diesel | Glow-plug delay may be needed — set Run Time Limits **min run time** to ≥ 5 min so the engine stabilizes before any auto-stop. |
| Gasoline | Less common in off-grid; works with same 2-wire interface. Choke automation is generator-side. |

### Tested Cerbo signal sources

| Source | Wiring |
|--------|--------|
| Cerbo GX **Relay 1** or **Relay 2** | NO contact → GPIO17, COM → Pi GND. |
| 24V dry contact (other source) | Use an opto-coupler module if voltage isn't 0/3.3V. |
| External PLC | Same — opto-isolate to protect the Pi GPIO. |

---

## Failure scenarios + expected behavior

| Scenario | Expected behavior |
|----------|-------------------|
| GenMaster reboots while generator running | On boot: state reset to safe (disarmed, generator_running=false), orphaned run closed with `stop_reason=power_loss`. Generator may still be physically running until GenSlave's failsafe trips (default 30s after last heartbeat — calculated as 3× the heartbeat interval). |
| GenSlave reboots while generator running | On boot: relay forced OFF (hardware safety). Generator stops. Run record on GenMaster gets stop_reason `slave_lost` after heartbeat timeout. |
| Network partition between master and slave | Heartbeats fail. After the failsafe timeout (default 30s = 3× the 10s heartbeat interval) the slave triggers failsafe and forces relay OFF, sends Apprise alert. |
| Postgres dies | API errors. Web UI shows toast + degraded badges. Generator state retained in-memory until restart. Recover by restarting `genmaster_db`. |
| Disk full | Logs fail to write. Backups fail. Run history may stop persisting. Web UI may degrade. Free space immediately. |
| Cert expires | HTTPS access fails. Force renew via [System → SSL Certificates](system.md#ssl-certificates) or `docker compose exec genmaster_certbot certbot renew --force-renewal`. |
| Tailscale auth key expires | Tailscale-routed access fails. Re-auth via Tailscale admin console or generate a new auth key and update `.env`. |
| Cloudflare tunnel down | Public URL fails. LAN/Tailscale access still works. Restart `genmaster_cloudflared`. |

---

## Related docs

- [Architecture overview](../ARCHITECTURE.md) — how the master + slave fit together at the system level.
- [Generator Controls (install guide)](../GENERATOR.md) — original install-side reference.
- [Scheduling (install guide)](../SCHEDULING.md) — deeper background on the scheduler.
- [Victron Integration](../VICTRON.md) — Cerbo GX wiring and behavior.
- [Notifications (install guide)](../NOTIFICATIONS.md) — Apprise setup details.
- [GenSlave Setup](../GENSLAVE.md) — slave Pi Zero install.
- [Tailscale VPN](../TAILSCALE.md) — mesh VPN setup.
- [Cloudflare Tunnel](../CLOUDFLARE.md) — public access setup.
- [Troubleshooting](../TROUBLESHOOTING.md) — extended troubleshooting reference.

## Getting help

- **GitHub Issues**: [github.com/rjsears/pizero_generator_control/issues](https://github.com/rjsears/pizero_generator_control/issues) — bug reports, feature requests.
- **GitHub Discussions**: [github.com/rjsears/pizero_generator_control/discussions](https://github.com/rjsears/pizero_generator_control/discussions) — community Q&A.
- **In-app Help**: the [?] icon in the header opens the [Help & Documentation dialog](common-ui.md#help--documentation-) with quick links to API docs, this manual, and the repo.
