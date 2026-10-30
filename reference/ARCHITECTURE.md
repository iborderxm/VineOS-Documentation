# Architecture

This describes how VineOS is put together: the Kotlin app layers, the two
native pieces, and how they talk to each other and to the guest. For setup
instructions see [BUILDING.md](../guides/BUILDING.md); for what the app does from
a user's point of view see [USAGE.md](../guides/USAGE.md); for what a ROM must
provide see [ROM_INTEGRATION.md](ROM_INTEGRATION.md).

## Table of Contents

- [High-level overview](#high-level-overview)
- [Kotlin app layers](#kotlin-app-layers)
- [Native pieces (C++)](#native-pieces-c)
- [The root helper protocol](#the-root-helper-protocol)
- [Instance directory layout](#instance-directory-layout)
- [Instance lifecycle, start to stop](#instance-lifecycle-start-to-stop)
- [Guest root and namespaces](#guest-root-and-namespaces)
- [Display pipeline](#display-pipeline)
- [Input and the guest agent](#input-and-the-guest-agent)
- [Home screen shortcuts](#home-screen-shortcuts)
- [Storage and snapshots](#storage-and-snapshots)
- [Networking](#networking)
- [ABI compatibility](#abi-compatibility)
- [Data storage](#data-storage)
- [Security model](#security-model)
- [Testing strategy](#testing-strategy)
- [CI/CD](#cicd)

## High-level overview

A VineOS "instance" is a full, separate Android system image (a ROM,
packaged as a `.vrom` file) running inside a Linux namespace container on
the host device. VineOS is not a hypervisor: the guest kernel is the same
kernel as the host's. Isolation comes from PID, mount, UTS, IPC and network
namespaces plus cgroup limits and loop-mounted images, similar in spirit to
how a container runtime like `runc` isolates a process tree, adapted for
running a full Android `init` as the containerized process.

Starting a container needs privilege the app does not have. The app
therefore ships a second native binary, the **root helper**, which it starts
with `su`. The helper owns every guest. The app talks to it over the helper's
stdin and stdout, and gets guest frames straight from a shared memory file.

```text
┌──────────────────────────────────────────────────────────────┐
│ VineOS app process (no root)                                  │
│                                                                │
│  Compose UI → ViewModels → VineVMManager ──► HelperClient      │
│                                │                  │ stdin/out  │
│                          DisplayBridge            │            │
│                      (libvine_runtime.so)         │            │
└───────────────────────────────┼───────────────────┼────────────┘
                                │ mmap, read only   │
┌───────────────────────────────┼───────────────────┼────────────┐
│ libvine_helper.so (root, started with su)         ▼            │
│                                                                │
│  HelperServer → Container (one per instance) → AgentLink       │
│                      │                              │          │
└──────────────────────┼──────────────────────────────┼──────────┘
                       │ namespaces, mounts           │ unix socket
┌──────────────────────▼──────────────────────────────▼──────────┐
│ Guest: Android init (PID 1) · guest agent · display writer      │
│ /vine ◄── <instance>/shared (vinefb, agent.sock, boot.prop)     │
└────────────────────────────────────────────────────────────────┘
```

## Kotlin app layers

| Layer | Package | Responsibility |
|---|---|---|
| UI | `ui.screens`, `ui.components`, `ui.theme` | Jetpack Compose screens and widgets, Material You theming |
| Navigation | `ui.navigation` | `NavHost` route definitions |
| ViewModel | `ui.viewmodel` | Hilt-injected `ViewModel`s exposing `StateFlow` to the UI |
| Domain | `domain.VineVMManager` | Starts and stops instances through the helper, owns per-instance status flows and the foreground service count |
| Domain | `domain.InstanceProvisioner` | Unpacks a `.vrom` into a new instance directory with progress and a free space check |
| Domain | `domain.DisplayPlanner`, `domain.StorageSizing` | Pure logic: guest resolution and DPI from the phone's screen, and the disk size choices |
| Domain | `domain.shortcuts` | App list and icon cache, pinned shortcut creation, shortcut launch handling |
| Helper client | `helper.HelperLauncher`, `HelperClient`, `HelperProtocol`, `GuestProtocol` | Builds the `su` command line, speaks the helper protocol, formats guest agent lines |
| Data (models) | `data.models` | `VMInstance`, `ROMImage`, `DownloadProgress`, `AbiCompat`, `DisplaySettings` |
| Data (repository) | `data.repository` | `InstanceRepository` (Room), `ROMRepository` (network and files), `AppPreferences` (DataStore), `VineDatabase` |
| Native bridge | `native.VineRuntime` | `external fun` declarations mapping 1:1 to JNI exports |
| Service | `service.VineService` | Foreground service keeping the process alive while an instance runs |
| Shizuku | `shizuku` | Optional probe of what ADB-level privilege can do |

Screens are stateless composables that take a `ViewModel`'s exposed state
and callbacks as parameters; each `ViewModel` is the only thing that talks
to `VineVMManager` or the repositories, so UI code never touches Room,
DataStore, the helper or JNI directly.

## Native pieces (C++)

All native code lives under `app/src/main/cpp/` and builds into two
artifacts per host ABI (`arm64-v8a`, `armeabi-v7a`, `x86_64`, `x86`), plus a
static library of the shared engine code. See
[ABI compatibility](#abi-compatibility).

| Artifact | What it is | Runs as |
|---|---|---|
| `libvine_runtime.so` | JNI library: host probes and the display bridge | The app, no root |
| `libvine_helper.so` | An executable named like a library so Android extracts it to the native library directory. It holds the container engine and the helper server | Root, started with `su -c exec` |
| `vine_core` (static) | The sources both of the above and the host tests share | n/a |

| Module | Files | Responsibility |
|---|---|---|
| Container | `container/namespace_manager.*` | The `Container` lifecycle, namespaces, mounts, cgroups, binder, binfmt, init launch, status polling |
| Container | `container/boot_props.*`, `ramdisk.*`, `sparse_image.*`, `loop_mount.*`, `net_setup.*`, `guest_exec.*` | Boot properties, cpio ramdisk extraction, sparse image expansion, loop mounts, veth and NAT, running a command inside a guest |
| Helper | `helper/helper_server.*`, `helper_main.cpp`, `agent_link.*` | The protocol server on stdin and stdout and the link to a guest's agent |
| Display | `display/vinefb*.{h,cpp}`, `pixel_convert.*`, `display_bridge.*` | The framebuffer contract, tear-free reads, pixel conversion, drawing onto a `Surface` |
| Diagnostics | `diagnostics/*` | What the kernel offers (namespaces, binder, cgroups, loop, SELinux, AArch32) |
| QEMU bridge | `qemu_bridge/qemu_launcher.cpp` | Locates the bundled `qemu-arm` binary |
| Utils | `utils/*` | Files, processes, sparse copies, AArch32 detection, line escaping, logging |
| JNI entry | `vine_runtime.cpp` | The `Java_com_hexadecinull_vineos_native_VineRuntime_*` exports |

The same sources compile with plain `g++` on a Linux host, which is how the
native tests run. See [Testing strategy](#testing-strategy).

## The root helper protocol

The app starts the helper with `su` and talks to it over the process's stdin
and stdout, so no other process can reach it. One line per message, tab
separated, with backslash escapes for `\n`, `\r`, `\t` and `\\`:

| Kind | Form |
|---|---|
| Request | `id TAB command TAB arg ...` |
| Reply | `id TAB ok\|err TAB payload` |
| Event | `* TAB name TAB field ...` |

A request with the id `-` gets no reply, which is how touch events travel.

| Command | Purpose |
|---|---|
| `hello`, `probe`, `diag` | Version handshake, device report, per-instance state and boot log tail |
| `start`, `stop`, `kill`, `pause`, `resume`, `status`, `list` | Guest lifecycle. `start` takes `key=value` options: RAM, CPU cores, data size, resolution, DPI, network mode, 32-bit support |
| `exec` | Run a command inside a running guest |
| `agent`, `agent_send` | Send a line to the guest agent, with or without waiting for the reply |
| `apps`, `launch`, `icon` | Guest app list, open an app, an app's icon as PNG |
| `snapshot`, `restore`, `snapshots`, `delete_snapshot` | `/data` disk snapshots |
| `rmtree`, `quit` | Delete an instance directory the helper created, shut down |

| Event | Meaning |
|---|---|
| `ready` | The helper is up and tells the app which uid it runs as |
| `state` | An instance went to booting, running, paused, stopped or error, with a detail text |
| `snapshot`, `restore` | A snapshot job finished, with success or the failure text |

Every path the app sends must lie under the instances directory the helper
was started with (`--base`). The helper refuses anything else. When the app
process or the helper's stdin goes away, every guest is killed with it.

## Instance directory layout

Everything for one instance lives under `filesDir/instances/<id>/`:

| Path | Contents |
|---|---|
| `manifest.json` | The `.vrom`'s own manifest, copied at creation |
| `ramdisk.img` | gzip cpio with `/init` and the init `.rc` files |
| `system.img`, `vendor.img` | Read-only images, mounted at `/system` and `/vendor`. Android sparse images are expanded on first start |
| `data.img` | Sparse ext4 disk, mounted at `/data`. Created on first start |
| `rootfs/` | The extracted ramdisk, the guest's `/` |
| `shared/` | The folder shared with the guest as `/vine`: `vinefb`, `boot.prop`, `cmdline`, `agent.sock`, `boot_completed` |
| `snapshots/` | `<name>.img` copies of `data.img` |
| `boot.log` | Output of the supervisor and of init's console |

The app keeps the app list and icons it read from a guest separately in
`filesDir/app_cache/<id>/`.

## Instance lifecycle, start to stop

1. The UI calls `VineVMManager.startInstance`.
2. `VineVMManager` makes sure the helper is running (`su` prompt on the
   first use), reads the `.vrom` manifest to decide if 32-bit emulation is
   needed, asks `DisplayPlanner` for the guest resolution and sends `start`.
3. The helper's `Container` prepares the instance: expands sparse images,
   extracts the ramdisk into `rootfs/` and checks that its `init` carries the
   container marker, formats `data.img` as sparse ext4 on the first start,
   creates `shared/vinefb` with its header and writes `boot.prop`, `cmdline`
   and a managed block in the ramdisk's `default.prop`.
4. A supervisor process forks the guest as PID 1 of new PID, UTS, IPC,
   network and mount namespaces (see
   [Guest root and namespaces](#guest-root-and-namespaces)). The host side
   of the network and the cgroup limits are set up, and the 32-bit
   `binfmt_misc` rule is registered when the guest needs it.
5. While booting, the helper polls the container. The instance becomes
   *running* when the guest creates `shared/boot_completed`, or when the
   first frame shows up in `vinefb`. If neither happens before the boot
   timeout it is treated as running anyway so the screen is visible.
6. The helper pushes a `state` event on every change, the app updates its
   `StateFlow<VMStatus>` and, through `VineService`, a foreground
   notification keeps the process alive while any instance is active.
7. Stopping sends `SIGTERM` to the guest's init and waits before falling back
   to `SIGKILL`. When no instance has been active for a minute the helper is
   shut down too.
8. If the app is killed or the helper dies, the kernel kills every guest with
   it. On the next start the app resets all stored statuses to stopped, since
   nothing can still be running.

## Guest root and namespaces

The guest's root is built inside its own mount namespace, so none of it is
visible to the phone:

| Mount | Source |
|---|---|
| `/system`, `/vendor` | Loop-mounted images, read only, with ext4, erofs, squashfs or f2fs tried in turn. The loop devices are autoclear, so they vanish with the namespace |
| `/data` | `data.img` (or a host folder when `mke2fs` is missing) |
| `/cache` | A 64 MB tmpfs |
| `/proc` | The guest's own PID namespace. `/proc/sys`, `irq`, `bus` and sysrq are bound read only, `kcore` and `kmsg` are blanked, `cmdline` is replaced by `shared/cmdline` |
| `/sys` | Read only |
| `/dev` | A small tmpfs with `null`, `zero`, `full`, `random`, `urandom`, `tty`, `fuse`, `pts`, `ptmx`, `console`, `ashmem` when the phone has it, and the binder devices |
| `/vine` | `shared/` |

Binder comes from a private `binderfs` instance when the kernel supports it,
otherwise from Anbox style extra binder devices when the phone has them, and
otherwise the guest has none and the log says so. The container then
`pivot_root`s into the new root (or moves it over the root when the host's own
root cannot be pivoted) and executes `/init` with a clean file descriptor
table and a small environment. A guest `init` without the marker
`VINE_CONTAINER_INIT_V1` is refused, because an unpatched Android `init` would
load its SELinux policy into the phone's kernel.

The container has **no user namespace**. Root inside the guest is root on
the phone, restricted only by the mounts, the namespaces and the cgroup
limits. That is a deliberate trade for working loop mounts and binder on stock kernels, and it
is why only ROMs you trust should run. See the
[security model](#security-model).

Memory and CPU limits come from cgroups: `memory.max` and `cpu.max` on
cgroup v2 or `memory.limit_in_bytes` and `cpu.cfs_quota_us` on v1. Pausing
an instance freezes its cgroup.

## Display pipeline

The display contract is a shared memory file, `vinefb`, created by the
engine in `shared/` before the guest starts. It has a 64 byte header
(magic, version, size, stride, pixel format, capacity and a frame counter)
followed by pixels from offset 4096. The guest's graphics stack writes
finished frames with a sequence counter that is odd while it writes and even
when the frame is complete, so a reader that copies a frame and sees the same
even value before and after has a tear-free picture. The full contract is in
[ROM_INTEGRATION.md](ROM_INTEGRATION.md).

When `VMDisplayScreen` attaches its `Surface`, `DisplayBridge` maps the file
read-only and starts a render thread. While frames arrive it follows the
display's vsync through `AChoreographer`. When the guest screen is still it
drops to a slow check, so an idle screen costs almost no CPU. Pixels are
converted to `RGBA_8888` as needed (including `RGB565`).

The bridge does not draw by itself. It asks a `Presenter` to copy the newest
frame to the window, and there are three of them:

| Presenter | How a frame reaches the screen | When it is used |
|---|---|---|
| Software | The frame is converted straight into the buffer of `ANativeWindow_lock`. The `Surface` is given the guest's own resolution, so the system compositor does the scaling | Graphics backend "Software", and the last fallback |
| OpenGL ES | The frame is converted into a CPU buffer, uploaded to one texture and drawn as a full screen quad through EGL | "Automatic" and "OpenGL ES" |
| Vulkan (experimental) | The frame is converted into a mapped staging buffer, copied to a device local image and blitted (scaled) to the swapchain image. There are no shaders | "Vulkan", only offered on phones where the probe found a usable Vulkan GPU |

The choice is the same graphics backend setting that goes to the guest as
`ro.boot.vine.gpu`, so the guest and the host agree. `VineRuntime.setDisplayBackend`
passes it to the bridge. If a presenter cannot start (no EGL, no Vulkan loader, an
unsupported surface format) or fails three frames in a row, the bridge moves down
the chain Vulkan, OpenGL ES, software and logs why under "Display" in the in-app
log. The chain never ends empty, software always works.

Two details keep this safe. Presenters only run on the render thread, because
EGL contexts and Vulkan swapchains belong to the thread that made them.
`set_surface` wakes that thread and waits (at most 300 ms) until the old window
was released, because Android forbids touching a `Surface` after
`surfaceDestroyed` returns. Vulkan is loaded with `dlopen("libvulkan.so")`, so
the app still starts on a phone that has no Vulkan, and the OpenGL ES presenter
never calls `eglTerminate`, because the display is shared with Compose.

The Vulkan probe (`probeVulkan`) creates an instance, looks for a GPU with a
graphics queue and `VK_KHR_swapchain`, and reports the GPU name and API
version. `GpuSupport` caches the result for the settings screens, which hide the
Vulkan choice when the probe fails.

`DisplayPlanner` chooses the guest resolution before the start: either the
phone's own aspect ratio (so the guest fills the screen) or the largest 9:16
rectangle that fits, capped by the quality setting (long side 1920, 1280 or
960) and rounded to multiples of 8. The DPI follows from the width.
`VMDisplayScreen` hides the system bars while an instance is shown and does
not apply the app's window insets, which removes the empty strips around the
guest.

## Input and the guest agent

Input does not use `uinput`. The app sends compact text lines to a small
**guest agent** that runs inside the ROM and injects real Android input
events:

```text
touch <action> <actionIndex> <n> <id> <x> <y> ...   x and y are fractions 0..1
key <keycode> <1|0>
text <escaped text>
```

These three get no reply. `VMDisplayScreen` collects every active pointer
(up to ten) and `VineVMManager` sends them through the helper's
`agent_send`, dropping move events when the link is busy. Normalized
coordinates mean the app never needs to know the guest's resolution. The
agent also answers request and reply commands (`ping`, `apps`, `launch`,
`icon`, `clip`), whose replies end with a line holding a single `.`. Without
an agent, hardware keys fall back to the guest's own `input keyevent` tool
through `exec`, and touch is unavailable.

## Home screen shortcuts

Each pinned shortcut is a launcher shortcut with the id
`app:<instanceId>:<package>`, the app's name as its label and, when the app
icon was fetched, that icon. Its intent targets `MainActivity` (a
`singleTask` activity) with the action
`com.hexadecinull.vineos.action.LAUNCH_APP` and the instance id and package
name as extras. `ShortcutLauncher` validates both, starts the instance when
it is not running and queues the package. `VineVMManager` opens the app with
the agent's `launch` command as soon as the instance reports *running* and
retries a few times while Android is still settling.

`MainActivity` is exported for the launcher, so another app can send the same
intent. The effect is limited to starting one of the user's own instances and
opening an app in it, with both values validated, but it is worth knowing.

## Storage and snapshots

`data.img` is a sparse file formatted as ext4, so choosing a large size costs
nothing until the guest writes data. The create-instance screen accepts any
size up to the phone's free space. Snapshots copy the image with
`SEEK_DATA` and `SEEK_HOLE`, so holes stay holes and a mostly empty disk makes
a small snapshot. Taking one of a running instance freezes its cgroup for the
copy. The copy runs in a separate process so the helper stays responsive, and
the result arrives as a `snapshot` or `restore` event. Restoring requires a
stopped instance.

## Networking

With *Guest internet access* on, each guest gets its own network namespace.
Its `eth0` is the guest end of a veth pair with an address from
`10.77.<slot>.0/30`, configured before `init` starts by ioctls only, so the
ROM needs no tools for it. The host end is NATed through the phone's current
uplink with `ip` and `iptables`. Android routes per network, so traffic is
pointed at the table of the current uplink. This part is best effort: when
it fails the guest still boots without internet. Android's own connectivity
service must also adopt `eth0` for apps to see a network, see
[ROM_INTEGRATION.md](ROM_INTEGRATION.md).

## ABI compatibility

`AbiCompat.kt` is the single source of truth for what runs where. It
defines a `RunMode` (`NATIVE`, `QEMU`, `UNAVAILABLE`) and a full host ABI
by guest ABI matrix:

| Host primary ABI | arm64-v8a guest | armeabi-v7a guest | armeabi guest | x86_64 guest | x86 guest |
|---|---|---|---|---|---|
| `arm64-v8a` | Native | Native or QEMU (device-dependent) | Native or QEMU | QEMU | QEMU |
| `armeabi-v7a` | Unavailable | Native | Native | Unavailable | QEMU |
| `x86_64` | QEMU | QEMU | QEMU | Native | Native |
| `x86` | QEMU | QEMU | QEMU | Unavailable | Native |

"Unavailable" always means a 32-bit host trying to run a 64-bit guest,
which no amount of emulation makes possible. `ROMsScreen` reads this matrix
to badge each downloadable ROM as natively runnable, QEMU-emulated (with a
performance cost), or incompatible with the current device, using
`Build.SUPPORTED_ABIS` as the host side of the lookup.

This Kotlin-side matrix is only meaningful because `libvine_runtime.so`
itself is compiled for all four host ABIs (`app/build.gradle.kts`
`ndk.abiFilters`) and because a matching `libqemu_arm.so` is bundled per
host ABI under `jniLibs/<abi>/` (see
[BUILDING.md](../guides/BUILDING.md#building-qemu-arm)); without both of those, the
compatibility badges would describe capabilities the installed APK doesn't
actually have on a given device.

## Data storage

| Store | Technology | Contents |
|---|---|---|
| `VineDatabase` | Room | `VMInstance` rows: name, RAM and storage size, status, timestamps |
| App preferences | Jetpack DataStore | Theme, defaults, display settings, guest network, root toggle |
| Instance and ROM files | App-private storage (`context.filesDir`) | Downloaded `.vrom` images, [instance directories](#instance-directory-layout) |
| App cache | `filesDir/app_cache/<id>/` | App lists and icons read from guests for the shortcut picker |

Room's `fallbackToDestructiveMigration(dropAllTables = true)` is used
instead of real migrations while the schema is still moving during the
pre-1.0 phase; this will be replaced with versioned migrations before a
1.0 release.

## Security model

Summarized here; the authoritative version is
[SECURITY.md](../project/SECURITY.md#security-design-notes). Namespace isolation is
meaningful but not equivalent to a hypervisor boundary, and without a user
namespace guest root is host root. The threat model assumes a trusted ROM
image (hash-verified on download) and a trusted host. The root helper accepts
commands only from the app that started it, over its stdin, and only touches
paths under the instances directory. Root access inside a guest (Magisk) is
opt-in and explicitly narrows the isolation boundary for that instance only.

## Testing strategy

- **Unit tests** (`app/src/test/`): JUnit4 + MockK + Truth, covering model
  logic (`VMStatus`, `AbiCompat`), the helper and guest protocols,
  `DisplayPlanner`, `StorageSizing`, shortcut validation, repository behavior
  against mocked dependencies and `ViewModel` state transitions.
- **Instrumented tests** (`app/src/androidTest/`): Room database tests
  running against a real in-memory database on-device, plus Compose UI
  tests where relevant.
- **Native tests** (`app/src/main/cpp/tests/native/`): the engine sources
  build with plain `g++` on a Linux host. `run_tests.sh` boots a small fake
  ROM (a static `init` and a fixture of ramdisk, ext4 images and tools)
  through the real `Container` code in real namespaces and checks isolation
  (including a private network namespace), `/data` persistence and growth,
  pause and resume, crash and power-off handling and two guests at once. It
  also drives the helper binary over its protocol with a fake guest agent. It
  needs root, `mke2fs` and a kernel with loop devices. NAT is not covered
  when the host has no `ip` tool, as in the sandbox these were written in. `run_display_tests.sh` covers the framebuffer reader, the
  pixel conversion, the guest side writer (including a writer racing the
  reader), the presenter fallback policy and the whole `DisplayBridge` against
  stubbed Android headers, which proves the fallback to software and the
  surface handover. It needs nothing but `g++`. The EGL and Vulkan code is
  compile checked against stub headers there, but only runs on a phone.
- **Guest agent** (`rom/agent/test/`): the agent's protocol class is plain
  Java, so `run_tests.sh` there checks it on any JDK.

What none of these prove: that the app builds and runs on a device, that a
real Android system image boots inside the container, and that NAT works on
Android's networking stack.

## CI/CD

GitLab CI/CD, defined in `.gitlab-ci.yml`, with helper scripts under
`scripts/ci/`:

| Job | Trigger | Purpose |
|---|---|---|
| `ktlint` | Branch and merge request pipelines | Kotlin style check |
| `android-lint` | Branch and merge request pipelines | Android lint |
| `unit-tests` | Branch and merge request pipelines | JUnit tests, results shown in the merge request |
| `native-display-tests` | Branch and merge request pipelines | Framebuffer reader and guest writer tests with plain `g++` |
| `rom-kit-tests` | Branch and merge request pipelines | Guest agent protocol tests on a JDK, syntax check of the Python tools |
| `secret_detection` | Branch and merge request pipelines | Scans for committed credentials |
| `build-debug` | After the checks pass | Debug APK, including the NDK compile |
| `nightly` | Pipeline schedule | Unit tests and a debug APK |
| `release-*` | Manual pipeline with a version tag | Signed release APK, published as a GitLab release |
| `renovate` | Pipeline schedule | Opens dependency update merge requests |

`renovate.json` configures the dependency updates: Gradle dependencies are
grouped by Compose, other AndroidX, and Kotlin/KSP, and the pinned CI
images are tracked too. Those merge requests go through the same pipeline
as any other. [BUILDING.md](../guides/BUILDING.md#cicd) covers the pipeline schedules
and [RELEASE_SETUP.md](../guides/RELEASE_SETUP.md) covers releases.

## Privilege modes (0.2.0)

The helper can now start two ways, chosen by **Settings, Engine and
privileges**:

- `su`: `su -c exec libvine_helper.so ...`, as before.
- Shizuku: the app binds a Shizuku user service (its own process, started as
  the Shizuku user, which is root or the ADB shell user). The service launches
  `libvine_helper.so --allow-unprivileged` with `ProcessBuilder` and hands the
  helper's stdin, stdout and stderr back over Binder as pipe file descriptors.
  On the app side they are wrapped in a `java.lang.Process`, so the helper
  client and the protocol did not change.

The helper reports `uid=` and `privileged=` in its `hello` reply. As a non
root user it checks, before any expensive preparation, that it can create
namespaces and make mounts private, and otherwise fails with the errno. The
namespace probe and the terminal use separate Shizuku processes, so running
either can never stop a running helper.

In `Automatic` mode the app prefers a root-backed Shizuku, then `su`, then a
shell-level Shizuku.

## Foreground service lifecycle

`VineService` calls `startForeground` in `onCreate` and again in
`onStartCommand`, so any start request satisfies Android's contract. It
publishes a confirmed-foreground flag. `VineVMManager` reconciles the service
under a mutex and waits for that flag before it stops the service, which
removes the start then stop race that crashed 0.1.0. Notifications use
`START_NOT_STICKY`, because a restarted service without guests is useless.

## Device identity overlay

See [Device identity](../guides/DEVICE_IDENTITY.md). The start command carries
`spoof.<key>=<value>` pairs; `container/spoof.cpp` validates them, expands
them to property names and rewrites `build.prop` copies that are bind mounted
into the guest.

## ashmem shim

`app/src/main/cpp/shim/ashmem_shim.c` implements libcutils' `ashmem_*`
functions on `memfd_create`. When the host has no `/dev/ashmem`, the engine
copies `libvine_ashmem.so` into the instance's shared folder and appends
`export LD_PRELOAD /vine/shim/libvine_ashmem.so` under `on early-init` in the
ramdisk's `init.vine.rc`. The Bionic linker aborts a process whose preload
cannot be loaded, so the shim is limited to the phone's primary ABI.

## QEMU binfmt rule

The 32 bit ARM rule uses the same magic and mask as QEMU's
`scripts/qemu-binfmt-conf.sh`. Flags are tried as `OCFP`, then `OCF`, then `F`:
`O` and `C` make the kernel take credentials (setuid) from the guest binary
instead of from QEMU, `P` keeps the guest's `argv[0]` (QEMU's linux-user honors
`AT_FLAGS_PRESERVE_ARGV0`), and `F` opens QEMU at registration so it works
inside the guest's mount namespace. `P` needs Linux 4.8, so older kernels fall
back. The engine also reads only the ELF header of the QEMU binary (the old
check loaded the whole file), accepts 32 bit builds on 32 bit hosts, rejects a
dynamically linked build, and reports its version.

## Memory and CPU limits

The cgroup memory limit is the instance's RAM plus one eighth of headroom for
kernel structures that are charged to the group, with `memory.high` (cgroup v2)
at the nominal RAM so reclaim starts before any kill. CPU weight follows the
performance profile (battery, balanced, performance).
