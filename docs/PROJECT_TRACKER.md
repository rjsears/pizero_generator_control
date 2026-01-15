# PiZero Generator Control - Project Tracker

## Project Status: 🟡 In Development

**Last Updated**: 2026-01-15

---

## Architecture Overview

### Hardware Configuration

| Device | Hardware | Role | Deployment |
|--------|----------|------|------------|
| **GenMaster** | Raspberry Pi 5 8GB + 128GB NVMe | Master controller, Web UI | Docker + PostgreSQL |
| **GenSlave** | Raspberry Pi Zero 2W + Automation Hat Mini | Relay controller | Native Python + SQLite |

### Key Architecture Decisions

1. **GenMaster on Pi 5**: Upgraded from Pi Zero 2W for better performance and Docker support
2. **PostgreSQL for GenMaster**: Full-featured database with JSONB, async support via asyncpg
3. **SQLite for GenSlave**: Zero-overhead file-based database to conserve RAM on Pi Zero 2W
4. **Native deployment for GenSlave**: No Docker to save ~150MB RAM
5. **Docker Hub publishing**: Multi-arch images (amd64/arm64) for GenMaster

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Project Outline](../generator_project_outline.md) | Complete system design |
| [01 - Project Structure](agents/01-project-structure.md) | Conventions & file structure |
| [02 - Database Schema](agents/02-database-schema.md) | PostgreSQL (GenMaster) & SQLite (GenSlave) |
| [03 - GenMaster Backend](agents/03-genmaster-backend.md) | FastAPI backend implementation |
| [04 - GenMaster Frontend](agents/04-genmaster-frontend.md) | Vue.js frontend implementation |
| [05 - GenSlave Backend](agents/05-genslave-backend.md) | Native relay controller implementation |
| [06 - Docker Infrastructure](agents/06-docker-infrastructure.md) | Container configuration |
| [07 - Networking](agents/07-networking.md) | Tailscale & Cloudflare setup |
| [08 - Setup Scripts](agents/08-setup-scripts.md) | Installation automation |

### Implementation Files

| File | Description | Status |
|------|-------------|--------|
| `genmaster/Dockerfile` | Multi-arch Dockerfile | ✅ Created |
| `genmaster/docker-compose.yml` | Docker Compose with profiles | ✅ Created |
| `genmaster/setup.sh` | Interactive installation script | ✅ Created |
| `genmaster/.env.example` | Environment template | ✅ Created |
| `genmaster/nginx/` | Nginx configuration | ✅ Created |
| `genslave/setup.sh` | Native installation script | ✅ Created |
| `.github/workflows/docker-publish.yml` | Docker Hub CI/CD | ✅ Created |

---

## Implementation Phases

### Phase 1: Foundation
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create project directory structure | ⬜ | 01-project-structure | |
| Set up GenMaster Python package | ⬜ | 03-genmaster-backend | |
| Set up GenSlave Python package | ⬜ | 05-genslave-backend | |
| Create base SQLAlchemy models | ⬜ | 02-database-schema | PostgreSQL for GenMaster |
| Create SQLite models for GenSlave | ⬜ | 02-database-schema | No Alembic needed |
| Initialize Alembic migrations (GenMaster only) | ⬜ | 02-database-schema | |
| Create initial migration | ⬜ | 02-database-schema | |
| Create FastAPI skeleton (GenMaster) | ⬜ | 03-genmaster-backend | |
| Create FastAPI skeleton (GenSlave) | ⬜ | 05-genslave-backend | |
| Test GPIO reading (GenMaster GPIO17) | ⬜ | 03-genmaster-backend | Requires Pi 5 hardware |
| Test Automation Hat Mini relay | ⬜ | 05-genslave-backend | Requires Pi Zero 2W |
| Test Automation Hat Mini LCD | ⬜ | 05-genslave-backend | Requires hardware |

---

### Phase 2: Core Communication
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Implement GenSlave relay endpoints | ⬜ | 05-genslave-backend | |
| Implement GenSlave heartbeat endpoint | ⬜ | 05-genslave-backend | |
| Implement GenMaster slave client | ⬜ | 03-genmaster-backend | |
| Implement GenMaster heartbeat service | ⬜ | 03-genmaster-backend | |
| Create heartbeat monitor (GenSlave) | ⬜ | 05-genslave-backend | |
| Implement failsafe logic (GenSlave) | ⬜ | 05-genslave-backend | |
| Test bidirectional communication | ⬜ | - | Integration test |
| Test failsafe trigger | ⬜ | - | Integration test |

