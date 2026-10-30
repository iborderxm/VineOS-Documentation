# Building VineOS

This covers building VineOS from source: the Android app (Kotlin + NDK), the
`qemu-arm` static binaries (one per host ABI), and AOSP ROM images.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Building the Android app](#building-the-android-app)
- [Running the tests](#running-the-tests)
- [Building qemu-arm](#building-qemu-arm)
- [Building AOSP ROM images](#building-aosp-rom-images)
- [CI/CD](#cicd)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

| Tool | Version | Notes |
|---|---|---|
| Android Studio | 2025.3+ (Narwhal or newer) | Needed for AGP 9.2 / API 37 support. [Download](https://developer.android.com/studio) |
| Android NDK | r27+ | Install via SDK Manager |
| CMake | 3.22.1+ | Install via SDK Manager |
| JDK | 17 | Bundled with Android Studio, do not substitute a different JDK |
| Git | Any recent | |

VineOS targets `compileSdk`/`targetSdk` 37 (Android 17) with `minSdk` 26
(Android 8.0). Gradle 9.5+ and AGP 9.2+ are required; AGP 9 compiles Kotlin
directly (no separate `org.jetbrains.kotlin.android` plugin), so an older
AGP will not sync this project.

### For qemu-arm cross-compilation (recommended)

| Tool | Notes |
|---|---|
| Ubuntu 22.04+ / Debian 12+ | WSL2 works fine on Windows |
| A cross-compiler per target host ABI | see the [qemu-arm](#building-qemu-arm) section |
| `ninja-build`, `python3`, `meson` | QEMU's build system |
| `libglib2.0-dev` (cross variant per target) | QEMU dependency |

### For ROM image builds (advanced, heavy)

| Requirement | Notes |
|---|---|
| Ubuntu 20.04 or 22.04 x86_64 | macOS and Windows aren't supported for AOSP builds |
| 16+ GB RAM | 32 GB strongly recommended |
| 300+ GB free disk | AOSP source is ~200 GB, build artifacts add more |
| 8+ CPU cores | A full AOSP build takes 2 to 6 hours on fast hardware |
| Fast internet | AOSP source download is ~70 GB |

## Building the Android app

### 1. Clone and open

```bash
git clone https://gitlab.com/Hexadecinull/VineOS/VineOS.git
cd VineOS
```

Open the `VineOS/` directory in Android Studio, let Gradle sync finish, and
install any SDK components it prompts for (Android SDK Platform 37, NDK r27,
CMake 3.22.1).

### 2. Build and run

```bash
./gradlew assembleDebug      # Debug build, fastest for development
./gradlew installDebug       # Install on a connected device
./gradlew assembleRelease    # Minified release build, needs a signing keystore
```

### Build variants

| Variant | Package suffix | Minified | Debug symbols | Use case |
|---|---|---|---|---|
| `debug` | `.debug` | No | Yes | Development |
| `release` | *(none)* | Yes (ProGuard/R8, see `app/proguard-rules.pro`) | No | Distribution |

### Signing (release builds)

See [RELEASE_SETUP.md](RELEASE_SETUP.md) for the full guide: generating a
keystore, setting up the GitLab CI/CD variables the release pipeline
needs, and how to actually run a release. The short version for local builds only:
create a `keystore.properties` in the project root (covered by
`.gitignore`) with `storeFile`/`storePassword`/`keyAlias`/`keyPassword`,
and `app/build.gradle.kts` picks it up automatically. Without it,
`assembleRelease` still works locally, just producing an unsigned APK.

The native build produces two things per host ABI: `libvine_runtime.so`
(JNI, loaded by the app) and `libvine_helper.so`, which is really an
executable that the app starts as root with `su`. It is named like a library
so Android extracts it into the native library directory, which is why
`app/build.gradle.kts` sets `useLegacyPackaging = true` and links the C++
runtime statically. See
[ARCHITECTURE.md](../reference/ARCHITECTURE.md#native-pieces-c).

## Running the tests

| What | Command | Needs |
|---|---|---|
| Kotlin unit tests | `./gradlew :app:testDebugUnitTest` | The Android SDK, as for the app |
| Engine and helper on a Linux host | `sudo sh app/src/main/cpp/tests/native/run_tests.sh` | root, `g++`, `python3`, `mke2fs`, zlib, a kernel with loop devices. Run it on a Linux machine or in WSL2, not on a phone |
| Framebuffer reader, guest writer, presenter policy and display bridge | `sh app/src/main/cpp/tests/native/run_display_tests.sh` | `g++` |
| Guest agent protocol | `sh rom/agent/test/run_tests.sh` | a JDK |

The host engine test boots a small fake ROM through the real container code.
It does not boot Android, and it skips the NAT checks when the host has no
`ip` tool.

## Building qemu-arm

### Why it's needed, and why there's more than one binary now

VineOS bundles a statically linked `qemu-arm` binary that lets the guest run
32-bit ARM (armeabi-v7a) code on hosts whose CPU doesn't support AArch32
execution. Since VineOS now supports running on `arm64-v8a`, `armeabi-v7a`,
`x86_64`, and `x86` host devices (see `AbiCompat.kt` and
[ARCHITECTURE.md](../reference/ARCHITECTURE.md#abi-compatibility)), `qemu-arm` needs to be
cross-compiled once **per host ABI** so each one gets a binary it can execute
natively. There is no cross-ABI sharing: an x86_64 host cannot run an
arm64-v8a `qemu-arm` binary any more than it can run the guest code directly.

| Host ABI | jniLibs subdirectory | Typical cross-compiler prefix |
|---|---|---|
| `arm64-v8a` | `app/src/main/jniLibs/arm64-v8a/` | `aarch64-linux-gnu-` |
| `armeabi-v7a` | `app/src/main/jniLibs/armeabi-v7a/` | `arm-linux-gnueabihf-` |
| `x86_64` | `app/src/main/jniLibs/x86_64/` | `x86_64-linux-gnu-` (native on an x86_64 build host) |
| `x86` | `app/src/main/jniLibs/x86/` | `i686-linux-gnu-` |

Each binary must be statically linked (no runtime library dependencies
inside the container's mount namespace) and built from QEMU's user-mode
emulation target, not the full system emulator.

### Build environment (example: arm64-v8a host target)

```bash
sudo apt update
sudo apt install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
    ninja-build python3 python3-pip libglib2.0-dev pkg-config flex bison git
pip3 install meson
```

Swap the `gcc-aarch64-linux-gnu`/`g++-aarch64-linux-gnu` packages for the
matching cross-compiler when targeting a different host ABI (for example
`gcc-arm-linux-gnueabihf` for `armeabi-v7a`, or the system `gcc`/`g++` when
building natively for `x86_64`).

### Cross-compile qemu-arm

```bash
git clone https://gitlab.com/qemu-project/qemu.git
cd qemu
git checkout v11.0.0   # or latest stable

cat > android-arm64-cross.ini << 'EOF'
[binaries]
c = 'aarch64-linux-gnu-gcc'
cpp = 'aarch64-linux-gnu-g++'
ar = 'aarch64-linux-gnu-ar'
strip = 'aarch64-linux-gnu-strip'
pkgconfig = 'aarch64-linux-gnu-pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'

[properties]
c_link_args = ['-static']
cpp_link_args = ['-static']
EOF

mkdir build-android-arm64 && cd build-android-arm64
meson setup .. \
    --cross-file ../android-arm64-cross.ini \
    --buildtype=release --strip \
    -Dtarget-list=arm-linux-user \
    -Ddefault_library=static -Dstatic=true \
    -Ddocs=disabled -Dtests=false -Dtools=disabled \
    -Dguest-agent=disabled -Dslirp=disabled -Dfdt=disabled \
    -Dkvm=disabled -Dvnc=disabled -Dsdl=disabled -Dgtk=disabled \
    -Dopengl=disabled -Dvirtfs=disabled

ninja -j$(nproc)
```

Repeat with a matching cross-file (swap the `[binaries]` prefix and
`cpu_family`/`cpu`) for each additional host ABI you want to support. Verify
and strip each binary:

```bash
file build-android-arm64/qemu-arm
# Expected: ELF 64-bit LSB executable, ARM aarch64, statically linked
aarch64-linux-gnu-strip build-android-arm64/qemu-arm
du -sh build-android-arm64/qemu-arm   # typically ~5-15 MB stripped
```

### Placing the binaries

Android NDK packages JNI libraries from `jniLibs/`. Naming the binary with a
`.so` extension makes the Android build system treat it as a native library
and extract it to the device's native lib directory at install time:

```bash
mkdir -p app/src/main/jniLibs/arm64-v8a/
cp build-android-arm64/qemu-arm app/src/main/jniLibs/arm64-v8a/libqemu_arm.so
```

At runtime, VineOS finds it via `context.applicationInfo.nativeLibraryDir +
"/libqemu_arm.so"`, which resolves to the copy matching the device's own
primary ABI automatically, no Kotlin-side ABI branching needed.

> `jniLibs/` is in `.gitignore` because these binaries are large. They're
> distributed as GitLab release assets instead of being committed.

## Building AOSP ROM images

This is advanced and resource-intensive. Most contributors won't need to do
this; ROM images only need building once per Android version and are then
distributed via the VineOS CDN.

### Overview

VineOS ROM images are minimal AOSP system images targeting the `ranchu`
virtual device (the same reference virtual hardware platform the Android
Emulator uses), stripped of unnecessary apps and services.

### Host requirements

- Ubuntu 20.04 or 22.04 x86_64 (other distros may work but are untested)
- 16+ GB RAM (32 GB recommended), 300+ GB free disk, Python 3.9+

```bash
sudo apt update
sudo apt install -y git gnupg flex bison build-essential zip curl \
    libc6-dev libncurses5 x11proto-core-dev libx11-dev libgl1-mesa-dev \
    libxml2-utils xsltproc unzip fontconfig python3-pip python3-setuptools \
    openjdk-11-jdk

mkdir -p ~/bin
curl https://storage.googleapis.com/git-repo-downloads/repo > ~/bin/repo
chmod a+x ~/bin/repo
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

### Fetch AOSP source

For the Android 7.1.2 ROM (`vine-rom-7`):

```bash
mkdir ~/aosp-7 && cd ~/aosp-7
repo init -u https://android.googlesource.com/platform/manifest \
    -b android-7.1.2_r39 --depth=1
repo sync -c -j$(nproc) --no-tags --no-clone-bundle
```

Use a similar release tag for other Android versions.

### Configure, build, and package

```bash
cd ~/aosp-7
source build/envsetup.sh
lunch aosp_arm64-userdebug   # dual-ABI: arm64-v8a + armeabi-v7a in the guest

make -j$(nproc) 2>&1 | tee build.log
# Produces system.img, ramdisk.img, kernel, etc. in out/target/product/generic_arm64/
```

A stock AOSP build will not run in VineOS as it is. Before packaging, the
ROM needs the guest side kit from the `rom/` folder of the main repository:
a container aware `init`, the guest agent, a display writer for the `vinefb`
framebuffer and a few init scripts. `rom/INIT_PATCH.md` describes the `init`
changes and `rom/README.md` the rest. There are no ready-made AOSP patch
files yet, and no ROM has booted this way so far. See
[ROM_INTEGRATION.md](../reference/ROM_INTEGRATION.md).

### ROM image format (.vrom)

A `.vrom` file is a zip archive:

```text
vine-rom-7.vrom
├── manifest.json    ROM metadata: version, sha256s, API level, etc.
├── system.img       ext4 (or Android sparse) image, the Android /system partition
├── vendor.img       optional ext4 image, /vendor partition
└── ramdisk.img      Android ramdisk, contains /init
```

VineOS unpacks `ramdisk.img`, `vendor.img` and `system.img` and ignores
anything else in the archive. A `kernel` entry is skipped on purpose: guests
run on the phone's kernel, so a ROM kernel would never be used. When the
manifest lists a `sha256` for a file, the app checks it while unpacking and
refuses a damaged file.

`manifest.json`:

```json
{
  "id": "vine-rom-7",
  "displayName": "Android 7.1.2 Nougat",
  "androidVersion": "7.1.2",
  "apiLevel": 25,
  "sha256": { "system.img": "...", "vendor.img": "...", "ramdisk.img": "..." },
  "sizeBytes": 524288000,
  "supportedAbis": ["arm64-v8a", "armeabi-v7a"],
  "has32BitSupport": true,
  "releaseDate": "2025-01-01",
  "vineosMinVersion": "0.1.0"
}
```

`displayName`, `androidVersion`, `apiLevel` and `supportedAbis` are required
by the store manifest generator (`scripts/generate_manifest.py`). A ROM whose
only ABIs are 32-bit ARM is run through QEMU on hosts without AArch32
support.

Package it with the script from the main repository, which writes the
manifest and the per-file hashes for you:

```bash
python3 rom/package_vrom.py out/target/product/generic_arm64/ vine-rom-7.vrom \
    --name "Android 7.1.2 Nougat" --android-version 7.1.2 --api-level 25 \
    --abis arm64-v8a armeabi-v7a
```

The folder given first must hold `ramdisk.img` and `system.img`, and may hold
`vendor.img`.

## CI/CD

VineOS uses GitLab CI/CD, defined in `.gitlab-ci.yml` at the root of the
main repository, with helper scripts under `scripts/ci/`.

| Job | Stage | When it runs | What it does |
|---|---|---|---|
| `ktlint` | test | Branch and merge request pipelines | Kotlin style check (`:app:ktlintCheck`) |
| `android-lint` | test | Branch and merge request pipelines | Android lint (`:app:lintDebug`) |
| `unit-tests` | test | Branch and merge request pipelines | `:app:testDebugUnitTest`, results shown in the merge request |
| `native-display-tests` | test | Branch and merge request pipelines | Framebuffer reader and guest writer tests with plain `g++` |
| `rom-kit-tests` | test | Branch and merge request pipelines | Guest agent protocol tests on a JDK, syntax check of the Python tools |
| `secret_detection` | test | Branch and merge request pipelines | GitLab's secret detection scan |
| `build-debug` | build | After the three checks above pass | Debug APK build, including the NDK compile |
| `nightly` | build | Pipeline schedule with `SCHEDULE_TYPE=nightly` | Unit tests, then a debug APK kept for 7 days |
| `release-validate`, `release-build`, `release-publish` | test, build, release | Manual pipeline with `RELEASE_VERSION_TAG` set | Signed release and debug APKs, GitLab release with both attached (see [RELEASE_SETUP.md](RELEASE_SETUP.md)) |
| `renovate` | test | Pipeline schedule with `SCHEDULE_TYPE=renovate` | Self-hosted Renovate run for every VineOS repository |

Renovate (`renovate.json`) opens merge requests for outdated Gradle
dependencies, grouped by Compose, other AndroidX, and Kotlin/KSP, and for
the pinned CI images. They go through the same pipeline as any other merge
request.

### Pipeline schedules

Two schedules are created once under **Build → Pipeline schedules** in the
main repository. Both use target branch `main`:

| Schedule | Cron | Variables |
|---|---|---|
| Nightly build | `0 2 * * *` | `SCHEDULE_TYPE` = `nightly` |
| Renovate | `0 4 * * 1` | `SCHEDULE_TYPE` = `renovate` |

The Renovate job also needs a masked CI/CD variable `RENOVATE_TOKEN`: an
access token with the `api` scope that can read and write all three VineOS
repositories. Skip it if you use the Mend-hosted Renovate app instead.

## Troubleshooting

**The root helper does not start**
The helper is started with `su`. Check that the superuser prompt was granted
and that your root manager lists VineOS. The Show diagnostics panel of an
instance reports the helper's state.

**`unshare() failed: Operation not permitted`**
The host kernel or SELinux policy is blocking namespace creation. Check
`adb shell dmesg | grep denied` for SELinux denials, and the device report
in Show diagnostics for which namespaces the kernel offers.

**`pivot_root` fails and the engine moves the root instead**
When the phone's own root is an initramfs, `pivot_root` cannot work, so the
engine mounts the guest root over it and uses `chroot`. This is expected on
such devices.

**`this ROM's init is not container aware`**
The ROM's `init` lacks the `VINE_CONTAINER_INIT_V1` marker. See
`rom/INIT_PATCH.md`. The helper's `start` command has an
`allow_unpatched=1` option that skips the check for engine experiments. The app
never sets it, and using it on a real phone is unsafe.

**QEMU binary not found at `nativeLibraryDir/libqemu_arm.so`**
The matching `jniLibs/<abi>/libqemu_arm.so` is missing for the device's host
ABI. See [Building qemu-arm](#building-qemu-arm).

**`mount(rootfs) failed`**
The loop device couldn't mount the ROM image: it may be corrupted
(re-download and verify SHA-256), or there's a permissions issue (check
`dmesg`).

**Gradle sync fails with `NDK not found`**
Install NDK r27 via SDK Manager, and confirm `local.properties` has the
correct `sdk.dir`.

**Gradle sync fails on the `kotlin-android` plugin**
AGP 9's built-in Kotlin support means `org.jetbrains.kotlin.android` is no
longer applied. If a fork or branch still references it, remove that plugin
alias; see the [AGP 9 migration guide](https://developer.android.com/build/migrate-to-built-in-kotlin).

**QEMU cross-compile fails with missing `libglib-2.0`**

```bash
sudo apt install libglib2.0-dev-aarch64-cross   # or the matching cross variant
```

Then re-run meson with `--pkg-config-path` pointing at the cross pkgconfig dir.
