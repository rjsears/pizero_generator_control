# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the RPi Generator Control system.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [GenMaster Issues](#genmaster-issues)
- [GenSlave Issues](#genslave-issues)
- [Communication Issues](#communication-issues)
- [Generator Control Issues](#generator-control-issues)
- [Victron Integration Issues](#victron-integration-issues)
- [Notification Issues](#notification-issues)
- [Database Issues](#database-issues)
- [Docker Issues](#docker-issues)
- [Log Analysis](#log-analysis)

---

## Quick Diagnostics

### System Health Check

Run these commands to quickly assess system status:

```bash
# GenMaster health
curl -s https://your-genmaster/api/health | jq .

# GenSlave health (via GenMaster)
curl -s https://your-genmaster/api/genslave/health \
  -H "Authorization: Bearer YOUR_TOKEN" | jq .

# Container status
docker compose ps

# Recent logs
docker compose logs --tail=50
```

### Expected Healthy Response

```json
{
  "status": "healthy",
  "generator_running": false,
  "slave_connected": true,
  "slave_armed": true,
  "victron_signal": "inactive",
  "database": "connected",
  "redis": "connected"
}
```

---

## GenMaster Issues

### Container Won't Start

**Symptoms:** Container exits immediately or keeps restarting.

**Check logs:**
```bash
docker compose logs genmaster
```

**Common causes:**

1. **Database not ready:**
   ```
   Error: Connection refused to postgres:5432
   ```
   **Fix:** Ensure postgres container is healthy:
   ```bash
   docker compose ps postgres
   docker compose logs postgres
   ```

2. **Missing environment variables:**
   ```
   Error: GENSLAVE_API_SECRET is required
   ```
   **Fix:** Check `.env` file has all required variables.

3. **Port already in use:**
   ```
   Error: Address already in use :8000
   ```
   **Fix:** Stop conflicting service or change port.

### Database Migrations Failed

**Symptoms:** App crashes with database schema errors.

**Fix:**
```bash
# Run migrations manually
docker compose exec genmaster alembic upgrade head

# Check migration status
docker compose exec genmaster alembic current
```

### API Returns 500 Errors

**Check application logs:**
```bash
docker compose logs genmaster | grep -i error
```

**Common causes:**
- Database connection lost
- Redis connection lost
- GenSlave unreachable (for proxy endpoints)

### High Memory Usage

**Check container stats:**
```bash
docker stats genmaster
```

**Fix:**
- Restart container: `docker compose restart genmaster`
- Check for memory leaks in logs
- Increase container memory limit if needed

---

## GenSlave Issues

### Container Won't Start

**Check logs:**
```bash
docker compose logs genslave
```

**Common causes:**

1. **GPIO access denied:**
   ```
   Error: Unable to determine board revision
   ```
   **Fix:** Ensure `privileged: true` in docker-compose.yaml.

2. **Automation Hat not detected:**
   ```
   Warning: automationhat library loaded but HAT not responding
   ```
   **Fix:** 
   - Check HAT is properly seated
   - Enable SPI: `sudo raspi-config` → Interface Options → SPI
   - Reboot Pi

### Mock Mode When HAT is Present

**Symptoms:** Logs show "Mock HAT mode" even with hardware.

**Check SPI:**
```bash
ls /dev/spidev*
# Should show /dev/spidev0.0, /dev/spidev0.1
```

**Enable SPI:**
```bash
sudo raspi-config
# Interface Options → SPI → Enable
sudo reboot
```

### Relay Not Clicking

1. **Check armed status:**
   ```bash
   curl http://localhost:8001/api/relay/state \
     -H "X-API-Key: YOUR_SECRET"
   ```
   Must be `"armed": true`.

2. **Check power supply:**
   - Pi Zero needs stable 5V 2.5A
   - Relay may not click with insufficient power

3. **Test relay directly:**
   ```python
   import automationhat
   automationhat.relay.one.on()  # Should click
   automationhat.relay.one.off()  # Should click
   ```

---

## Communication Issues

### GenSlave Not Reachable

**From GenMaster, test connection:**
```bash
# Via Tailscale hostname
ping genslave

# Test API
curl http://genslave:8001/api/health \
  -H "X-API-Key: YOUR_SECRET"
```

**Common causes:**

1. **Tailscale not connected:**
   ```bash
   tailscale status
   ```
   Both devices should show as connected.

2. **Wrong IP/hostname in config:**
   Check `GENSLAVE_HOST` in GenMaster's `.env`.

3. **Firewall blocking:**
   ```bash
   # On GenSlave
   sudo ufw status
   sudo ufw allow 8001
   ```

4. **GenSlave container not running:**
   ```bash
   # On GenSlave Pi
   docker compose ps
   ```

### Heartbeat Failures

**Symptoms:** GenSlave shows "Failsafe triggered" or frequent disconnections.

**Check heartbeat status:**
```bash
curl http://genslave:8001/api/failsafe \
  -H "X-API-Key: YOUR_SECRET"
```

**Common causes:**

1. **Network latency:**
   - Heartbeat timeout too short
   - Increase `FAILSAFE_TIMEOUT_SECONDS`

2. **GenMaster overloaded:**
   - Check GenMaster CPU/memory
   - Check database performance

3. **Intermittent network:**
   - Check WiFi signal strength
   - Consider wired connection

### API Authentication Errors

**Symptoms:** 401 Unauthorized responses.

**Check:**
1. **API secret matches:**
   - GenMaster: `GENSLAVE_API_SECRET`
   - GenSlave: `GENSLAVE_API_SECRET`
   - Must be identical

2. **Header format:**
   ```bash
   # Correct
   -H "X-API-Key: your-secret"
   
   # Wrong
   -H "Authorization: your-secret"
   ```

---

## Generator Control Issues

### Generator Won't Start

**Run through this checklist:**

1. **Is relay armed?**
   ```bash
   curl https://your-genmaster/api/generator/state \
     -H "Authorization: Bearer YOUR_TOKEN" | jq .armed
   ```
   Must be `true`.

2. **Is there an active override?**
   ```bash
   curl https://your-genmaster/api/override/status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   `force_stop` blocks automatic starts.

3. **Is runtime lockout active?**
   ```bash
   curl https://your-genmaster/api/generator/runtime-limits \
     -H "Authorization: Bearer YOUR_TOKEN" | jq .lockout_active
   ```

4. **Is GenSlave connected?**
   Check `slave_connected` in health endpoint.

5. **Is GenSlave armed?**
   GenSlave must be armed to execute relay commands.

### Generator Won't Stop

1. **Check if force_run override is active:**
   ```bash
   curl https://your-genmaster/api/override/status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. **Try force stop via GenSlave:**
   ```bash
   curl -X POST http://genslave:8001/api/relay/off \
     -H "X-API-Key: YOUR_SECRET" \
     -d '{"force": true}'
   ```

### State Mismatch Between Master and Slave

**Symptoms:** GenMaster shows running, GenSlave shows stopped (or vice versa).

**This should self-heal via heartbeat.** If not:

1. **Check heartbeat is working:**
   ```bash
   docker compose logs genmaster | grep heartbeat
   ```

2. **Force reconciliation:**
   Restart GenMaster to trigger startup reconciliation.

3. **Manual sync:**
   ```bash
   # Set GenSlave to match desired state
   curl -X POST http://genslave:8001/api/relay/off \
     -H "X-API-Key: YOUR_SECRET" -d '{"force": true}'
   ```

---

## Victron Integration Issues

### Signal Not Detected

**Check GPIO status:**
```bash
docker compose logs genmaster | grep -i victron
docker compose logs genmaster | grep -i gpio
```

**Common causes:**

1. **GPIO not accessible:**
   - Pi 5 needs `privileged: true` and `user: root`
   - Check device mappings for gpiochip

2. **Wiring issue:**
   - Verify connection to GPIO17 and GND
   - Test with multimeter

3. **Mock mode enabled:**
   - Check `MOCK_GPIO` environment variable

### Signal Stuck Active/Inactive

1. **Check Cerbo relay:**
   - Look for relay LED indicator
   - Listen for relay click

2. **Test GPIO manually:**
   ```python
   from gpiozero import Button
   btn = Button(17, pull_up=True)
   print(btn.is_pressed)  # True = signal active
   ```

3. **Check for shorts:**
   - Disconnect wire and test again

---

## Notification Issues

### Notifications Not Sending

1. **Check channel is enabled:**
   ```bash
   curl https://your-genmaster/api/notifications/channels \
     -H "Authorization: Bearer YOUR_TOKEN" | jq '.[].enabled'
   ```

2. **Check event configuration:**
   ```bash
   curl https://your-genmaster/api/system-notifications \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Test channel:**
   ```bash
   curl -X POST https://your-genmaster/api/notifications/channels/1/test \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Check logs:**
   ```bash
   docker compose logs genmaster | grep -i notification
   ```

### GenSlave Failsafe Not Notifying

1. **Check Apprise URLs configured:**
   ```bash
   curl https://your-genmaster/api/genslave/notifications \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. **Check notifications enabled:**
   Verify `enabled: true` in response.

3. **Check cooldown:**
   - Recent notification may have set cooldown
   - Clear cooldown to test again

---

## Database Issues

### PostgreSQL Won't Start

**Check logs:**
```bash
docker compose logs postgres
```

**Common causes:**

1. **Disk full:**
   ```bash
   df -h
   ```

2. **Corrupt data:**
   - Restore from backup
   - Or delete volume (loses data):
     ```bash
     docker compose down -v
     docker compose up -d
     ```

3. **Permission issues:**
   ```bash
   docker compose exec postgres ls -la /var/lib/postgresql/data
   ```

### Connection Pool Exhausted

**Symptoms:** "Too many connections" errors.

**Fix:**
```bash
# Restart to reset connections
docker compose restart genmaster

# Long-term: increase pool size in config
```

### Redis Connection Issues

**Check Redis:**
```bash
docker compose exec redis redis-cli ping
# Should return: PONG
```

**Fix:**
```bash
docker compose restart redis
```

---

## Docker Issues

### Container Keeps Restarting

**Check exit code:**
```bash
docker compose ps -a
# Look for exit code
```

**Common exit codes:**
- 0: Clean exit
- 1: Application error
- 137: OOM killed (out of memory)
- 139: Segfault

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a

# Clean specific volumes
docker volume prune
```

### Permission Denied

If you see `permission denied while trying to connect to the Docker daemon socket` (or `Got permission denied while trying to connect to the Docker daemon`), choose ONE of the following based on your situation:

**For one-off commands** (recommended for occasional admin):

```bash
sudo docker compose ...    # or `sudo docker ...`
```

**For daily use on a trusted workstation** (lets you run `docker` without sudo):

```bash
sudo usermod -aG docker $USER
# Log out and log back in for the group change to take effect.
```

!!! warning "Do NOT `chmod 666 /var/run/docker.sock`"
    Making the Docker socket world-writable lets any local user — including any compromised low-privilege process — control Docker, which is effectively root on the host. This is a common piece of bad advice on Stack Overflow; ignore it.

!!! info "Why is `docker` group membership 'effectively root'?"
    Anyone who can talk to the Docker daemon can spin up a privileged container that mounts the host's `/` and gives them a root shell. Only add yourself (or a service user) to the `docker` group on machines where you'd already be trusted as root.

---

## Log Analysis

### Viewing Logs

```bash
# All containers
docker compose logs

# Specific container
docker compose logs genmaster

# Follow logs
docker compose logs -f genmaster

# Last N lines
docker compose logs --tail=100 genmaster

# With timestamps
docker compose logs -t genmaster
```

### Filtering Logs

```bash
# Errors only
docker compose logs genmaster 2>&1 | grep -i error

# Specific component
docker compose logs genmaster | grep -i heartbeat

# Time range (requires timestamps)
docker compose logs -t genmaster | grep "2026-05"
```

### Common Log Patterns

**Healthy patterns:**
```
Heartbeat sent to GenSlave
Generator started - trigger: victron
GPIO monitor started on pin 17
```

**Warning patterns:**
```
Relay ON requested but relay not armed
Victron signal active but relay not armed
GenSlave connection timeout
```

**Error patterns:**
```
Failed to connect to GenSlave
Database connection lost
Failed to send notification
```

---

## Getting Help

If you can't resolve an issue:

1. **Collect diagnostics:**
   ```bash
   # Save to file
   docker compose logs > logs.txt
   docker compose ps >> logs.txt
   docker stats --no-stream >> logs.txt
   ```

2. **Check GitHub Issues:**
   [github.com/rjsears/pizero_generator_control/issues](https://github.com/rjsears/pizero_generator_control/issues)

3. **Open a new issue** with:
   - Description of problem
   - Steps to reproduce
   - Relevant log excerpts
   - System information (Pi model, OS version)

---

## Recovery Procedures

### Lost Network After WiFi Change

A bad static IP, gateway, or subnet on a saved WiFi profile can leave a device unreachable over the network. Recovery options (local console, `nmcli`, SD card edit, Ethernet fallback) are documented separately:

→ See [Network Recovery](manual/network-recovery.md).

### Full System Reset

If all else fails:

```bash
# Stop everything
docker compose down

# Remove all data (WARNING: loses all history)
docker compose down -v

# Pull fresh images
docker compose pull

# Start fresh
docker compose up -d

# Run migrations
docker compose exec genmaster alembic upgrade head
```

### Restore from Backup

```bash
# Stop services
docker compose stop genmaster

# Restore database
docker compose exec -T postgres pg_restore \
  -U postgres -d genmaster < backup.dump

# Start services
docker compose start genmaster
```

### Emergency Generator Stop

If automation isn't working, stop generator manually:

```bash
# Direct to GenSlave (bypasses GenMaster)
curl -X POST http://genslave:8001/api/relay/off \
  -H "X-API-Key: YOUR_SECRET" \
  -d '{"force": true}'
```

Or physically disconnect power to the Automation Hat relay.
