# Welcome to the GenMaster User Manual

This manual walks through every screen and option in the GenMaster web interface — the master controller for your distributed generator control system. Use it as a reference to find what a button does, what a status panel is telling you, or how to configure a particular feature.

## How this manual is organized

Each top-level navigation tab in GenMaster has its own page in this manual:

| Page | What it covers |
|------|----------------|
| [Generator Control](generator.md) | The home page — start/stop, arming, fuel tracking, runtime limits, exercise schedule, generator info |
| [GenSlave](genslave.md) | Remote relay controller status — health, network, failsafe, notifications, scheduled reboot |
| [Schedule](schedule.md) | Creating and managing scheduled runs |
| [Run History](history.md) | Browsing past runs with filters |
| [Notifications](notifications.md) | Apprise channels and groups, configure rules, history |
| [Containers](containers.md) | Docker container management |
| [System](system.md) | Host health, network, terminal, SSL certs, WiFi watchdog |
| [Settings](settings.md) | Appearance, security, access control, environment, account, advanced |
| [Common UI](common-ui.md) | Theme toggle, Help dialog, About dialog, login/logout |
| [Appendix](appendix.md) | Troubleshooting, glossary, security flag index |

## Layout overview

Every GenMaster page shares the same top header and main content area.

![GenMaster top navigation header](images/screenshots/common-01-header.png)

From left to right in the header you'll find:

1. **GenMaster** wordmark — links back to the home page (Generator Control)
2. **Top navigation** — one tab per major area: Generator, GenSlave, Schedule, History, Notifications, Containers, System, Settings
3. **Help & Documentation** (?) — opens the in-app help dialog with links to this manual and the GitHub repo
4. **About** (i) — shows version and build info
5. **Theme toggle** (sun/moon) — switches between light and dark mode
6. **User badge** — shows the logged-in user (default: `admin`)
7. **Logout** (door icon) — ends the current session

The top navigation is sticky: it stays visible as you scroll down any page.

## Reading conventions

This manual uses a few visual cues:

!!! note "Note"
    A clarification or extra detail.

!!! tip "Tip"
    A best practice or shortcut worth remembering.

!!! warning "Warning"
    Something that can affect operation if ignored.

!!! danger "Danger"
    Destructive action — read carefully before proceeding.

!!! example "Sensitive data"
    Indicates a screenshot contains data you may want to mask before publishing or sharing externally (IPs, hostnames, tokens).

## What you need to use GenMaster

- A browser pointed at your GenMaster instance (typically `https://<your-domain>` or `https://<tailscale-host>`)
- An admin account (default username `admin`, set the password during setup)
- A connected GenSlave on the same network (or via Tailscale) for the generator relay to function

If GenMaster reports the slave as offline, see [GenSlave](genslave.md) and the [Appendix](appendix.md) troubleshooting tables.

## Where to start

If you're new to GenMaster, read the pages in nav order — they progress from the most-used screen (Generator Control) to the least-used (Settings → Advanced). If you're looking up a specific feature, the per-page table of contents on the right side of each page makes it easy to jump straight to the section you need.
