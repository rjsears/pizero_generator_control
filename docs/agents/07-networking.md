# Agent Handoff: Networking Setup

## Purpose
This document provides complete specifications for configuring Tailscale mesh VPN and optional Cloudflare Tunnel for secure remote access to the generator control system.

---

## Overview

The networking stack provides:
1. **Tailscale (Required)** - Secure mesh VPN for all device communication
2. **Cloudflare Tunnel (Optional)** - Public web access without port forwarding

### Deployment Methods

| Device | Hardware | Tailscale Deployment | Cloudflare Tunnel |
|--------|----------|---------------------|-------------------|
| **GenMaster** | Pi 5 8GB | Docker container (profile) | Docker container (profile) |
| **GenSlave** | Pi Zero 2W | Native installation | Not supported |

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└─────────────────────────────────────────────────────────────────────────────┘
              │                                           │
              │ (Optional)                                │
              │ Cloudflare Tunnel                         │
              ▼                                           │
┌─────────────────────┐                                   │
│   Cloudflare Edge   │                                   │
│  genmaster.domain   │                                   │
└─────────────────────┘                                   │
              │                                           │
              │                                           │
              ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TAILSCALE MESH NETWORK                               │
│                      (Encrypted WireGuard Tunnels)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  GenMaster  │◄──►│  GenSlave   │    │    n8n      │    │ Your Phone  │  │
│  │ 100.x.x.101 │    │ 100.x.x.102 │    │ 100.x.x.50  │    │ 100.x.x.20  │  │
│  │  :80 (web)  │    │ :8001 (api) │    │ :5678       │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tailscale Configuration

### Prerequisites

1. Tailscale account (free tier works)
2. Auth key from Tailscale admin console

### Generate Auth Key

1. Go to https://login.tailscale.com/admin/settings/keys
2. Click "Generate auth key..."
3. Settings:
   - **Reusable**: Yes (for multiple devices)
   - **Ephemeral**: No
   - **Pre-approved**: Yes (optional)
   - **Tags**: `tag:generator` (optional, for ACLs)
   - **Expiry**: 90 days (or longer)
4. Copy the key (starts with `tskey-auth-`)

### GenMaster: Docker Container Configuration

GenMaster uses Tailscale via Docker Compose profile. Enable with `--profile tailscale`:

```yaml
# genmaster/docker-compose.yml (excerpt)
services:
  tailscale:
    image: tailscale/tailscale:latest
    container_name: genmaster-tailscale
    hostname: genmaster
    restart: unless-stopped
    profiles:
      - tailscale
    environment:
      - TS_AUTHKEY=${TAILSCALE_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=false
      - TS_EXTRA_ARGS=${TAILSCALE_EXTRA_ARGS:---advertise-tags=tag:generator}
    volumes:
      - tailscale_state:/var/lib/tailscale
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: host

volumes:
  tailscale_state:
```

Start GenMaster with Tailscale:
```bash
docker compose --profile tailscale up -d
```

### GenSlave: Native Installation

GenSlave runs Tailscale natively (no Docker) to conserve RAM on Pi Zero 2W:

```bash
# Install Tailscale on GenSlave
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate with tag for ACLs
sudo tailscale up --authkey=tskey-auth-xxxxx --hostname=genslave --advertise-tags=tag:generator

# Check status
tailscale status
```

The GenSlave setup script (`genslave/setup.sh`) automates this installation.

### MagicDNS

With MagicDNS enabled (Tailscale default), devices are reachable by hostname:

- `genmaster` → GenMaster device
- `genslave` → GenSlave device
- `genmaster.your-tailnet.ts.net` → Full FQDN

Configure GenMaster to use hostname:

```bash
# In genmaster/.env
SLAVE_API_URL=http://genslave:8001
```

### Tailscale ACLs

Configure access control in Tailscale admin console:

```json
{
  "tagOwners": {
    "tag:generator": ["autogroup:admin"],
    "tag:n8n": ["autogroup:admin"],
    "tag:admin": ["autogroup:admin"]
  },
  "acls": [
    // Admin devices can access everything
    {
      "action": "accept",
      "src": ["tag:admin"],
      "dst": ["*:*"]
    },
    // Generator devices can talk to each other
    {
      "action": "accept",
      "src": ["tag:generator"],
      "dst": ["tag:generator:*"]
    },
    // Generator devices can send webhooks to n8n
    {
      "action": "accept",
      "src": ["tag:generator"],
      "dst": ["tag:n8n:5678"]
    },
    // n8n can query generator devices
    {
      "action": "accept",
      "src": ["tag:n8n"],
      "dst": ["tag:generator:80", "tag:generator:8001"]
    }
  ],
  "ssh": [
    // SSH access for admin devices
    {
      "action": "accept",
      "src": ["tag:admin"],
      "dst": ["tag:generator"],
      "users": ["autogroup:nonroot", "root"]
    }
  ]
}
```

