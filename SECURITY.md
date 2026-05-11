# Security Policy

## Supported Versions

This project is pre-1.0. Only the latest `main` branch is actively
supported with security fixes.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| Other   | :x:                |

## Reporting a Vulnerability

If you discover a security issue in this project, please **do not** open
a public GitHub issue. Email the maintainer directly:

- **richardjsears@protonmail.com**

Include reproduction steps and the affected version (image SHA or git
commit). The project is maintained by one person on a hobby schedule,
but I take security issues seriously and will respond as fast as I can.

## Scope

This is a single-owner-operator project, not designed for multi-tenant
or untrusted environments. The full threat model, trust boundaries, and
hardening checklist live in [`docs/SECURITY.md`](docs/SECURITY.md) —
read that for the complete security story.
