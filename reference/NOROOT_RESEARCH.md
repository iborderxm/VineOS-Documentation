# No-root path research: ADB shell privilege elevation

Notes toward Phase 4 of the [roadmap](https://gitlab.com/Hexadecinull/VineOS/VineOS#roadmap). It began as a technical brief to
decide *whether* the Shizuku/Virtual Master technique gets VineOS far enough
to be worth building. The Shizuku part is built (0.2.0). The no-root answer
VineOS ships is a different one, described in
[Update for 0.2.5](#update-for-025-the-no-root-path-is-a-machine-not-a-container).

## What Virtual Master and Shizuku actually do

Both are closed-source (Virtual Master) or open-source (Shizuku), but
Shizuku's mechanism is fully documented and Virtual Master is understood
to work the same way: they start a background process authenticated as
the **ADB shell user (UID 2000)** instead of the app's own UID, using
Android's Wireless Debugging feature (Developer options → Wireless
debugging, Android 11+) to do this entirely on-device with no PC:

1. The app enables Wireless Debugging via `WRITE_SECURE_SETTINGS` (a
   permission normal apps can be granted without root, either by the
   user via `adb shell pm grant` once, or by some apps via an
   accessibility-service-driven UI walk).
2. It runs an embedded ADB client that pairs with the device's own
   `adbd` over `127.0.0.1`, using the same TLS pairing-code protocol a
   desktop `adb pair` would use. The phone is simultaneously the ADB
   host and the ADB target.
3. Once paired and connected, it starts a helper process (`app_process`
   running a Java entrypoint, in Shizuku's case) via the ADB shell
   connection. That process inherits the **`shell`** SELinux domain and
   UID 2000, not the app's own `untrusted_app` domain and app UID.
4. Other apps talk to that helper over Binder IPC as a broker: "ask
   shell to do X on my behalf."

This is a real, working technique, confirmed by both Shizuku's own docs
and a third-party technical writeup of malware replicating the same
flow (HackTricks). It needs Android 11+ for the on-device pairing step;
older versions need a one-time PC-based `adb` pair.

## What shell (UID 2000) actually unlocks, confirmed from AOSP sepolicy

I pulled the current AOSP `system/sepolicy` source directly rather than
going on secondhand descriptions, since this is the part that decides
whether the technique is useful for VineOS specifically.

**Confirmed: `untrusted_app` (what VineOS's own process runs as today)
is flatly blocked from cgroups, full stop:**

```text
# private/app_neverallows.te
neverallow all_untrusted_apps cgroup:file *;
neverallow all_untrusted_apps cgroup_v2:file *;
```

This directly affects the RAM/CPU cgroup limiting added in the last
round of changes (`Container::setup_resource_limits()`): on a stock
device with SELinux enforcing, that code cannot work from VineOS's own
process, full stop. No capability workaround fixes an SELinux
`neverallow`. It's consistent with the project's own documented
"currently requires CAP_SYS_ADMIN" status; I'm calling it out
specifically because it's the concrete mechanism behind that
requirement for this one subsystem.

**Confirmed: `shell` gets read access to cgroups, not write:**

```text
# private/shell.te
r_dir_file(shell, cgroup)
r_dir_file(shell, cgroup_v2)
```

`r_dir_file` is search/open/read/getattr only. I did not find a write
grant for shell on cgroup files in the base AOSP policy. So moving the
cgroup-limiting code to run as shell (via a Shizuku-style helper)
would not obviously unlock it either. Shell can read `/sys/fs/cgroup`
(that's how `top`/`dumpsys` work), not write to it. Real `adb`-driven
priority/resource controls I'm aware of (e.g. what `am`/`cmd` commands
do) go through a Binder call to `system_server`, which does the actual
cgroup write itself, rather than the shell process writing cgroup files
directly.

**Not confirmed either way: whether shell can `mount()` / `pivot_root()`
/ `unshare()` the namespace types VineOS's container engine needs.**
I did not find an explicit capability grant (`allow shell self:capability
sys_admin`) in `shell.te`, and didn't find a `neverallow` blocking it for
app domains either, in the files I was able to pull. This needs an
empirical answer, not more source-reading. See "Next step" below.

## The one path that doesn't depend on any of the above

Regardless of what shell can or can't do, `CLONE_NEWUSER` (creating an
*unprivileged* user namespace) does not require `CAP_SYS_ADMIN` from any
UID, app or shell, as long as the kernel allows it
(`CONFIG_USER_NS_UNPRIVILEGED` / `kernel.unprivileged_userns_clone`,
device-dependent) and SELinux doesn't specifically block `userns_create`
for the calling domain. Inside that new namespace the calling process
becomes "fake root" with real `CAP_SYS_ADMIN`, but only over resources
created within that same namespace (a new mount namespace, new pid
namespace, etc.), which is the standard rootless-container technique
used by `bubblewrap`, `podman`, and `unshare --map-root-user`.

This is the one mechanism that could plausibly work from an
**untrusted_app process with no ADB/shell involvement at all**, if the
device's kernel and SELinux policy allow it. It's also the one AOSP has
been actively locking down over the years specifically because it's a
common kernel-exploit surface, so it is genuinely device/vendor/Android-
version dependent, more so than most of what's in `namespace_manager.cpp`
today.

## Net assessment

- The shell/Wireless-Debugging route is real and gets VineOS a
  meaningfully more privileged domain than a plain app, for free, with
  no root prompt. But based on what I could verify from the actual
  policy source, it does **not** obviously clear the specific bar
  `namespace_manager.cpp` needs (`CAP_SYS_ADMIN` for mount/pivot_root,
  cgroup writes). Shell looks read-mostly for exactly the things this
  project needs to write.
- The `CLONE_NEWUSER` unprivileged-namespace route is the one with a
  real shot at working without *any* elevation (root or shell), but its
  availability is the least predictable of the three, since it's
  exactly the kind of thing OEMs and newer AOSP releases restrict.
- Realistically, the strongest no-root path is probably **both
  combined**: use Wireless Debugging to get a shell-domain helper
  running (for the things shell demonstrably can do: reading, some
  property/service access, and potentially unlocking `unshare` even if
  cgroup writes stay blocked), and have that helper create the
  unprivileged user namespace rather than relying on it directly having
  `CAP_SYS_ADMIN`. Whether cgroup limits end up available at all on a
  no-root install is a separate, secondary question from whether the
  container can boot.

## Next step (needs a real device, not more reading)

The fastest way to resolve the open question is empirical, not further
policy archaeology. This is now built directly into the app rather than
left as a manual exercise: Settings → Shizuku, once Shizuku itself is
installed and connected (via Wireless Debugging or root), has a "Test
namespace access" button. It binds a Shizuku user service that runs in
whatever process Shizuku is hosting (shell UID 2000 for the ADB/Wireless
Debugging path, uid 0 for the root path), and from there attempts the
exact two operations `namespace_manager.cpp`'s `launch_init()` depends
on: `unshare(CLONE_NEWNS|CLONE_NEWPID|CLONE_NEWUTS|CLONE_NEWIPC)` followed
by a private recursive remount of `/`, both from a disposable forked
child so the probe can't leave the long-lived service process in a
half-unshared state. It reports back which of the two succeeded and the
`errno` for whichever didn't, straight to the Settings screen. See
`app/src/main/cpp/diagnostics/namespace_probe.cpp` and
`app/src/main/java/com/hexadecinull/vineos/shizuku/` for the
implementation.

This turns the open question from source-reading into a one-tap check
on whatever device it's run on. It settles the `unshare`/`mount`
question directly; it does not settle the separate cgroup-write question
from earlier in this document (the probe only checks the two calls the
container engine's `launch_init()` actually needs to start; cgroup
limits are a secondary, independent concern that can degrade gracefully
without blocking boot).

This document should get updated with real findings once that's been
tried on real hardware, and it should also be re-checked against the
Virtual Master and similar closed-source apps' actual behavior if it
ever becomes possible to observe them (e.g. via `strace`/`dmesg` on a
rooted test device running the closed-source app itself, which would
show directly what syscalls it relies on rather than guessing from
policy alone).

## Update for 0.2.0

The recommended next step above is now built into the app:

- **Settings, Engine and privileges, Test namespace access** runs the probe
  through a Shizuku user service and explains the result.
- The helper runs through Shizuku as the shell user (`--allow-unprivileged`),
  and fails before any preparation with the exact errno when the kernel refuses
  namespaces. A Shizuku that was started with root works as a full root path.
- A log from a real phone showed the first failure was not the kernel at all.
  The app crashed 270 ms after Start because a foreground service was stopped
  while Android still waited for `startForeground`. That race is fixed, see
  [Troubleshooting](../guides/TROUBLESHOOTING.md).

What is still open: a phone whose ADB shell can create namespaces. Please run
the probe on yours and report the result.

## Update for 0.2.5: the no-root path is a machine, not a container

The question this document started with, whether the ADB shell can stand in
for root for the container engine, still needs a phone that answers yes, and
most phones answer no. 0.2.5 stops depending on the answer.

### What changed

VineOS has a second engine that boots a ROM as a QEMU virtual machine inside
the app's own process tree. Nothing in it needs `CAP_SYS_ADMIN`, namespaces,
mounts, cgroups, loop devices or a helper process, so nothing in it needs root
or Shizuku. Apps that run a full guest without root (Vectras VM and Podroid
are the ones used as references) do the same thing: QEMU's software CPU
emulation (TCG) as an ordinary process, with the guest's disks and sockets in
the app's private folder.

The container engine stays. It is far faster, because the guest runs natively
on the phone's CPU, and **Automatic** mode keeps using it whenever root or a
root-backed Shizuku can start it.

### Why an ordinary app can do it

- **Executing the binary.** Android 10 and newer, for apps that target API 29
  or higher, refuse to execute a file from the app's writable data folder
  (the Termux project documents this as the W^X rule). Files in the native
  library folder are allowed. QEMU therefore ships as
  `libqemu_system_aarch64.so` and `libqemu_system_arm.so`, and the app is
  packaged so those files are extracted to disk (`useLegacyPackaging`).
- **No KVM.** An app cannot open `/dev/kvm`, so the machine is emulated, not
  accelerated. It runs on every phone and runs 32 bit ARM guests on arm64
  chips that dropped 32 bit, at a fraction of native speed.
- **No device nodes, no network setup.** The disks are files, the network is
  QEMU's user mode NAT (it needs no privilege), the display is VNC and the
  control channel is QMP, both over Unix sockets in the app's folder, and
  the guest agent talks over a virtio serial port that QEMU exposes as a third
  socket.

### What Wireless debugging and Shizuku are for now

Not for creating namespaces. They are for keeping the machine alive. Android
12 and newer kill the child processes of an app once the device holds more than
a set number of them (the phantom process limit), and QEMU is such a child
process. When the app is killed this way, the log says the machine was
stopped by signal 9. The documented switches need the ADB shell (or
`WRITE_SECURE_SETTINGS`), which is exactly what Wireless debugging plus Shizuku
provides without a computer:

| Android | What VineOS runs |
|---|---|
| 12 (API 31) | `device_config set_sync_disabled_for_tests persistent`, then `device_config put activity_manager max_phantom_processes 2147483647` |
| 12L and newer (API 32+) | `settings put global settings_enable_monitor_phantom_procs false` |
| 14 and newer | The same, and the "Disable child process restrictions" switch in Developer options is explained in the app, because it is a separate switch the user has to flip |

The same run also exempts VineOS from battery optimisation, allows it to run in
the background and moves it to the active standby bucket. It is one button,
**Stop Android from killing VineOS** under Settings, Engine, and it runs
through root or Shizuku and reports which step worked. Without either, the same
switches can be set from a computer with `adb shell`, see
[Troubleshooting](../guides/TROUBLESHOOTING.md#the-machine-stops-after-a-while).

### Root managers

Once the machine engine made root optional, detecting root properly mattered
more, not less, because Automatic needs an honest answer to "can the container
engine start?". Looking for a `su` file is not enough. KernelSU, KernelSU Next,
SukiSU Ultra and APatch answer for `su` through the kernel, so there can be no
file at all, and they refuse apps that are not switched on in their Superuser
list. Magisk only shows its prompt when a process really runs `su`. VineOS
therefore runs `su -c id` and classifies the result (granted, denied, no answer
within 30 seconds, missing), reads `su -v` only after a grant to name the
manager, and turns each outcome into a message for the manager that is
installed.

### What is still open

- A ROM with a kernel that boots under QEMU's `virt` machine. The engine, the
  manifest profile and the ROM kit are written and tested on a host. No Android
  system image has booted in it yet.
- Speed. TCG is interpretation plus translation. Expect games to need the
  largest translation cache setting and still be slow, and expect 32 bit guests
  to be slower again.
- The Android Virtualization Framework (Android 13 and newer) as a third
  backend, which would use the phone's hypervisor.
