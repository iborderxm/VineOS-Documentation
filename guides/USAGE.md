# Using VineOS

This is a guide to using the VineOS app itself: downloading ROMs, creating
and running instances, and what the settings do. For building the app from
source, see [BUILDING.md](BUILDING.md); for how it works internally, see
[ARCHITECTURE.md](../reference/ARCHITECTURE.md).

## Table of Contents

- [Before you start: is your device compatible?](#before-you-start-is-your-device-compatible)
- [Downloading a ROM](#downloading-a-rom)
- [Creating an instance](#creating-an-instance)
- [First run](#first-run)
- [Engines: with and without root](#engines-with-and-without-root)
- [Running an instance](#running-an-instance)
- [Display and navigation buttons](#display-and-navigation-buttons)
- [Graphics backend](#graphics-backend)
- [Home screen shortcuts](#home-screen-shortcuts)
- [Managing instances](#managing-instances)
- [Snapshots](#snapshots)
- [Settings](#settings)
- [Developer options](#developer-options)
- [Root access inside a guest](#root-access-inside-a-guest)
- [Understanding the compatibility badges](#understanding-the-compatibility-badges)
- [Troubleshooting](#troubleshooting)

> **Where things stand.** Both engines, the app and the guest protocols are
> built and tested on a host. No real Android ROM has booted inside VineOS
> yet, so an instance only starts a ROM that carries the guest side kit
> described in [ROM_INTEGRATION.md](../reference/ROM_INTEGRATION.md). The
> container engine needs root, or Shizuku started with root. The virtual
> machine engine needs nothing, but it needs a ROM with a virtual machine
> profile and a build of VineOS that includes the QEMU libraries (the
> [Building](BUILDING.md#building-the-qemu-machine-engine) guide explains how
> they are made). Shizuku started through Wireless debugging runs as the ADB
> shell user, which most phones do not allow to create the namespaces the
> container engine needs; the [Troubleshooting](TROUBLESHOOTING.md) guide
> explains how to check yours.

## Before you start: is your device compatible?

VineOS needs `minSdk` 26 (Android 8.0) or newer, and works on `arm64-v8a`,
`armeabi-v7a`, `x86_64`, and `x86` devices. You can check your device's
supported ABIs from **Settings → About → Host ABI** inside the app, which
mirrors what `adb shell getprop ro.product.cpu.abilist` reports.

Not every ROM runs equally well on every device: a ROM built only for
32-bit ARM will run through hardware emulation (slower) on an x86_64
device, but natively (fast) on an `armeabi-v7a` or capable `arm64-v8a`
device. The [ROMs tab](#understanding-the-compatibility-badges) shows
exactly what to expect before you download anything.

## Downloading a ROM

1. Open the **ROMs** tab.
2. Each entry shows the Android version, size, and which guest CPU
   architectures it supports.
3. Tap a ROM to see its full detail page: description, supported ABIs with
   per-ABI compatibility, and whether it includes 32-bit app support.
4. Tap **Download**. VineOS verifies the download's SHA-256 hash before
   marking it ready; a corrupted or interrupted download is flagged rather
   than silently used.

ROMs are minimal AOSP builds targeting a virtual hardware platform, not
your device's specific hardware, so don't expect vendor camera apps or
carrier bloatware inside a guest. That's intentional.

## Creating an instance

Tap **New instance** on the Instances tab. Everything happens on one screen:

1. **ROM**: swipe through your downloaded ROMs and pick one. If you have none
   yet, the screen offers a button that takes you to the ROMs tab.
2. **Name**: filled in from the ROM, and made unique if you already have an
   instance with that name.
3. **Performance**: *Light* (1 GB, 2 cores), *Balanced* (your defaults) or
   *Fast* (half of your phone's RAM and a higher CPU priority).
4. **Advanced options** (collapsed by default): icon, memory, storage (any size
   up to your free space; the disk is a sparse file, so it only uses what the
   guest writes), CPU cores, graphics backend, device identity (see
   [Device identity](DEVICE_IDENTITY.md)) and, when allowed in Settings, root.
5. Tap **Create instance**. VineOS unpacks the ROM and returns you to the home
   screen. Start it from there when you are ready.

You can still open a ROM's detail page and create an instance from there. It
opens the same screen with that ROM already selected.

Everything you chose, and more, can be changed later under **Instance
settings** (the slider icon on the instance page, or the card's menu).

## First run

The first launch shows a short setup: language, theme (with a live preview),
permission checks (notifications, storage access, battery optimization),
privileged access (root or Shizuku) and the
[User Agreement](../project/USER_AGREEMENT.md) with the
[Privacy Policy](../project/PRIVACY.md). Nothing except accepting the agreement
is required, and every step can be repeated later under Settings.

## Engines: with and without root

VineOS can run a ROM two ways, and **Settings, Engine and privileges** has the
**Engine** choice:

| Engine | What it needs | Speed |
|---|---|---|
| Container | Root, or Shizuku started with root. A ROM with container images | Fast. The guest runs on your phone's own CPU and kernel |
| Virtual machine | Nothing. A ROM with a virtual machine profile | Slower. QEMU emulates a CPU, so expect a fraction of native speed |
| Automatic (default) | Either of the above | Container when it can start, virtual machine when it cannot |

So to boot a ROM **without root**, use a ROM that carries a virtual machine
profile (its release notes say so, and `package_vrom.py --vm-kernel` is how one
is made), leave the engine on Automatic or choose Virtual machine, and start
it. No Shizuku, no Wireless
debugging and no computer are needed. If a ROM has no virtual machine profile
and you have no privileged access, the app says so instead of failing later.

The container engine asks for root when an instance starts. VineOS recognises
Magisk, KernelSU, KernelSU Next, SukiSU Ultra and APatch. KernelSU, KernelSU
Next, SukiSU Ultra and APatch have no prompt, so switch VineOS on in the
**Superuser** list of the manager first, otherwise the request is refused and
the app tells you so. With Magisk, allow the prompt when it appears.

Shizuku and its forks (for example the-dj-chi) work too, including a server
that has no visible app. Under Engine and privileges the Shizuku card says
which one VineOS found.

A virtual machine is a child process of VineOS, and Android 12 and newer can
kill such processes. If a machine stops by itself after a while, tap **Stop
Android from killing VineOS** in the same settings page (it needs root or
Shizuku), and on Android 14 and newer also turn on **Disable child process
restrictions** in Developer options. See
[Troubleshooting](TROUBLESHOOTING.md#the-machine-stops-after-a-while).

## Running an instance

From the **Instances** tab, tap an instance's play button to boot it, or
tap the card itself to see its detail page first. A running instance shows
a live status indicator (booting, running, error) and can be stopped from
either the home screen or its detail page.

Once booted, the instance opens full-screen. Touch input, including
multi-touch with up to ten fingers, is forwarded to the guest as if it were a
real touchscreen. See [Display and navigation buttons](#display-and-navigation-buttons)
for the on-screen controls.

Instances keep running in the background (via a foreground service, with
a persistent notification) if you switch away from VineOS, so you can use
other apps while a guest stays booted.

## Display and navigation buttons

The guest screen fills the whole phone. The status bar and the system
navigation bar are hidden while an instance is open, and swiping from the
edge shows them for a moment.

- **Screen fit** in Settings decides the shape of the guest screen. *Fill the
  whole screen* gives the guest your phone's own aspect ratio, so there is no
  empty space at the top or bottom. *Keep 9:16 shape* keeps a classic phone
  shape with black bars.
- **Guest resolution** trades sharpness for speed. High renders the long side
  at 1920 pixels, Balanced at 1280, Low at 960. A lower setting costs less
  CPU.
- **Avoid camera cutout** keeps the guest below the notch or camera hole.
- **On-screen buttons** controls the three round back, home and recents
  buttons:
  - *Hidden* (default): no buttons. The phone's back gesture acts as Back
    inside the guest. Touch the screen with three fingers to show the
    controls, which also hold Exit and Stop.
  - *Tap to show*: a small handle at the top. Tap it and the buttons appear
    for a few seconds.
  - *Always visible*: the buttons stay on top of the guest screen.

A changed guest resolution applies the next time an instance starts.

## Graphics backend

The graphics backend decides how the guest draws and how your phone shows the
result. Set the default in **Settings, Virtual machine defaults**, or per
instance in the instance settings.

| Backend | What it does |
|---|---|
| Automatic | The ROM picks the guest renderer. The phone presents frames through Vulkan when VineOS found a Vulkan GPU it can present to, and through OpenGL ES otherwise |
| OpenGL ES | The guest renders with OpenGL ES and the phone draws frames with an OpenGL ES texture. The safe choice |
| Vulkan | The guest uses Vulkan on Android 10 and newer ROMs and the phone presents frames through a Vulkan swapchain |
| Software | Everything on the CPU. Slowest, but it works everywhere |

Vulkan only appears in the list on phones where VineOS found a Vulkan GPU it
can present to. It is a regular, supported choice and the one Automatic prefers
on those phones, which matters most for games. The presenter rebuilds its
swapchain when the window changes size (split screen, a folded or unfolded
phone). If Vulkan cannot start or the driver keeps losing the device or
surface, VineOS falls back to OpenGL ES, and then to software, by itself. The
**Logs** screen shows which one is in use, on a line that starts with
`Display:`, and **Settings, Developer, Display statistics** shows it over the
guest screen. If you hit a Vulkan problem, switch the instance to OpenGL ES and
include the log in your bug report.

## Home screen shortcuts

Put an app from inside an instance on your home screen. Tapping the shortcut
starts the instance right away and opens the app as soon as the guest has
booted.

1. Open **Settings → App Shortcuts**.
2. Pick an instance. The list shows the apps installed inside it. If the
   instance has never been listed, start it once from this screen and the
   list is read from the running guest, then remembered, so the picker also
   works while the instance is off.
3. Tap an app. Android asks to add the shortcut and uses the app's name and
   icon. If the guest could not provide the icon, the VineOS icon is used.
4. If the instance is already running, the shortcut only opens the app.

The shortcut depends on the guest agent listed in
[ROM_INTEGRATION.md](../reference/ROM_INTEGRATION.md). A ROM without the agent
still starts from the shortcut, but the app list and the automatic opening of
the app are unavailable.

## Managing instances

From an instance's detail page you can see its RAM/storage allocation,
when it was created and last used, and (with **Show diagnostics**) a raw
dump of the container's current state, mount table, and QEMU status,
useful when filing a bug report. The diagnostics end with the tail of the
instance's boot log, which is the first place to look when a ROM fails to
start. Deleting an instance removes its storage permanently and can't be
undone; an instance must be stopped first.

## Snapshots

A snapshot is a copy of an instance's `/data` disk, the apps and files you
installed inside it. On the instance's detail page tap **Create snapshot**. It is named after
the date and time, and later you pick **Restore** next to it to go back, or
delete it to free the space.

- Snapshots copy only the parts of the disk that hold data, so a mostly empty
  disk makes a small snapshot. There must be enough free space for the copy.
- Creating a snapshot of a running instance freezes it for the length of the
  copy so the disk does not change underneath it. If the phone cannot freeze it, stop the
  instance first.
- A snapshot is a disk copy, not a memory snapshot. Restoring it behaves like
  pulling the plug and booting again.
- Restoring replaces the current disk and needs the instance to be stopped.

## Settings

| Page | What it covers |
|---|---|
| Appearance | A dark mode switch. Tapping the row (not the switch) opens the dark mode options: follow system, light, dark and AMOLED pure black. Also Material You colors, seven accent colors, animation level (full, reduced, off), haptics and keep screen on |
| Language | English, French, Spanish, Chinese, Russian, German, Polish, Hungarian, Portuguese, Arabic, Dutch, Italian, Japanese and Korean. The app follows your phone's language and falls back to English. Arabic mirrors the layout |
| Virtual machine defaults | Memory, storage, CPU cores, graphics backend (automatic, OpenGL ES, Vulkan, software), frame rate limit, performance profile, guest internet, ashmem compatibility, rooted instances, technical info |
| Display | Screen fit, guest resolution, on-screen buttons, camera cutout, see [Display and navigation buttons](#display-and-navigation-buttons) |
| Engine and privileges | The engine (automatic, container, virtual machine), how VineOS gets access (automatic, root, Shizuku), the root managers found, Shizuku status and extra package names for forks, the namespace test, Wireless debugging steps, **Stop Android from killing VineOS**, background keep-alive, battery optimization, idle shutdown, device report |
| Developer | Options for the virtual machine engine, see [Developer options](#developer-options) |
| App shortcuts | Put an app of an instance on your home screen, see [Home screen shortcuts](#home-screen-shortcuts) |
| Terminal | Run commands in the app, on the host phone or in a running guest |
| Logs | Every action and message, filterable, savable and shareable, plus a diagnostic report |
| Legal and About | User Agreement, Privacy Policy, licenses, version, developer and contributors. **More** holds the detailed build, engine and device information |

Debug builds add a **Debug settings** page.

## Developer options

**Settings, Developer** is in every build, not only debug builds. The defaults
are right for most phones.

| Option | What it does |
|---|---|
| Display statistics | Shows the renderer in use, frame rates and the guest size over the guest screen |
| Translation cache | The size of QEMU's code cache (64 to 1024 MB). A bigger cache makes the virtual machine faster and uses more memory |
| Extra QEMU arguments | Added to the end of the QEMU command line, up to 32 arguments. Quote values that contain spaces. Options VineOS manages itself (the machine, disks, display, control sockets and so on) are refused, and the app says which |
| Check the machine engine | Runs the bundled QEMU for each architecture with `--version` and shows the result, or "Not included in this build" |

Debug builds add a **Debug settings** page with more switches (force a display
presenter, simulate a refused root request, disable the guest agent, trace the
display link, boot timeout, helper simulations) and tools (root probe, root
manager and tuning logs, graphics probe, machine engine check, settings dump
and resets).

## Root access inside a guest

Root support (via Magisk-style tooling) is opt-in and off by default. It's
scoped to the guest, granting elevated privileges *inside that instance's
own sandbox*, not on your host device. Enabling it does narrow that
instance's isolation boundary; see
[SECURITY.md](../project/SECURITY.md#security-design-notes) if you want the full
technical detail before turning it on.

## Understanding the compatibility badges

Each guest ABI a ROM supports is labeled with how your specific device
will run it:

| Badge | Meaning |
|---|---|
| **Native** | Runs directly on your device's CPU, best performance |
| **QEMU** | Runs through instruction-level emulation, works but slower |
| **Incompatible** | Can't run at all on your device, usually a 32-bit host trying to run a 64-bit guest |

A ROM card is grayed out and undownloadable if every ABI it supports comes
back incompatible for your device. See
[ARCHITECTURE.md](../reference/ARCHITECTURE.md#abi-compatibility) for the full
host/guest compatibility matrix if you're curious why a specific
combination lands where it does.

## Troubleshooting

The full guide, with the log viewer, diagnostic report and an Android 7 boot
checklist, is in [TROUBLESHOOTING.md](TROUBLESHOOTING.md). Quick answers:

**An instance won't boot / gets stuck on "Booting"**
Check its diagnostics panel for mount or namespace errors. If the ROM
shows a QEMU badge for your device, first boots can take noticeably
longer than a natively-running one.

**Downloads keep failing SHA-256 verification**
Usually an unstable connection. Delete the partial download from the
ROM's detail page and try again on a more stable connection.

**The app is slow or my battery drains fast with an instance running**
A running instance is a full Android system doing real work, similar to
running a resource-heavy app. QEMU-emulated instances cost more CPU than
natively-running ones; check the compatibility badge before committing to
a ROM if this matters to you.

**The instance fails with "init is not container aware"**
The ROM's `init` does not carry the VineOS marker, so VineOS refuses to start
it. An unpatched Android `init` would load its SELinux policy into your
phone's kernel. The ROM needs the patch described in
[ROM_INTEGRATION.md](../reference/ROM_INTEGRATION.md).

**It says root is required**
The engine runs in a helper started with `su`. Grant the superuser prompt, or
check that your root manager lists VineOS. A no-root path is still on the
roadmap.

**The guest has no internet**
Check **Guest internet access** in Settings. Networking needs the `ip` and
`iptables` tools on the phone and is best effort: when it cannot be set up the
guest still boots, just offline.

**I can't find a "Create Instance" option**
It only appears on a downloaded ROM's detail page (ROMs tab → tap a ROM →
Create Instance), not directly from the Instances tab.

For anything not covered here, ask in the
[VineOS Discord](https://discord.gg/sVgCAdgGgR), check existing
[GitLab issues](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/issues) or open a
new one with the details listed in
[CONTRIBUTING.md](../project/CONTRIBUTING.md#issue-reporting).