---

### Phase 3: State Management
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Implement state machine service | ⬜ | 03-genmaster-backend | |
| Implement GPIO monitor service | ⬜ | 03-genmaster-backend | Using gpiod for Pi 5 |
| Create Victron signal handlers | ⬜ | 03-genmaster-backend | |
| Implement boot recovery logic | ⬜ | 03-genmaster-backend | |
| Add manual start/stop functionality | ⬜ | 03-genmaster-backend | |
| Implement override system | ⬜ | 03-genmaster-backend | |
| Test state persistence | ⬜ | - | Reboot test |
| Test Victron signal response | ⬜ | - | Hardware test |

---

### Phase 4: Web Interface
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Initialize Vue.js project | ⬜ | 04-genmaster-frontend | |
| Configure Tailwind CSS | ⬜ | 04-genmaster-frontend | |
| Create API client modules | ⬜ | 04-genmaster-frontend | |
| Create Pinia stores | ⬜ | 04-genmaster-frontend | |
| Build StatusCard component | ⬜ | 04-genmaster-frontend | |
| Build HealthGauge component | ⬜ | 04-genmaster-frontend | |
| Build RuntimeChart component | ⬜ | 04-genmaster-frontend | |
| Build ScheduleTable component | ⬜ | 04-genmaster-frontend | |
| Build Dashboard view | ⬜ | 04-genmaster-frontend | |
| Build History view | ⬜ | 04-genmaster-frontend | |
| Build Schedule view | ⬜ | 04-genmaster-frontend | |
| Build Settings view | ⬜ | 04-genmaster-frontend | |
| Test real-time updates | ⬜ | - | |
| Test responsive design | ⬜ | - | Mobile testing |

---

### Phase 5: Notifications
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Implement webhook service | ⬜ | 03-genmaster-backend | |
| Create webhook payload schemas | ⬜ | 03-genmaster-backend | |
| Add webhook test endpoint | ⬜ | 03-genmaster-backend | |
| Implement GenSlave failsafe webhook | ⬜ | 05-genslave-backend | |
| Create n8n workflow | ⬜ | - | External system |
| Test all webhook events | ⬜ | - | |

---

### Phase 6: Scheduling
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Implement APScheduler service | ⬜ | 03-genmaster-backend | |
| Create schedule CRUD endpoints | ⬜ | 03-genmaster-backend | |
| Implement recurring schedules | ⬜ | 03-genmaster-backend | |
| Add auto-stop for manual runs | ⬜ | 03-genmaster-backend | |
| Test schedule execution | ⬜ | - | |
| Test recurring patterns | ⬜ | - | |

---

### Phase 7: Containerization (GenMaster Only)
**Status**: 🟡 Infrastructure Created

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create GenMaster Dockerfile | ✅ | genmaster/Dockerfile | Multi-arch support |
| Create docker-compose.yml | ✅ | genmaster/docker-compose.yml | With profiles |
| Configure nginx | ✅ | genmaster/nginx/ | HTTP & SSL configs |
| Create .env.example | ✅ | genmaster/.env.example | |
| Create entrypoint scripts | ✅ | genmaster/docker/ | |
| Test GPIO access in container | ⬜ | - | Requires Pi 5 hardware |
| Build and test Docker image | ⬜ | - | |

### GenSlave Native Installation
**Status**: 🟡 Infrastructure Created

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create setup.sh script | ✅ | genslave/setup.sh | |
| Configure systemd service | ✅ | 05-genslave-backend | In documentation |
| Configure log rotation | ✅ | 05-genslave-backend | In documentation |
| Test native installation | ⬜ | - | Requires Pi Zero 2W |

---

### Phase 8: Remote Access & Networking
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Configure Tailscale (GenMaster) | ⬜ | 07-networking | Docker container |
| Configure Tailscale (GenSlave) | ⬜ | 05-genslave-backend | Native install |
| Test Tailscale connectivity | ⬜ | - | |
| Configure Cloudflare Tunnel (optional) | ⬜ | 07-networking | |
| Set up Tailscale ACLs | ⬜ | 07-networking | |
| Configure nginx for dual access | ⬜ | 07-networking | |
| Test GenMaster ↔ GenSlave over Tailscale | ⬜ | - | |
| Test webhook delivery over Tailscale | ⬜ | - | |

---

