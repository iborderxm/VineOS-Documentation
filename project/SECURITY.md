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
- The root helper: any way for another app or a guest to make it run commands or touch files outside the instances directory
- The guest agent link (`agent.sock`) and the home screen shortcut intent handling
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

VineOS uses Linux namespaces (PID, mount, UTS, IPC and network) and cgroups
for guest isolation. This provides meaningful but not absolute isolation; it
is not a hypervisor. The security model assumes:

1. The guest ROM image is trusted (downloaded and SHA-256 verified by VineOS)
2. The host is not already compromised, and the user trusts the apps they
   grant root to
3. Only the VineOS app can talk to the root helper it started

Things worth knowing before running a guest:

- **There is no user namespace.** Root inside a guest is root on the phone,
  limited only by the guest's own mounts, namespaces and cgroup limits. A
  malicious ROM must be assumed able to escape. Only run ROMs you trust.
- **The root helper** (`libvine_helper.so`) is started by the app with `su`
  and talks to it only over the standard input and output of that process, so
  no other process can send it commands. It accepts file paths only below the
  instances directory it was started with, validates instance ids, package
  names and snapshot names, and exits, killing every guest, when the app goes
  away. A compromise of the app process is therefore a compromise of whatever
  the helper can do as root.
- **Unpatched `init` is refused.** An unmodified Android `init` loads its
  SELinux policy into the kernel it runs on, which here is the phone's. The
  engine refuses to start a ROM whose `init` does not carry the
  `VINE_CONTAINER_INIT_V1` marker. The marker is a promise by the ROM author,
  not a verification of the patch.
- **Home screen shortcuts** launch `MainActivity` with a custom action. The
  activity is exported so launchers can use it, which means any app can send
  that intent. It can only start one of the user's own instances and open an
  app in it, and the instance id and package name are validated, but the
  exposure exists.
- **The guest agent socket** lives in the instance's shared folder, which the
  guest can write to. The helper treats everything it reads from the agent as
  untrusted data and limits the size of replies.

Root-required features (Magisk inside instances) are opt-in and explicitly
documented as reducing the isolation boundary. See
[ARCHITECTURE.md](../reference/ARCHITECTURE.md#security-model) for the full
threat model.
