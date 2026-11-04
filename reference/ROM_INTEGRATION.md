# ROM integration

This is the contract between the VineOS container engine and a ROM: what the
engine hands a guest, what a guest must hand back, and what is still
unproven. The guest side kit that implements it lives in the `rom/` folder of
the [main repository](https://gitlab.com/Hexadecinull/VineOS/VineOS). For how
the engine itself works see [ARCHITECTURE.md](ARCHITECTURE.md).

> **Status.** The engine side is implemented and tested on a Linux host with a
> fake ROM. The guest side kit is written against this contract and its pure
> parts are unit tested. No real Android system image has booted inside
> VineOS yet. Treat everything below as the design to build against, and the
> first real boot as the open milestone.

## Table of Contents

- [What the engine provides](#what-the-engine-provides)
- [The shared folder](#the-shared-folder)
- [Boot properties](#boot-properties)
- [The init marker](#the-init-marker)
- [The framebuffer contract (vinefb)](#the-framebuffer-contract-vinefb)
- [The guest agent protocol](#the-guest-agent-protocol)
- [Boot completion](#boot-completion)
- [Networking](#networking)
- [Kernel features a guest depends on](#kernel-features-a-guest-depends-on)
- [Checklist for a first boot](#checklist-for-a-first-boot)
- [Known open problems](#known-open-problems)
- [Booting as a virtual machine](#booting-as-a-virtual-machine)

## What the engine provides

`/init` from the ROM's `ramdisk.img` starts as PID 1 with:

| Path | What it is |
|---|---|
| `/system`, `/vendor` | The ROM's images, loop mounted read only. `vendor.img` is optional |
| `/data` | A sparse ext4 image created on first start, sized by the instance's storage setting |
| `/cache` | A 64 MB tmpfs |
| `/proc`, `/sys`, `/dev` | Fresh mounts. `/proc/sys` and sysrq are read only, `/sys` is read only, `/dev` is a small tmpfs. There is no uevent source |
| `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` | A private binderfs instance or Anbox style devices, see [Kernel features](#kernel-features-a-guest-depends-on) |
| `/dev/ashmem` | Bound from the phone when the kernel has it |
| `/vine` | The shared folder |
| Network | A private network namespace with `lo` up and, with guest internet enabled, `eth0` already addressed and routed |

The guest has its own PID, UTS, IPC, network and mount namespaces and a
cgroup with the instance's memory and CPU limits. It has no user namespace,
so guest root is host root.

`/dev` holds only `null`, `zero`, `full`, `random`, `urandom`, `tty`, `fuse`,
`pts/ptmx`, `console`, `ashmem` and the binder devices. Nothing else exists,
so `ueventd` has nothing to create and anything that opens `/dev/graphics/fb0`,
`/dev/input/*`, `/dev/ion`, `/dev/dri/*` or `/dev/kvm` will fail unless the
ROM avoids it.

## The shared folder

`<instance>/shared/` on the host is mounted at `/vine` in the guest. It is
cleaned of stale `boot_completed`, `agent.sock` and `vinefb` entries on every
start.

| File | Written by | Meaning |
|---|---|---|
| `boot.prop` | host | `key=value` boot properties |
| `cmdline` | host | The same values as kernel command line words. Bound over `/proc/cmdline` |
| `vinefb` | host creates, guest writes | The display. See below |
| `agent.sock` | guest | Unix socket the guest agent listens on |
| `boot_completed` | guest | Created when Android finished booting |

## Boot properties

The engine writes the same values into three places so a ROM can read
whichever is convenient: `/vine/boot.prop`, `/proc/cmdline` as
`androidboot.*` words (which Android's init turns into `ro.boot.*`), and a
block between `# vine-begin` and `# vine-end` in the ramdisk's `default.prop`.

| Property | Meaning |
|---|---|
| `ro.boot.hardware` | `vine`, `ranchu` or `goldfish`, whichever of `init.<name>.rc` exists in the ramdisk, in that order. Empty if none |
| `ro.boot.vine` | `1` |
| `ro.boot.vine.instance` | The instance id |
| `ro.boot.vine.width`, `height`, `dpi` | Display size in pixels and density |
| `ro.boot.vine.ram_mb` | The memory limit |
| `ro.boot.vine.root` | `1` when the instance may be rooted |
| `ro.boot.vine.qemu32` | `1` when 32-bit ARM code runs through QEMU |
| `ro.boot.vine.net_ip`, `net_gw`, `net_dns` | The guest address (a `/30`), the gateway and DNS server. Only present with guest internet |
| `ro.sf.lcd_density` | Same as the DPI |

The command line also carries `androidboot.selinux=permissive`,
`androidboot.console=console` and `androidboot.vine=1`.

## The init marker

The engine refuses to start a ROM whose `/init` does not contain the byte
string `VINE_CONTAINER_INIT_V1` within its first 16 MB. A stock Android `init`
mounts its own `/proc`, `/sys` and `/dev`, and loads its SELinux policy into
the kernel it runs on. That kernel is the phone's, so an unpatched `init` can
change the phone's security state. The marker is the ROM author's promise
that `init` was changed to live in a container. `rom/INIT_PATCH.md` in the
main repository lists the places in AOSP's `init` to change.

## The framebuffer contract (vinefb)

`vinefb` is a shared memory file. The engine creates it before the guest
starts. Every field is a little-endian `uint32`.

| Offset | Field | Meaning |
|---|---|---|
| 0 | `magic` | `0x31424656` ("VFB1") |
| 4 | `version` | `1` |
| 8 | `width` | Pixels |
| 12 | `height` | Pixels |
| 16 | `stride` | Bytes per row |
| 20 | `format` | `0` RGBA_8888, `1` BGRA_8888, `2` RGB_565, `3` RGBX_8888 |
| 24 | `data_offset` | Always `4096` |
| 28 | `capacity` | Bytes available at `data_offset`. Large enough for either orientation |
| 32 | `frame_seq` | Odd while the guest writes a frame, even when complete |
| 36 | `frame_count` | Frames presented since boot |
| 40 | reserved | Six `uint32`, zero |

The header is 64 bytes, pixels start at byte 4096.

**Writing a frame.** Set `frame_seq` to an odd value, copy the pixels, add
one to `frame_count`, then set `frame_seq` to the next even value, with
release ordering on the last store. If `frame_seq` is already odd when you
start, an earlier write was cut short, so round down to the even value first.
`rom/hwc/vinefb_writer.h` implements exactly this as a header only class.

**Reading.** The app copies a frame only when `frame_seq` is even and
unchanged after the copy, so it never shows a half written frame. It retries
a bounded number of times if the guest keeps overwriting.

The host chooses the size. A guest should render at the width and height in
the header (also given as `ro.boot.vine.width` and `height`), for example by
setting its display size to match.

## The guest agent protocol

The agent runs as root inside the guest and listens on the Unix socket
`/vine/agent.sock` (a plain filesystem socket, mode `0666`). The host's
helper connects to it. One command per line, UTF-8, `\n` terminated.

**Commands without a reply** (high rate or fire and forget):

| Command | Meaning |
|---|---|
| `touch <action> <actionIndex> <n> <id> <x> <y> ...` | A motion event with `n` pointers. `action` is the Android `MotionEvent` action (0 down, 1 up, 2 move, 3 cancel, 5 pointer down, 6 pointer up). `x` and `y` are fractions of the screen from 0 to 1. `id` is any integer the host chose per finger |
| `key <keycode> <1\|0>` | An Android key code, down (`1`) or up (`0`) |
| `text <escaped text>` | Types the text. `\n`, `\r`, `\t` and `\\` are escaped as in the helper protocol |

**Commands with a reply.** The reply is a first line starting with `ok` or
`err`, then any payload lines, then a line holding only `.`. A payload line
that would be a lone `.` is sent as `..`.

| Command | Reply |
|---|---|
| `ping` | `ok pong` |
| `apps` | `ok <count>` then one `package TAB label` line per launchable app, sorted by label |
| `launch <package>` | `ok` or `err <reason>`. Starts the app's launcher activity |
| `icon <package>` | `ok` then one line with the app icon as a base64 PNG |
| `clip get` | `ok` then one line with the clipboard text, escaped |
| `clip set <escaped text>` | `ok` |

Package names must match `[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+`. The agent
must ignore malformed lines, keep lines under 256 KB and not crash on a
closed connection.

`rom/agent/` is a reference implementation. `VineAgent.java` uses
`InputManager.injectInputEvent`, `PackageManager`, `am start` and
`ClipboardManager` through reflection, so it needs a ROM that allows its hidden
APIs for a root process. The host protocol class is separate and tested on any
JDK. The Android side has been compiled only against stubs of the Android API
and has never run.

Without an agent the instance still boots and shows its screen. Hardware keys
fall back to the guest's `input keyevent` tool, `launch` to `monkey`, and
the app list to package names only. Touch, text, icons and the clipboard need
the agent.

## Boot completion

When Android has finished booting the guest creates `/vine/boot_completed`.
`rom/init/init.vine.rc` does it from `on property:sys.boot_completed=1`. The
engine also treats the first frame in `vinefb` as a boot signal, and after the
boot timeout it assumes the guest is up so the screen is visible.

## Networking

With guest internet enabled the engine configures `eth0` itself, before
`init`, with ioctls only: the address from `ro.boot.vine.net_ip` with a `/30`
mask, a default route through `net_gw`, and `lo` up. The host side is NATed
through the phone's current uplink.

That makes `eth0` work for the kernel. For Android apps to see a network,
Android's `ConnectivityService` must adopt `eth0` as a network, which needs
Ethernet support in the ROM (`android.hardware.ethernet` and a static
configuration, since there is no DHCP server). `rom/system/etc/vine/net.sh`
repairs the address and sets the DNS properties from the boot properties but
cannot make the framework adopt the interface. Making that work is part of
the first boot effort.

## Kernel features a guest depends on

The Show diagnostics panel lists what your phone's kernel offers. The guest
benefits from:

| Feature | Used for | If missing |
|---|---|---|
| Loop devices and ext4 or erofs | Mounting the images | The start fails |
| `binderfs` (Linux 5.0+ with `CONFIG_ANDROID_BINDERFS`) or Anbox style binder devices | Android's IPC | The guest has no private binder, Android cannot boot |
| `ashmem` or `memfd` | Shared memory. Newer Android uses `memfd` | Older ROMs need `ashmem` |
| cgroups (v1 or v2) | Memory and CPU limits and pausing | Limits are skipped, pause is unavailable |
| PID, UTS, IPC, mount and network namespaces | Isolation | The start fails |
| `binfmt_misc` | 32-bit ARM through QEMU | 32-bit apps do not run on CPUs without AArch32 |
| Phone's SELinux policy | The guest runs in the phone's policy | A strict policy may block mounts or binder |

## Checklist for a first boot

1. Build or obtain the system, vendor and ramdisk images of a ROM.
2. Apply the `init` changes from `rom/INIT_PATCH.md` and keep the marker.
3. Put `rom/init/init.vine.rc` in the ramdisk root and `rom/system/etc/vine/net.sh` in `/system/etc/vine/`.
4. Build `vine-agent.jar` with `rom/agent/build_agent.sh` and install it to `/system/framework/`.
5. Make the ROM's graphics path write frames with `rom/hwc/vinefb_writer.h`.
6. Pack with `rom/package_vrom.py`, import, create an instance, start it.
7. When it fails, open Show diagnostics on the instance. It ends with the tail of `boot.log`, which holds init's console output.
8. When it boots, confirm each part: frames appear (display), touch works (agent), `ping` answers (agent), `boot_completed` appears (init script).

## Known open problems

- No real ROM has booted. Expect the first attempts to fail in `init`, binder or graphics.
- Guest root is host root. Run only ROMs you trust.
- SELinux of the phone is the policy the guest runs in.
- Android networking needs framework support for `eth0` as described above.
- Display output depends on a graphics path nobody has written for a stock ROM yet.

## Properties added in 0.2.0

| Property | Meaning |
| --- | --- |
| `ro.boot.vine.gpu` | `auto`, `gles`, `vulkan` or `software`. `/system/etc/vine/gpu.sh` turns it into `debug.hwui.renderer` (Skia GL or Skia Vulkan on Android 10 and newer) |
| `ro.boot.vine.perf` | `battery`, `balanced` or `performance` |
| `ro.boot.vine.fps_cap` | Frame rate limit, `0` for none |
| `ro.boot.vine.ashmem` | `device`, `memfd` (shim preloaded) or `missing` |
| `ro.boot.vine.root` | `1` only when the instance was created with root and the app allows it |
| `ro.product.*`, `ro.build.*`, `ro.serialno` | Present only when the instance has a device identity |

Add `service vine-gpu` and `gpu.sh` from the kit to your image. A ROM that is
Android 7 or 8 and uses `init.vine.rc` also gets the ashmem preload described
in the [ROM kit README](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/blob/main/rom/README.md).

## Booting as a virtual machine

Everything above describes the container engine. A ROM can also offer the
virtual machine engine, which needs no root. The two are independent: a
`.vrom` can carry container images, a machine profile, or both, and the
`engines` list of the manifest says which. The app picks one at start (Settings,
Engine and privileges).

In a machine the ROM boots like a phone. Its kernel starts its own `init`, loads
its own SELinux policy and brings up its own devices. There is **no container,
no `/vine` folder and no namespace patch**, so the init marker and
`INIT_PATCH.md` do not apply. The things a container ROM reads from `/vine`
have a machine equivalent:

| Container engine | Virtual machine engine |
|---|---|
| `/vine/boot.prop` and `ro.boot.vine.*` | `androidboot.vine.*` tokens on the kernel command line. Android's `init` turns every `androidboot.*` token into `ro.boot.*`, so `androidboot.vine.width=1080` is `ro.boot.vine.width`. Only values without spaces are passed. |
| `/vine/vinefb` | A `virtio-gpu` device. The phone reads the screen over VNC. |
| `/vine/agent.sock` | The virtio serial port `/dev/virtio-ports/org.vineos.agent`, same protocol. |
| `/vine/boot_completed` | The first frame. The instance is marked running when the screen draws, and the start fails if nothing draws within the boot timeout (120 seconds by default). |
| Loop mounted images | `virtio-blk` disks in manifest order, then a writable userdata disk. |
| `eth0` set up by the host | `virtio-net` behind QEMU's user mode NAT with QEMU's default addressing (DHCP, guest `10.0.2.15`, gateway `10.0.2.2`, DNS `10.0.2.3`). |

### The manifest section

```json
{
  "engines": ["container", "vm"],
  "vm": {
    "arch": "aarch64",
    "kernel": "Image",
    "initrd": "ramdisk.img",
    "cmdline": "console=ttyAMA0 androidboot.hardware=ranchu",
    "disks": [
      { "file": "system.img", "readOnly": true },
      { "file": "vendor.img", "readOnly": true }
    ],
    "transport": "pci"
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `arch` | yes | `aarch64` or `arm`. `arm` runs the 32 bit machine. |
| `kernel` | yes | File name of the kernel image in the `.vrom`. |
| `initrd` | no | Ramdisk file name, empty or absent for none. |
| `cmdline` | no | The ROM's kernel command line, printable ASCII, 1536 characters at most. |
| `disks` | yes | One to eight disks, `readOnly` defaults to true, no file twice. `vda` is the first. |
| `userdata` | no | Name of the writable disk, default `userdata.img`. It is created as a sparse file of the instance's storage size and must not be in `disks`. The ROM formats it on first boot. |
| `machine` | no | QEMU machine, default `virt`. |
| `cpu` | no | `max` for `aarch64`, `cortex-a15` for `arm`. |
| `gic` | no | Interrupt controller version, `max` for `aarch64`, `2` for `arm`. |
| `transport` | no | `pci` (default) or `mmio`. |

File names are plain names (letters, digits, dot, dash, underscore, 64
characters at most, no `..`). Anything else makes VineOS ignore the profile, so
a hostile manifest never reaches the QEMU command line.
`rom/package_vrom.py --vm-kernel` writes the section for you.

### What the kernel and the ROM need

- Drivers for `virtio-blk`, `virtio-gpu` (with DRM framebuffer console or a
  display stack that can use it), `virtio-input`, `virtio-rng`, `virtio-net`,
  `virtio-console` (for the agent port) and the PCI host controller of QEMU's
  `virt` machine, or the MMIO transport for kernels without PCI.
- A PL011 UART on `ttyAMA0` for the console. VineOS keeps what the kernel prints
  as `console.log` in the instance folder and shows the tail in the diagnostics.
- A key layout that maps Escape to `BACK`, Super to `HOME` and Menu to
  `APP_SWITCH`, for guests that run without the agent.
- `VineAgent` started at boot, listening on the serial port, for real
  multi-touch, text, the app list, icons, shortcuts and clean power off
  (VineOS sends `exec` with `setprop sys.powerctl shutdown`, see the agent
  protocol above).

### Honest limits

- The engine is emulation. It has no KVM, so a ROM runs at a fraction of its
  native speed.
- No Android image has booted in it yet. The command line, the manifest checks,
  the agent protocol, the VNC bridge and the QMP client are tested on a host.
  Treat the first real boot as the open milestone.
- The app needs the QEMU libraries. Without them the app says the build does
  not include QEMU for that architecture, see
  [Building](../guides/BUILDING.md#building-the-qemu-machine-engine).
