# Troubleshooting

How to find out why an instance does not start, using the tools built into
VineOS 0.2.5.

## Table of Contents

- [Collect the facts first](#collect-the-facts-first)
- [The app closed when I started an instance](#the-app-closed-when-i-started-an-instance)
- [Which privilege level do I have](#which-privilege-level-do-i-have)
- [Root is refused or not found](#root-is-refused-or-not-found)
- [Shizuku and Wireless debugging](#shizuku-and-wireless-debugging)
- [The virtual machine does not start](#the-virtual-machine-does-not-start)
- [The machine stops after a while](#the-machine-stops-after-a-while)
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
0.2.0 the service enters the foreground in `onCreate`, and the app waits for
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
| Shizuku started through Wireless debugging (uid 2000) | The helper runs as the ADB shell user. Most phones do not let that user create namespaces or mount images, so starting an instance with the container engine fails fast with the exact refusal. |
| Nothing | The container engine cannot start. ROMs with a virtual machine profile still boot through the virtual machine engine, see [The virtual machine does not start](#the-virtual-machine-does-not-start). |

Tap **Test namespace access** to run the check yourself. It reports whether
the Shizuku user may create namespaces and make mounts private, and the errno
if not (usually `EPERM`). That is a property of your kernel and SELinux
policy, not of VineOS. See
[the no-root research](../reference/NOROOT_RESEARCH.md) for the background.

## Root is refused or not found

VineOS finds out whether it has root by asking for it (`su -c id`), because
looking for a `su` file is not enough. The message on the start screen says
what happened:

| Message says | What to do |
| --- | --- |
| The manager refused VineOS | Open KernelSU, KernelSU Next, SukiSU Ultra or APatch, go to **Superuser** and switch VineOS on. These managers have no prompt, so an app that is not switched on is refused without a question. Then start again. |
| The manager did not answer in time | Magisk showed a prompt, or was waiting to, and nobody answered within 30 seconds. Open Magisk and allow VineOS. If the prompt never shows, exclude VineOS from battery optimisation and check that notifications of the manager are allowed. |
| `su` is not answering | A kernel based manager is installed, but `su` did not start for VineOS. Switch VineOS on in its Superuser list and try again. |
| Root is not available on this phone | No manager and no `su`. Use a ROM with a virtual machine profile, or root the phone. |

A granted request is remembered for two minutes so that starting several
instances in a row does not prompt every time. In a debug build, **Debug
settings, Re-detect su** and **Run a root probe** repeat the check and write
the result to the log, and **Simulate a refused root request** lets you see the
refusal message.

## Shizuku and Wireless debugging

VineOS talks to Shizuku through its public API, so Shizuku forks that serve the
same API work too. If a fork uses a different package name, add it under
**Extra Shizuku package names** so VineOS can detect and open it. Detection of
whether Shizuku is running does not depend on the package name. Forks that keep
the original package name (the-dj-chi, for example) are told apart by their
version name, and a Shizuku with no visible app (Sui, or a fork in stealth mode)
is found through its running service, so the card on **Engine and privileges**
still reports it.

To start Shizuku without a computer on Android 11 or newer:

1. Connect to Wi-Fi.
2. Turn on Developer options (tap the build number seven times).
3. Turn on Wireless debugging and pair it from inside the Shizuku app.
4. Start Shizuku, return to VineOS and grant permission.

The page shows the live state of each switch. If you chose "Deny and don't ask
again", the permission dialog will not appear again. Open Shizuku and allow
VineOS under authorized apps.

## The virtual machine does not start

These apply to the engine that needs no root.

- **"This ROM does not include a virtual machine profile"**: the `.vrom` has no
  `vm` section, so only the container engine can run it. Use a ROM that has
  one, or give VineOS root or Shizuku with root.
- **"This build of VineOS does not include the QEMU engine"**: the app was built
  without `libqemu_system_aarch64.so` or `libqemu_system_arm.so`. Check with
  **Settings, Developer, Check the machine engine**. Official builds are meant
  to ship them, a build from source needs
  [the QEMU step](BUILDING.md#building-the-qemu-machine-engine).
- **"The guest did not draw anything within 120 seconds"**: QEMU started and
  the kernel may be running, but nothing reached the display. The message ends
  with the last console line. **Show diagnostics** on the instance has the
  console tail, and `console.log` in the instance folder has all of it. A first
  boot of a full Android image under emulation is slow, so on a slow phone raise
  the boot timeout in a debug build before assuming a hang.
- **A black screen after the logo**: the ROM's kernel or userspace has no
  driver for the virtual GPU or draws to something else. Read
  [Booting as a virtual machine](../reference/ROM_INTEGRATION.md#booting-as-a-virtual-machine).
- **Touch does nothing**: without the guest agent, input is a VNC pointer, which
  needs `virtio-tablet` support in the guest. Start the agent from the ROM for
  real multi-touch.
- **Extra QEMU arguments are refused**: VineOS owns the machine, disks, display
  and control sockets, and refuses options that would replace them. The message
  names the option.
- **Slow**: it is emulation. Raise **Translation cache** in **Settings,
  Developer**, give the instance more CPU cores, and prefer the Vulkan or OpenGL
  ES display over software.

## The machine stops after a while

If the instance leaves the running state on its own and the error says Android
stopped the virtual machine (QEMU ended with signal 9), Android 12 or newer
killed it as a phantom process. Apps are allowed a limited number of child
processes and QEMU is one.

1. Tap **Stop Android from killing VineOS** in **Settings, Engine and
   privileges**. It needs root or Shizuku. It lifts the background process
   limit, exempts VineOS from Doze, allows background running and sets the
   active standby bucket, and shows which steps worked.
2. On Android 14 and newer, also turn on **Disable child process restrictions**
   in Developer options. It is a separate switch.
3. Keep battery optimisation off for VineOS, see
   [Keeping instances alive in the background](#keeping-instances-alive-in-the-background).

Without root or Shizuku, the same can be done once from a computer with
`adb shell`. On Android 12L and newer:

```bash
settings put global settings_enable_monitor_phantom_procs false
```

On Android 12 (API 31):

```bash
device_config set_sync_disabled_for_tests persistent
device_config put activity_manager max_phantom_processes 2147483647
```

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

Open the **Logs** screen and look for the line
that starts with `Display:`. It says which presenter is in use, and when Vulkan
was skipped it also says why (no Vulkan loader, no GPU that can present to the
window, a format the GPU cannot blit to).

- `using opengles instead of vulkan`: Vulkan could not start and the fallback
  works. Nothing to fix. Set the backend to OpenGL ES to stop trying.
- A black screen with `using vulkan`: the GPU driver accepted the swapchain but
  shows nothing. Set the instance graphics backend to **OpenGL ES**
  and report the GPU name from the `Graphics:` line in the log.
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