### Tailscale SSH (Optional)

Enable SSH access through Tailscale:

```bash
# On each Pi
sudo tailscale up --ssh

# Then access from any Tailscale device
ssh pi@genmaster
```

### Subnet Router (Optional)

If you need to access local network devices through GenMaster:

```bash
# Advertise local subnet
sudo tailscale up --advertise-routes=192.168.1.0/24

# Enable in Tailscale admin console
# Go to Machines → GenMaster → Route settings → Enable routes
```

---

## Cloudflare Tunnel Configuration

### When to Use Cloudflare Tunnel

**Use it if:**
- Need public web access without Tailscale
- External services need webhook access
- Want additional DDoS protection
- Guest access requirement

**Don't use it if:**
- All devices are on Tailscale (most common)
- Concerned about resource usage (~75-100MB RAM)
- Want to minimize complexity

### Prerequisites

1. Cloudflare account (free tier works)
2. Domain managed by Cloudflare
3. Create tunnel in Cloudflare Zero Trust dashboard

### Create Tunnel

1. Go to https://one.dash.cloudflare.com/
2. Navigate to: Access → Tunnels
3. Click "Create a tunnel"
4. Name: `genmaster-tunnel`
5. Install connector: Choose Docker
6. Copy the tunnel token

### Docker Container Configuration

```yaml
# docker-compose.prod.yml (include with --profile cloudflare)
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: genmaster-cloudflared
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped
    network_mode: host
    profiles:
      - cloudflare
```

Start with Cloudflare profile:

```bash
docker compose --profile cloudflare up -d
```

### Tunnel Configuration

In Cloudflare Zero Trust dashboard, configure the tunnel:

**Public Hostname:**
- Subdomain: `genmaster`
- Domain: `yourdomain.com`
- Service: `http://localhost:80`

**Access Policy (Optional):**
1. Go to Access → Applications
2. Create new application
3. Name: GenMaster Control Panel
4. Configure authentication (email, Google, GitHub, etc.)

### Nginx Configuration for Cloudflare

Update nginx to trust Cloudflare headers:

```nginx
# nginx.conf additions

# Trust Cloudflare IPs for real client IP
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 131.0.72.0/22;
real_ip_header CF-Connecting-IP;

# Verify requests come from Cloudflare (optional extra security)
# geo $cloudflare_ip {
#     default 0;
#     173.245.48.0/20 1;
#     ... (all Cloudflare IPs)
# }
```

---

## Firewall Configuration

### UFW Rules (Recommended)

```bash
# Default deny incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (local network only - Tailscale SSH preferred)
sudo ufw allow from 192.168.0.0/16 to any port 22

# Allow Tailscale
sudo ufw allow in on tailscale0

# Allow HTTP on local network (for initial setup)
sudo ufw allow from 192.168.0.0/16 to any port 80

# Enable firewall
sudo ufw enable
```

### iptables for Docker

Docker manages its own iptables rules. To restrict external access:

```bash
# Block external access to Docker ports (except Tailscale)
sudo iptables -I DOCKER-USER -i eth0 ! -s 100.64.0.0/10 -j DROP
sudo iptables -I DOCKER-USER -i wlan0 ! -s 100.64.0.0/10 -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

---

## DNS Configuration

### Local DNS Resolution

If using local DNS server (Pi-hole, etc.):

```
# Local DNS records
genmaster.local    → 192.168.1.101
genslave.local     → 192.168.1.102
```

### Tailscale MagicDNS

MagicDNS provides automatic DNS:
- `genmaster` → Tailscale IP
- `genmaster.your-tailnet.ts.net` → Tailscale IP

Enable in Tailscale admin console under DNS settings.

---

## SSL/TLS Configuration

### Tailscale HTTPS (Recommended)

Tailscale provides automatic HTTPS certificates:

```bash
# Enable HTTPS on GenMaster
sudo tailscale cert genmaster.your-tailnet.ts.net
```

Update nginx for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name genmaster.your-tailnet.ts.net;

    ssl_certificate /etc/ssl/certs/genmaster.your-tailnet.ts.net.crt;
    ssl_certificate_key /etc/ssl/private/genmaster.your-tailnet.ts.net.key;

    # ... rest of config
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

### Cloudflare SSL

Cloudflare handles SSL termination automatically. Traffic flow:
```
Browser → HTTPS → Cloudflare → HTTP → Tunnel → GenMaster
```

For full encryption, use Cloudflare Origin certificates.

---

## Monitoring & Troubleshooting

### Tailscale Status

```bash
# Check connection status
tailscale status