### Phase 9: Setup & Installation
**Status**: 🟡 Scripts Created

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create GenMaster setup.sh | ✅ | genmaster/setup.sh | Full n8n_nginx style |
| Create GenSlave setup.sh | ✅ | genslave/setup.sh | Lightweight native |
| Create health-check scripts | ✅ | In setup.sh files | |
| Create backup scripts | ✅ | In setup.sh files | |
| Test fresh install (GenMaster) | ⬜ | - | Requires Pi 5 |
| Test fresh install (GenSlave) | ⬜ | - | Requires Pi Zero 2W |

---

### Phase 10: CI/CD & Publishing
**Status**: 🟡 Workflows Created

| Task | Status | Notes |
|------|--------|-------|
| Create Docker Hub workflow | ✅ | .github/workflows/docker-publish.yml |
| Configure Docker Hub secrets | ⬜ | DOCKERHUB_USERNAME, DOCKERHUB_TOKEN |
| Test multi-arch build | ⬜ | linux/amd64, linux/arm64 |
| Publish to Docker Hub | ⬜ | rjsears/genmaster |
| Add security scanning | ✅ | Trivy in workflow |

---

### Phase 11: Testing & Polish
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Write unit tests (GenMaster backend) | ⬜ | 03-genmaster-backend | |
| Write unit tests (GenSlave backend) | ⬜ | 05-genslave-backend | |
| Write integration tests | ⬜ | - | |
| Performance testing on Pi 5 | ⬜ | - | |
| Memory optimization (GenSlave) | ⬜ | - | Target <200MB |
| Database backup/restore testing | ⬜ | - | |
| Documentation review | ⬜ | - | |
| Security review | ⬜ | - | |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ | Not started |
| 🟡 | In progress |
| ✅ | Complete |
| ❌ | Blocked |
| ⏸️ | On hold |

---

## Hardware Requirements

### GenMaster (Updated)
- [x] Raspberry Pi 5 8GB (upgraded from Pi Zero 2W)
- [x] 128GB NVMe SSD + adapter
- [ ] 5V 5A USB-C power supply
- [ ] 2-wire connection to Victron Cerbo GX relay

### GenSlave
- [ ] Raspberry Pi Zero 2W
- [ ] Pimoroni Automation Hat Mini
- [ ] SSD + USB adapter (or good quality SD card)
- [ ] 5V 2.5A power supply
- [ ] 2-wire connection to generator remote start

---

## Open Questions

1. **Victron Relay Behavior**: Does the relay close to ground or provide voltage?
   - **Status**: ❓ Needs confirmation
   - **Assumption**: Closes to ground (normally open)

2. **Generator Start Mechanism**: Momentary pulse or continuous contact?
   - **Status**: ❓ Needs confirmation
   - **Assumption**: Continuous contact while running

3. **Generator Feedback**: Any way to confirm generator started?
   - **Status**: ❓ Needs confirmation
   - **Assumption**: None available

---

## Notes

### Agent Assignment
Each agent document can be handed off independently. Recommended order:
1. Database schema (02) - foundation for all code
2. GenMaster backend (03) - core business logic
3. GenSlave backend (05) - can work in parallel with GenMaster
4. Frontend (04) - after backend APIs are defined
5. Docker (06) - after applications are built
6. Networking (07) - after Docker is configured
7. Setup scripts (08) - final integration

### Deployment Strategy
- **GenMaster**: Use `genmaster/setup.sh` for guided Docker installation
- **GenSlave**: Use `genslave/setup.sh` for native Python installation
- Both devices communicate over Tailscale VPN

### Testing Strategy
- Unit tests can be written without hardware (mock GPIO)
- Integration tests require both Pi devices on Tailscale
- End-to-end tests require full hardware setup including Victron/generator

---

## Changelog

### 2026-01-15 (Architecture Update)
- Upgraded GenMaster hardware to Raspberry Pi 5 8GB + 128GB NVMe
- Changed GenMaster database from MariaDB to PostgreSQL 16
- Changed GenSlave database from MariaDB to SQLite
- Updated GenSlave to native deployment (no Docker)
- Created GenMaster Dockerfile with multi-arch support
- Created docker-compose.yml with Tailscale/Cloudflare profiles
- Created GitHub Actions workflow for Docker Hub publishing
- Created comprehensive setup.sh scripts for both devices
- Updated all agent documentation to reflect new architecture

### 2024-01-15
- Created project tracker
- Created all 8 agent handoff documents
- Added comprehensive task breakdown

---

*This document should be updated as tasks are completed.*
