# Troubleshooting

How to find out why an instance does not start, using the tools built into
VineOS 0.1.1-alpha.

## Table of Contents

- [Collect the facts first](#collect-the-facts-first)
- [The app closed when I started an instance](#the-app-closed-when-i-started-an-instance)
- [Which privilege level do I have](#which-privilege-level-do-i-have)
- [Shizuku and Wireless debugging](#shizuku-and-wireless-debugging)
- [An Android 7 or 8 ROM does not boot](#an-android-7-or-8-rom-does-not-boot)
- [The screen is black or stutters with Vulkan](#the-screen-is-black-or-stutters-with-vulkan)
- [Keeping instances alive in the background](#keeping-instances-alive-in-the-background)
- [Reporting a bug](#reporting-a-bug)

## Collect the facts first

Open **Settings, Logs**. The log records every action the app takes, every
status change of an instance, and every line the helper prints. Filter by
level or by tag (`engine`, `helper`, `shizuku`, `native`, `action`) and use the
search box.

From the menu you can save all logs, save only the visible ones, or save a
**diagnostic report**: one text file with the device, kernel, ABIs, Shizuku
state, the engine capability probe and the last 2000 log lines. Attach that to
a bug report.

**Settings, Terminal** runs commands against three targets: the app itself,
the host phone (with root or Shizuku) and a running guest. Useful host
commands: `getenforce`, `ls -l /dev/binder /dev/ashmem`,
`cat /proc/filesystems`, `ls /proc/sys/fs/binfmt_misc`.

## The app closed when I started an instance

0.1.0 could crash the whole app as soon as you tapped Start, when the helper
failed within a fraction of a second (for example because there was no root).
The log of such a crash ends with
`ForegroundServiceDidNotStartInTimeException: Context.startForegroundService() did not then call Service.startForeground()`.

The cause was a race. The app asked Android to start its foreground service,
the start failed immediately, and the app stopped the service again before the
service had called `startForeground`. Android treats that as a crash. From
0.1.1 the service enters the foreground in `onCreate`, and the app waits for
that confirmation before it ever stops the service. A failed start now shows
the real reason on the instance screen.

In a debug build, **Settings, Debug settings, Foreground service stress test**
repeats the start and stop sequence six times so you can confirm it on your
device.

## Which privilege level do I have

**Settings, Engine and privileges** shows the helper state and lets you pick
how VineOS gets access.

| You have | What happens |
| --- | --- |
| Root through `su` | Full support. |
| Shizuku started with root | Full support, and VineOS does not need `su` at all. |
| Shizuku started through Wireless debugging (uid 2000) | The helper runs as the ADB shell user. Most phones do not let that user create namespaces or mount images, so starting an instance fails fast with the exact refusal. |

Tap **Test namespace access** to run the check yourself. It reports whether
the Shizuku user may create namespaces and make mounts private, and the errno
if not (usually `EPERM`). That is a property of your kernel and SELinux
policy, not of VineOS. See
[the no-root research](../reference/NOROOT_RESEARCH.md) for the background.

## Shizuku and Wireless debugging

VineOS talks to Shizuku through its public API, so Shizuku forks that serve the
same API work too. If a fork uses a different package name, add it under
**Extra Shizuku package names** so VineOS can detect and open it. Detection of
whether Shizuku is running does not depend on the package name.

To start Shizuku without a computer on Android 11 or newer:

1. Connect to Wi-Fi.
2. Turn on Developer options (tap the build number seven times).
3. Turn on Wireless debugging and pair it from inside the Shizuku app.
4. Start Shizuku, return to VineOS and grant permission.

The page shows the live state of each switch. If you chose "Deny and don't ask
again", the permission dialog will not appear again. Open Shizuku and allow
VineOS under authorized apps.

## An Android 7 or 8 ROM does not boot

Check these in order. The log and the device report show most of them.

1. **Privilege.** Without root or root-backed Shizuku the helper refuses to
   start an instance. The message names the privilege level.
2. **Container-aware init.** The engine refuses a ROM whose `init` does not
   carry the VineOS marker, because an unpatched Android `init` would try to
   load its SELinux policy into your phone's kernel. Build the ROM with the
   [ROM kit](../reference/ROM_INTEGRATION.md).
3. **`/dev/ashmem`.** Android 7 and 8 create shared memory through
   `/dev/ashmem`, which recent kernels no longer ship. The device report line
   `ashmem` says whether yours has it. When it is missing the engine copies a
   memfd based shim into the instance and preloads it from `init.vine.rc`.
   Keep **Ashmem compatibility** on unless you are debugging it.
4. **32 bit processes.** The shim, like the engine, is built for the phone's
   own ABI. A 32 bit process in a dual ABI ROM cannot load a 64 bit preload
   and is aborted by the linker. That affects only 32 bit helper daemons.
5. **QEMU.** If the ROM is 32 bit only and your CPU cannot run 32 bit code,
   the engine needs `libqemu_arm.so`, a static build. The report shows its
   version and whether the kernel supports the binfmt flags the engine uses.

## The screen is black or stutters with Vulkan

Vulkan output is experimental. Open the **Logs** screen and look for the line
that starts with `Display:`. It says which presenter is in use, and when Vulkan
was skipped it also says why (no Vulkan loader, no GPU that can present to the
window, a format the GPU cannot blit to).

- `using opengles instead of vulkan`: Vulkan could not start and the fallback
  works. Nothing to fix, you can set the backend to Automatic to stop trying.
- A black screen with `using vulkan`: the GPU driver accepted the swapchain but
  shows nothing. Set the instance graphics backend to **Automatic** or
  **OpenGL ES**, and report the GPU name from the `Graphics:` line in the log.
- The log says the presenter keeps failing and switched: the fallback already
  happened, the picture continues with the next presenter.

## Keeping instances alive in the background

Disable battery optimization for VineOS first. If Android still stops an
instance, turn on **Background keep-alive**: the app then holds a CPU and a
Wi-Fi lock while an instance runs and does not shut the helper down when idle.
Some phone makers add their own restrictions. **Autostart and background
limits** opens the maker's manager where one is known, and
[dontkillmyapp.com](https://dontkillmyapp.com) lists per-brand steps.

## Reporting a bug

Open the [issue tracker](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/issues),
state the VineOS version from **About**, and attach the diagnostic report.
Read it first, it contains your device model and build fingerprint.
