# PiZero Generator Control - Project Tracker

## Project Status: 🟡 In Development

**Last Updated**: 2024-01-15

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Project Outline](../generator_project_outline.md) | Complete system design |
| [01 - Project Structure](agents/01-project-structure.md) | Conventions & file structure |
| [02 - Database Schema](agents/02-database-schema.md) | Database design & models |
| [03 - GenMaster Backend](agents/03-genmaster-backend.md) | FastAPI backend implementation |
| [04 - GenMaster Frontend](agents/04-genmaster-frontend.md) | Vue.js frontend implementation |
| [05 - GenSlave Backend](agents/05-genslave-backend.md) | Relay controller implementation |
| [06 - Docker Infrastructure](agents/06-docker-infrastructure.md) | Container configuration |
| [07 - Networking](agents/07-networking.md) | Tailscale & Cloudflare setup |
| [08 - Setup Scripts](agents/08-setup-scripts.md) | Installation automation |

---

## Implementation Phases

### Phase 1: Foundation
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create project directory structure | ⬜ | 01-project-structure | |
| Set up GenMaster Python package | ⬜ | 03-genmaster-backend | |
| Set up GenSlave Python package | ⬜ | 05-genslave-backend | |
| Create base SQLAlchemy models | ⬜ | 02-database-schema | |
| Initialize Alembic migrations | ⬜ | 02-database-schema | |
| Create initial migration | ⬜ | 02-database-schema | |
| Create FastAPI skeleton (GenMaster) | ⬜ | 03-genmaster-backend | |
| Create FastAPI skeleton (GenSlave) | ⬜ | 05-genslave-backend | |
| Test GPIO reading (GenMaster GPIO17) | ⬜ | 03-genmaster-backend | Requires hardware |
| Test Automation Hat Mini relay | ⬜ | 05-genslave-backend | Requires hardware |
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
| Implement GPIO monitor service | ⬜ | 03-genmaster-backend | |
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

### Phase 7: Containerization
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create GenMaster Dockerfile | ⬜ | 06-docker-infrastructure | |
| Create GenSlave Dockerfile | ⬜ | 06-docker-infrastructure | |
| Create docker-compose.yml (GenMaster) | ⬜ | 06-docker-infrastructure | |
| Create docker-compose.yml (GenSlave) | ⬜ | 06-docker-infrastructure | |
| Configure nginx | ⬜ | 06-docker-infrastructure | |
| Create .env.example files | ⬜ | 06-docker-infrastructure | |
| Test GPIO access in containers | ⬜ | - | Hardware test |
| Test I2C/SPI in containers | ⬜ | - | Hardware test |
| Create systemd service files | ⬜ | 06-docker-infrastructure | |

---

### Phase 8: Remote Access & Networking
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Configure Tailscale containers | ⬜ | 07-networking | |
| Test Tailscale connectivity | ⬜ | - | |
| Configure Cloudflare Tunnel (optional) | ⬜ | 07-networking | |
| Set up Tailscale ACLs | ⬜ | 07-networking | |
| Configure nginx for dual access | ⬜ | 07-networking | |
| Test GenMaster ↔ GenSlave over Tailscale | ⬜ | - | |
| Test webhook delivery over Tailscale | ⬜ | - | |

---

### Phase 9: Setup & Installation
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Create main setup.sh script | ⬜ | 08-setup-scripts | |
| Implement system preparation phase | ⬜ | 08-setup-scripts | |
| Implement hardware validation phase | ⬜ | 08-setup-scripts | |
| Implement network config phase | ⬜ | 08-setup-scripts | |
| Implement application deploy phase | ⬜ | 08-setup-scripts | |
| Create health-check.sh script | ⬜ | 08-setup-scripts | |
| Create update.sh script | ⬜ | 08-setup-scripts | |
| Create backup.sh script | ⬜ | 08-setup-scripts | |
| Test fresh install (GenMaster) | ⬜ | - | |
| Test fresh install (GenSlave) | ⬜ | - | |

---

### Phase 10: Testing & Polish
**Status**: 🔴 Not Started

| Task | Status | Agent Document | Notes |
|------|--------|----------------|-------|
| Write unit tests (GenMaster backend) | ⬜ | 03-genmaster-backend | |
| Write unit tests (GenSlave backend) | ⬜ | 05-genslave-backend | |
| Write integration tests | ⬜ | - | |
| Performance testing on Pi Zero 2W | ⬜ | - | |
| Memory usage optimization | ⬜ | - | |
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

### GenMaster
- [ ] Raspberry Pi Zero 2W
- [ ] SSD + USB adapter
- [ ] 5V 2.5A power supply
- [ ] 2-wire connection to Victron Cerbo GX relay

### GenSlave
- [ ] Raspberry Pi Zero 2W
- [ ] Pimoroni Automation Hat Mini
- [ ] SSD + USB adapter
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

### Testing Strategy
- Unit tests can be written without hardware (mock GPIO)
- Integration tests require both Pi Zero 2W devices
- End-to-end tests require full hardware setup including Victron/generator

---

## Changelog

### 2024-01-15
- Created project tracker
- Created all 8 agent handoff documents
- Added comprehensive task breakdown

---

*This document should be updated as tasks are completed.*
