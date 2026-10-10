# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch | Active development |
| Tagged releases | Critical fixes backported |
| Older releases | No longer supported |

VineOS is pre-1.0. Once 1.0 is released, this policy will be updated to
cover the current stable release and the previous minor version.

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Report security issues privately by opening a confidential issue on GitLab.
Tick **This issue is confidential** before submitting, so that only project
members can see it:

**[Report a vulnerability](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/issues/new)**

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce, with affected Android version and device model if relevant
- Any proof-of-concept code or screenshots
- A suggested fix if you have one

## Response Timeline

| Step | Target time |
|------|-------------|
| Acknowledgement | 48 hours |
| Initial assessment | 5 business days |
| Fix for critical issues | 7 days |
| Fix for moderate issues | 30 days |
| Public disclosure | After fix is released |

## Scope

In scope:

- Container namespace escape (guest process reaching the host filesystem or processes)
- QEMU binfmt_misc misconfiguration enabling arbitrary code execution on the host
- VineRuntime JNI vulnerabilities allowing privilege escalation
- ROM download integrity bypass (SHA-256 verification)
- VineService foreground service abuse

Out of scope:

- Vulnerabilities requiring physical device access
- Issues in upstream dependencies (QEMU, AOSP); report those upstream instead
- Theoretical vulnerabilities with no practical exploit path
- Issues in the Android OS itself

## Automated dependency scanning

Two automated checks help catch dependency-related and credential-leak
issues before they reach `main`. Renovate (`renovate.json`) opens merge
requests to keep Gradle dependencies and CI images current, and flags
dependencies with known vulnerabilities. GitLab's secret detection job
scans every pipeline for committed credentials. Neither replaces manual
review of security-sensitive changes.

## Security Design Notes

VineOS uses Linux namespaces (PID, mount, UTS, IPC) for guest isolation.
This provides meaningful but not absolute isolation; it is not a
hypervisor. The security model assumes:

1. The host device is not rooted by an attacker (the attacker has normal
   Android app sandbox privileges)
2. The guest ROM image is trusted (downloaded and SHA-256 verified by VineOS)
3. SELinux is enforcing on the host

Root-required features (Magisk inside instances) are opt-in and explicitly
documented as reducing the isolation boundary. See
[ARCHITECTURE.md](../reference/ARCHITECTURE.md#security-model) for the full threat model.
