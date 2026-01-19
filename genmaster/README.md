# GenMaster - Generator Control System

The **Master Controller** for a wireless generator control system running on Raspberry Pi.

## Overview

GenMaster monitors the Victron Cerbo GX relay signal and sends commands to GenSlave to start/stop the generator. It provides a web-based dashboard for monitoring and manual control.

## Features

- **Victron Integration**: Monitors Cerbo GX relay signal for automatic generator control
- **Web Dashboard**: Real-time status, history, and manual controls
- **State Machine**: Manages generator state with proper transitions
- **Scheduling**: Automatic exercise schedules and maintenance reminders
- **Notifications**: Webhook support for n8n/Pushover/email alerts
- **Secure Communication**: Tailscale VPN for GenSlave connectivity

## Quick Start

### Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/rjsears/pizero_generator_control.git
cd pizero_generator_control/genmaster

# Copy and configure environment
cp .env.example .env
nano .env  # Configure your settings

# Start the stack
docker compose up -d
```

### Using Setup Script

For a guided installation with SSL and Tailscale configuration:

```bash
curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genmaster/setup.sh | bash
```

## Architecture

| Component | Description |
|-----------|-------------|
| **genmaster** | FastAPI backend + Vue.js frontend |
| **db** | PostgreSQL 16 database |
| **nginx** | Reverse proxy with SSL termination |
| **tailscale** | (Optional) VPN for secure connectivity |
| **cloudflared** | (Optional) Cloudflare Tunnel for public access |
| **portainer** | (Optional) Container management UI |

## Docker Socket Access

The Containers tab in the web UI requires access to the Docker socket. The setup script automatically:
1. Detects the Docker socket group ID
2. Mounts `/var/run/docker.sock` into the genmaster container
3. Adds the container to the correct group for socket access

If you're manually configuring docker-compose.yaml, add these to the genmaster service:

```yaml
genmaster:
  ...
  group_add:
    - "${DOCKER_GID:-999}"  # Use your host's docker group ID
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

Find your Docker group ID with: `stat -c '%g' /var/run/docker.sock`

## Supported Platforms

- `linux/amd64` - Standard x86_64 servers
- `linux/arm64` - Raspberry Pi 5, Pi 4, and other ARM64 devices

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_SECRET_KEY` | Application secret key | Required |
| `DATABASE_PASSWORD` | PostgreSQL password | Required |
| `SLAVE_API_URL` | GenSlave API URL | `http://genslave:8000` |
| `SLAVE_API_SECRET` | Shared secret with GenSlave | Required |
| `HEARTBEAT_INTERVAL_SECONDS` | Heartbeat interval | `60` |

See `.env.example` for all available options.

## Docker Compose Profiles

```bash
# Basic stack (GenMaster + PostgreSQL + nginx)
docker compose up -d

# With Tailscale VPN
docker compose --profile tailscale up -d

# With Cloudflare Tunnel
docker compose --profile cloudflare up -d

# Development mode with hot reload
docker compose --profile dev up -d
```

## Health Check

```bash
curl http://localhost/api/health
```

## Documentation

- [Project Outline](../generator_project_outline.md) - Complete system design
- [Backend API](../docs/agents/03-genmaster-backend.md) - API documentation
- [Frontend](../docs/agents/04-genmaster-frontend.md) - Vue.js components
- [Database Schema](../docs/agents/02-database-schema.md) - PostgreSQL tables

## Related Projects

- **GenSlave**: The relay controller that runs on a separate Pi Zero 2W
- [Full Documentation](../docs/)

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Author

Created by [rjsears](https://github.com/rjsears)