# Check connectivity to specific device
tailscale ping genslave

# View Tailscale IP
tailscale ip -4

# Debug connection
tailscale netcheck

# View logs
journalctl -u tailscaled -f
# Or for Docker:
docker logs genmaster-tailscale -f
```

### Cloudflare Tunnel Status

```bash
# Check tunnel status
docker logs genmaster-cloudflared -f

# Verify in Cloudflare dashboard
# Access → Tunnels → genmaster-tunnel → Status: Healthy
```

### Network Debugging

```bash
# Test GenMaster → GenSlave connectivity
curl -H "X-GenControl-Secret: $SECRET" http://genslave:8001/api/status

# Test webhook delivery
curl -X POST http://n8n:5678/webhook/test -d '{"test": true}'

# Check listening ports
ss -tlnp

# Check Tailscale interface
ip addr show tailscale0
```

---

## Failover Considerations

### If Tailscale Goes Down

1. GenMaster and GenSlave lose contact
2. GenSlave triggers failsafe after threshold
3. Generator stops (safety measure)
4. Local network access still works (if configured)

### If Internet Goes Down

1. Tailscale connections may persist (direct LAN possible)
2. If DERP relay was in use, connection drops
3. Same failsafe behavior as above

### Mitigation

Configure Tailscale for direct LAN connection:

```bash
# Enable LAN access (Tailscale admin console)
# Devices → GenMaster → Disable key expiry
# This keeps devices connected even during internet outage
```

---

## Security Best Practices

1. **Use Tailscale ACLs** - Limit which devices can access what
2. **Rotate auth keys** - Use short-lived keys for initial setup
3. **Enable Tailscale SSH** - Avoid exposing SSH on public interface
4. **Use Cloudflare Access** - If public access needed, require authentication
5. **API secrets** - Strong, unique secrets for API authentication
6. **Firewall rules** - Default deny, whitelist necessary traffic
7. **Keep updated** - Regular updates for Tailscale and cloudflared

---

## Configuration Reference

### GenMaster Networking Environment

```bash
# .env
# Tailscale
TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# GenSlave connection (Tailscale hostname)
SLAVE_API_URL=http://genslave:8001
SLAVE_API_SECRET=strong-shared-secret

# Webhooks (Tailscale hostname)
WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
WEBHOOK_SECRET=webhook-secret

# Cloudflare (optional)
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoixxxxx
```

### GenSlave Networking Environment

```bash
# .env
# Tailscale
TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# API secret (must match GenMaster)
API_SECRET=strong-shared-secret

# Webhook for failsafe (Tailscale hostname)
WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
WEBHOOK_SECRET=webhook-secret
```

---

## Agent Implementation Checklist

### Tailscale Setup
- [ ] Generate Tailscale auth keys (reusable, with tag:generator)
- [ ] Configure Tailscale ACLs in admin console
- [ ] Enable MagicDNS
- [ ] **GenMaster**: Configure Tailscale in docker-compose (--profile tailscale)
- [ ] **GenSlave**: Install Tailscale natively (setup.sh handles this)
- [ ] Test GenMaster ↔ GenSlave connectivity via Tailscale hostname
- [ ] Test webhook delivery to n8n over Tailscale
- [ ] Enable Tailscale SSH for maintenance

### Cloudflare Tunnel (Optional - GenMaster only)
- [ ] Create Cloudflare tunnel in Zero Trust dashboard
- [ ] Configure tunnel in docker-compose (--profile cloudflare)
- [ ] Configure Cloudflare Access for authentication
- [ ] Update nginx for Cloudflare IP headers

### Security
- [ ] Configure firewall rules (UFW)
- [ ] Test failover scenarios
- [ ] Document Tailscale IPs for reference

---

## Related Documents

- `06-docker-infrastructure.md` - Container configuration
- `08-setup-scripts.md` - Network setup automation
- `03-genmaster-backend.md` - API that uses network
- `05-genslave-backend.md` - API that uses network
