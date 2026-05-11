# Nginx Access Control

This document explains the **IP-based access control** layer of GenMaster's nginx reverse proxy: how the `geo` block evaluates client IPs, how traffic from different sources (LAN, Cloudflare Tunnel, Tailscale) is treated, and how to manage the allowlist from the GenMaster UI.

!!! note "Real-IP and trusted-proxy configuration is documented separately"
    For how nginx identifies the real client IP behind the cloudflared tunnel sidecar — including `set_real_ip_from`, the `CF-Connecting-IP` vs `X-Forwarded-For` decision, and the trust model — see [`SECURITY.md`](SECURITY.md#how-nginx-identifies-the-real-client-ip). This page assumes that real-IP is already correctly configured and focuses on what to do with the resulting `$remote_addr`.

## Overview

GenMaster uses nginx as a reverse proxy with IP-based access control. The `geo` block in nginx.conf determines whether requests are treated as "internal" or "external".

- **internal** — granted access to the entire GenMaster interface on port 443: the web UI (`/`), backend API (`/api/`), websocket (`/ws/`), health endpoint (`/healthz`), and Portainer (`/portainer/`).
- **external** — denied with HTTP 403 by every location block on the 443 listener.

In other words, the IP allowlist below governs **all** access to GenMaster's public HTTPS interface, not just Portainer. If a client's IP is not in the list, none of the management interface is reachable. To tighten security further, you can disable the Cloudflare tunnel entirely and reach the UI only over Tailscale.

## Traffic Sources

GenMaster can be accessed through three different paths:

### 1. Direct LAN Access (10.x.x.x, 192.168.x.x, etc.)

- **Path**: Client → Host port 443 → nginx container
- **What nginx sees**: Real client IP (e.g., 10.200.40.2)
- **Why it works**: Docker port publishing preserves source IP for external traffic

### 2. Cloudflare Tunnel Access

- **Path**: Client → Cloudflare Edge → cloudflared sidecar (pinned at `172.30.0.10`) → nginx container
- **What nginx sees without real_ip config**: Docker network IP (`172.30.0.10`, the cloudflared sidecar)
- **What nginx sees with real_ip config**: Real client IP from the `CF-Connecting-IP` header
- **Why real_ip is needed**: nginx must rewrite `$remote_addr` from the sidecar's IP to the real client so the `geo` block can apply the allowlist correctly. The trusted-proxy list is narrowed to **only** the pinned cloudflared IP — see [`SECURITY.md`](SECURITY.md#how-nginx-identifies-the-real-client-ip) for the rationale.

### 3. Tailscale Access

- **Path**: Client → Tailscale network → Host's Tailscale interface → Host port 443 → nginx container
- **What nginx sees**: Docker gateway IP (172.x.x.x)
- **Why no headers**: Tailscale runs in `network_mode: host` for GenMaster-GenSlave communication, so no proxy headers are added

## Configuration Details

### The `geo` Block (Access Control)

```nginx
geo $access_level {
    default          "external";
    127.0.0.1/32     "internal";
    10.0.0.0/8       "internal";
    172.16.0.0/12    "internal";
    192.168.0.0/16   "internal";
    100.64.0.0/10    "internal";  # Tailscale CGNAT range
    # Custom ranges can be added via GenMaster UI
}
```

This block evaluates the client's IP (after real_ip processing) and sets `$access_level` to either "internal" or "external".

## Why Tailscale Uses `network_mode: host`

The Tailscale container uses `network_mode: host` for a critical reason:

**GenMaster must be able to reach GenSlave over Tailscale when they are NOT on the same local network.**

If Tailscale ran in a Docker bridge network:
- The Tailscale interface (100.x.x.x) would only be accessible inside the Tailscale container
- GenMaster (in its own Docker network) couldn't route to GenSlave's Tailscale IP
- This would break GenMaster-GenSlave communication when they're on different networks

With `network_mode: host`:
- The Tailscale interface is available on the host
- GenMaster can reach GenSlave via Tailscale IP (100.x.x.x) from anywhere

### Trade-off

The trade-off is that Tailscale web traffic (via *.ts.net URLs) doesn't have real client IPs in nginx logs - you'll see 172.x.x.x instead. However:

1. Tailscale traffic is already authenticated by Tailscale
2. The 172.x.x.x IP falls within the "internal" range, so access is granted
3. This is acceptable because only authenticated Tailscale users can reach the *.ts.net URL

## Summary Table

| Access Method | Nginx Sees | Access Level | Result |
|--------------|------------|--------------|--------|
| LAN (10.x.x.x) | Real IP | internal | Allowed — direct connection preserves IP |
| Cloudflare (untrusted IP) | Real IP | external | 403 — IP not in allowlist |
| Cloudflare (allowlisted IP) | Real IP | internal | Allowed — IP is in geo block |
| Tailscale | 172.x.x.x | internal | Allowed — Docker IP is in "internal" range |

## Managing Access Control

IP ranges can be managed through the GenMaster UI:
1. Navigate to Settings → Access Control
2. Add or remove IP ranges as needed
3. Changes are written to nginx.conf and nginx is reloaded automatically

The `access_control.py` service only modifies the `geo` block - it preserves all other nginx configuration including the real_ip settings.
