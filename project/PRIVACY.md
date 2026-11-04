# Privacy Policy

**Last updated: October 2026**

VineOS is a free, open-source Android app. This policy explains what data
it handles and, just as importantly, what it doesn't.

## Summary

VineOS does not have user accounts, does not run analytics or crash
reporting, does not display ads, and does not send your data to VineOS
project maintainers or any third party. Everything the app stores lives on
your device. The source code backing every claim below is public; see
[ARCHITECTURE.md](../reference/ARCHITECTURE.md) for where each piece lives.

## Data VineOS stores on your device

| Data | Where | Purpose |
|---|---|---|
| VM instance metadata (name, RAM/storage size, status) | Local Room database (`VineDatabase`) | Lets the app list and manage your instances |
| App settings (theme, language, default RAM, privilege mode, keep-alive, etc.) | Jetpack DataStore preferences | Remembers your configuration between launches |
| Per-instance settings, including the device identity values you enter for spoofing (brand, model, serial, Android ID, fingerprint) | Local Room database | Applies your choices inside that instance only |
| The in-app log (a memory buffer of recent events) and, only if you turn it on, a log file | App memory, and the app cache folder when file logging is on | Lets you and contributors diagnose problems |
| Downloaded ROM images and per-instance rootfs data | App-private storage (`context.filesDir`) | Runs the guest Android systems you create |

None of this leaves your device unless you explicitly export or share it
yourself (for example, saving logs or a diagnostic report and attaching it to
a bug report). A diagnostic report contains technical details about your
device and can include its build fingerprint, so read it before sharing.
Device identity values you configure are written into the guest instance
only. Apps inside that instance may send them to their own servers, which is
outside VineOS and this policy.

## Network requests VineOS makes

The only outbound network activity is:

- **Fetching the ROM manifest and downloading ROM images** you choose to
  download, from the VineOS ROM distribution CDN, over HTTPS
- Standard OS-level requests (like DNS resolution) needed to make those
  connections work

VineOS does not phone home on startup, does not check for updates outside
what your app store or the GitLab Releases page already do, and does not embed
any advertising or analytics network calls.

## Permissions and why VineOS asks for them

| Permission | Why |
|---|---|
| Internet / network state | Downloading ROM images and checking connectivity before a download |
| Foreground service | Keeping a running VM instance alive while you use other apps |
| Post notifications | Showing the required foreground service notification, and download progress |
| Storage / media (scoped by Android version) | Reading ROM files you import manually, and future host-to-guest file sharing |
| Wake lock and Wi-Fi lock | Preventing the device from sleeping mid-boot or mid-download, and, only when you turn on Background keep-alive, while an instance runs |
| Ignore battery optimizations | Optional. Stops Android from freezing a running instance. VineOS only opens the system screen where you decide |
| All files access | Optional. Lets VineOS read ROM files and write exported logs on shared storage. Imports also work without it through the system file picker |
| Vibrate | Haptic feedback on touch input inside a running instance |

VineOS requests each permission only where the corresponding feature is
used, and none of them are used to collect data about you.

## Privileged access and the Terminal

VineOS uses root or Shizuku only to run its engine and the commands you type
into the Terminal. The Terminal does not run anything on its own. Command
output stays in the app and is discarded when you leave the screen unless you
copy, save or share it.

## Guest operating systems

Each VM instance runs a full, separate Android system image (a "ROM") that
you download and choose to run. Apps you install *inside* that guest
environment have their own privacy behavior, entirely independent of
VineOS and outside this policy's scope. Treat a VineOS guest like you
would any other Android device: review what you install into it.

## Root access (Magisk)

If you opt in to root support for an instance, you're granting elevated
privileges *inside that guest's sandbox*, not on your host device or
within VineOS itself. This is documented further in
[SECURITY.md](SECURITY.md#security-design-notes) and is off by default.

## Children's privacy

VineOS is a general-purpose systems tool and isn't directed at children.
It doesn't knowingly collect any data from anyone, of any age, since it
doesn't collect data at all in the sense this policy covers.

## Open source

VineOS is licensed under GPL-3.0. You (or anyone) can read the full source
at [gitlab.com/Hexadecinull/VineOS/VineOS](https://gitlab.com/Hexadecinull/VineOS/VineOS)
and verify every statement in this document directly against the code.

## Changes to this policy

If VineOS ever adds a feature that changes what's described here (for
example, an opt-in crash reporter), this document will be updated first,
and the change will be called out in the release notes for that version.

## Contact

Questions about this policy can be raised as a
[GitLab issue](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/issues). For
anything security-sensitive, use the process in
[SECURITY.md](SECURITY.md) instead of a public issue.
