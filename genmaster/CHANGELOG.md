# Changelog

All notable changes to the GenMaster project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-02-07

### Added

#### Automated Docker Builds
- GitHub Actions workflow now builds both GenMaster and GenSlave images automatically
- Triggers on push to main when `genmaster/**` or `genslave/**` paths change
- GenSlave builds for `linux/arm/v6` (Pi Zero compatible)
- Manual dispatch option to build specific images (both/genmaster/genslave)
- Path-based filtering to only build changed images

#### GPIO Support for Raspberry Pi 5
- GenMaster container now runs with `privileged: true` and `user: root` for GPIO access
- Enables proper GPIO17 Victron signal detection on Pi 5 hardware
- Required because Pi 5 uses different GPIO architecture (`/dev/gpiochip0`, `/dev/gpiomem4`)

### Changed

- Victron status now uses fast polling (5 seconds) for responsive UI updates
- Previously was in slow polling cycle (30 seconds)

### Fixed

- Fixed GPIO callbacks not triggering state machine (coroutine not awaited in threaded callback)
- Fixed comm restored notification showing "not armed" when auto-arm was triggered
- Added 5-second delay before sending notification to allow auto-arm to complete
- Fixed GenSlave not reading `.env` file on system reboot (added explicit `env_file:` directive)

---

## [1.1.1] - 2026-01-27

### Added

#### Override Notification Events
- New system notification events for manual override enable/disable
- `override_enabled`: Triggered when Victron override is enabled
- `override_disabled`: Triggered when Victron override is disabled
- Configurable in Settings → Notifications → System Notifications

### Fixed

- Fixed Victron override not persisting on page refresh (wrong API endpoint)
- Fixed Victron override 422 error (missing `override_type` parameter)
- Fixed notification target add/remove endpoints returning 405 error
- Fixed container stats/logs timeout errors (store now uses extended timeouts)
- Fixed env-config backup directory (now uses `/app/data/env_backups`)
- Added `.env` mount to setup.sh generated docker-compose

---

## [1.1.0] - 2026-01-26

### Added

#### Auto-Arm Relay on Connection Restore
- New feature to automatically arm the GenSlave relay when connection is restored
- Configurable via `AUTO_ARM_RELAY_ON_CONNECT` environment variable
- Respects manual disarm: if user manually disarms via UI, auto-arm won't override until they manually arm again
- Database fields: `config.auto_arm_relay_on_connect`, `system_state.manual_disarm_active`

#### Host-Tools Sidecar Container
- New persistent container for fast host network commands
- Pre-installed with `wireless-tools`, `iproute2`, `networkmanager`
- Uses `docker exec` instead of `docker run` for instant execution
- Eliminates 5+ second delays for WiFi status checks (no more package downloads per request)
- Memory limited to 32MB
- Docker Hub: `rjsears/genmaster-host-tools:latest`

#### Environment Configuration UI
- New Settings page for viewing/editing `.env` file from the web UI
- Backup/restore functionality for environment files
- Groups variables by category (database, GenSlave, networking, etc.)
- Requires mounting `.env` to `/config/.env`

#### Frontend API Optimizations
- Staggered API calls on GeneratorView to avoid browser connection saturation
- Phase 1: Critical data (cached endpoints) - instant
- Phase 2: Essential data (generator stats, fuel, health)
- Phase 3: Non-critical data (WiFi, Victron) - deferred 3 seconds
- Extended timeouts for slow endpoints:
  - Container stats/start/stop/restart: 30s
  - Container recreate: 60s
  - Container logs: 15s
  - Relay arm/disarm: 15s

### Changed

- SlaveClient connections now properly closed after use to prevent connection leaks
- HTTP client reset after consecutive connection failures
- WiFi endpoints (`/host/wifi/*`) now use host-tools container instead of spawning new containers

### Fixed

- Fixed `.env` file permissions check in setup.sh
- Fixed `.env` loading from `/config/.env` mount point
- Fixed default GenSlave port from 8000 to 8001 in migrations
- Fixed API timeout cascade when multiple slow endpoints called concurrently

## [1.0.0] - 2026-01-15

### Added

- Initial release of GenMaster
- Victron Cerbo GX relay signal monitoring
- Web-based dashboard with real-time status
- State machine for generator control
- Scheduling system for automatic exercise
- Notification support via webhooks
- Secure GenSlave communication via Tailscale VPN
- Docker deployment with multi-platform support (amd64/arm64)
- PostgreSQL database for persistent storage
- Redis cache for session management
- Nginx reverse proxy with SSL termination
- Container management UI (Portainer integration)

---

## Docker Compose Changes

### New Services

#### host-tools (v1.1.0)
```yaml
host-tools:
  image: rjsears/genmaster-host-tools:latest  # Or build locally
  container_name: genmaster_host_tools
  restart: unless-stopped
  network_mode: host
  privileged: true
  mem_limit: 32m
  memswap_limit: 32m
```

### Updated Volumes

#### genmaster (v1.1.0)
Add `.env` mount for Settings → Environment Config:
```yaml
volumes:
  - ./.env:/config/.env:rw  # Mount .env for UI editing
```

---

## Environment Variables

### New in v1.1.0

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTO_ARM_RELAY_ON_CONNECT` | Auto-arm relay when GenSlave connection restored | `false` |
| `GEN_INFO_MANUFACTURER` | Generator manufacturer (optional) | - |
| `GEN_INFO_MODEL_NUMBER` | Generator model number (optional) | - |
| `GEN_INFO_SERIAL_NUMBER` | Generator serial number (optional) | - |
| `GEN_INFO_FUEL_TYPE` | Fuel type: `lpg`, `natural_gas`, `diesel` (optional) | - |
| `GEN_INFO_LOAD_EXPECTED` | Expected load percentage (optional) | - |
| `GEN_INFO_FUEL_CONSUMPTION_50` | Fuel consumption at 50% load (optional) | - |
| `GEN_INFO_FUEL_CONSUMPTION_100` | Fuel consumption at 100% load (optional) | - |

---

## Migration Notes

### Upgrading to v1.1.0

1. **Pull latest code:**
   ```bash
   git pull origin main
   ```

2. **Update docker-compose.yaml:**
   - Add `host-tools` service (see above)
   - Add `.env` volume mount to `genmaster` service

3. **Pull/build new images:**
   ```bash
   docker compose pull  # or docker compose build
   ```

4. **Restart services:**
   ```bash
   docker compose up -d
   ```

5. **Run database migrations:**
   Migrations run automatically on container start.

---

## API Changes

### New Endpoints (v1.1.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/env-config` | GET | Get all environment variables (grouped) |
| `/api/env-config` | POST | Add new environment variable |
| `/api/env-config/{key}` | PUT | Update environment variable |
| `/api/env-config/{key}` | DELETE | Delete environment variable |
| `/api/env-config/backups` | GET | List .env backups |
| `/api/env-config/backup` | POST | Create .env backup |
| `/api/env-config/restore` | POST | Restore .env from backup |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `/api/system/host/wifi` | Now uses host-tools container (faster) |
| `/api/system/host/wifi/networks` | Now uses host-tools container |
| `/api/system/host/wifi/connect` | Now uses host-tools container |
| `/api/system/host/wifi/saved` | Now uses host-tools container |
| `/api/system/host/wifi/add` | Now uses host-tools container |
| `/api/system/host/wifi/delete` | Now uses host-tools container |
