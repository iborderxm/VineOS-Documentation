# Contributing to VineOS

Thank you for considering a contribution. VineOS is a community-driven
project and every contribution, big or small, matters.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to contribute](#ways-to-contribute)
- [Getting help](#getting-help)
- [Before you start](#before-you-start)
- [Development setup](#development-setup)
- [Project structure](#project-structure)
- [Coding standards](#coding-standards)
- [Branching strategy](#branching-strategy)
- [Commit messages](#commit-messages)
- [Opening a merge request](#opening-a-merge-request)
- [Issue reporting](#issue-reporting)
- [Contributing ROM images](#contributing-rom-images)
- [Security vulnerabilities](#security-vulnerabilities)

## Code of Conduct

By participating in this project, you agree to be respectful to all
contributors regardless of experience level, background, or opinion.
Harassment, gatekeeping, and bad-faith criticism will not be tolerated. See
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for the full policy.

## Ways to contribute

You don't need to write code to contribute:

- **Report bugs**: open an [issue on GitLab](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/issues) with as much detail as possible
- **Test on your device**, especially useful if you own an arm64-only device or a less common host ABI like x86_64
- **Improve documentation**: fix typos, add examples, clarify confusing sections in any file of this repository (see the [documentation index](../README.md))
- **Build ROM images**: the project currently has no bootable ROM; this is the single biggest blocker
- **Cross-compile QEMU** for additional host ABIs, see [BUILDING.md](../guides/BUILDING.md#building-qemu-arm)
- **Review merge requests**, a second pair of eyes on MRs is always helpful
- **Write code**, see the [Roadmap](https://gitlab.com/Hexadecinull/VineOS/VineOS#roadmap) for what's most needed

## Getting help

Stuck, or not sure where to start? Ask in the [VineOS Discord](https://discord.gg/sVgCAdgGgR).
Maintainers and other contributors hang out there, and it's the fastest way
to get a second opinion before you open an issue or a merge request.

## Before you start

For anything beyond a typo fix:

1. Check existing issues and merge requests to make sure nobody else is already working on it.
2. Open an issue first for significant changes (new features, architectural changes, large refactors), so effort isn't wasted if the direction isn't one the project wants to take.
3. For small, obvious fixes (typos, formatting, broken links), feel free to open a merge request directly.

## Development setup

See [BUILDING.md](../guides/BUILDING.md) for the full environment setup. Short version:

- Android Studio 2025.3+ (needed for AGP 9.2 / API 37 support)
- NDK r27+, CMake 3.22+, JDK 17 (bundled with Android Studio)
- A device or emulator for testing; VineOS now builds for `arm64-v8a`,
  `armeabi-v7a`, `x86_64`, and `x86` hosts, so a wider range of hardware
  works than before

## Project structure

```text
VineOS/
├── app/
│   ├── build.gradle.kts             App-level build config
│   ├── proguard-rules.pro           R8/ProGuard rules for release builds
│   ├── .gitignore                   Module-scoped ignores
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml
│       │   ├── java/com/hexadecinull/vineos/
│       │   │   ├── MainActivity.kt      Compose host + NavHost
│       │   │   ├── VineApplication.kt   Hilt app class
│       │   │   ├── ui/                  All Compose UI
│       │   │   │   ├── theme/           Material You theming
│       │   │   │   ├── navigation/      Screen definitions + nav graph
│       │   │   │   ├── screens/         HomeScreen, ROMsScreen, SettingsScreen, ...
│       │   │   │   └── components/      Reusable composables (InstanceCard, etc.)
│       │   │   ├── data/
│       │   │   │   ├── models/          VMInstance, ROMImage, AbiCompat, ...
│       │   │   │   └── repository/      InstanceRepository, ROMRepository, VineDatabase
│       │   │   ├── domain/
│       │   │   │   ├── VineVMManager.kt VM lifecycle orchestrator
│       │   │   │   ├── InstanceProvisioner.kt, DisplayPlanner.kt, StorageSizing.kt
│       │   │   │   └── shortcuts/       Home screen app shortcuts
│       │   │   ├── helper/              Root helper client and the helper and guest protocols
│       │   │   ├── service/
│       │   │   │   └── VineService.kt   Foreground service
│       │   │   └── native/
│       │   │       └── VineRuntime.kt   JNI bridge
│       │   └── cpp/                     C++17 native code
│       │       ├── CMakeLists.txt
│       │       ├── vine_runtime.cpp     JNI entry points
│       │       ├── container/           Linux namespace container engine
│       │       ├── helper/              Root helper server and guest agent link
│       │       ├── qemu_bridge/         QEMU binary verification + binfmt_misc
│       │       ├── display/             vinefb contract, reader and Surface bridge
│       │       ├── diagnostics/         What the kernel offers the engine
│       │       ├── utils/               Logging, filesystem, process helpers
│       │       └── tests/native/        Host tests with a fake ROM
│       └── test/, androidTest/          Unit and instrumented tests
├── rom/                              Guest side ROM kit: agent, init scripts, vinefb writer, .vrom packer
├── scripts/                          CI helpers and the ROM manifest generator
├── .gitlab/                          Issue and merge request templates
├── .gitlab-ci.yml                    CI/CD pipeline
├── renovate.json                     Automated dependency updates (Renovate)
├── cliff.toml                        Release notes configuration (git-cliff)
├── gradle/
│   └── libs.versions.toml            Centralized dependency versions
└── README.md                         Project overview
```

The documentation lives in [VineOS-Documentation](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation) and the website in
[VineOS-Website](https://gitlab.com/Hexadecinull/VineOS/VineOS-Website), each in its own repository.

## Coding standards

### Kotlin

- Follow the [official Kotlin coding conventions](https://kotlinlang.org/docs/coding-conventions.html)
- Follow the [Jetpack Compose API guidelines](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/compose/docs/compose-api-guidelines.md) for Composable functions
- 4-space indentation, no tabs
- No hardcoded strings in UI code; user-visible strings go in `res/values/strings.xml`
- Suspending functions that touch the native layer run on `Dispatchers.IO`
- Prefer `StateFlow` over `LiveData` for observable state
- `PascalCase` for Composable functions, `camelCase` for everything else
- No comments on self-explanatory code. Where a comment earns its place
  (a non-obvious workaround, a "why" that isn't visible in the code), it
  must be a single `//` line, however long. No multi-line comment blocks,
  no `/** */` doc comments, no ASCII-art section dividers.
- `./gradlew ktlintCheck` must pass; see `.editorconfig` for the house style

```kotlin
@Composable
fun InstanceCard(
    instance: VMInstance,
    onLaunchClick: (VMInstance) -> Unit,
    modifier: Modifier = Modifier,
) {
    // ...
}
```

### C/C++ (NDK)

- C++17 throughout, no older standards
- Follow the [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) with one exception: `snake_case` for functions and variables, not `CamelCase`
- All code lives in the `vine` namespace (or sub-namespaces like `vine::qemu`)
- Always check syscall return values and log errors with `VINE_LOGE_ERRNO()`
- No raw `new`/`delete`; use smart pointers
- `std::string`/`std::vector`, not manual C-string allocation
- No `printf`; use the `VINE_LOG*` macros, which route to `__android_log_print`
- Same comment policy as Kotlin: single-line `//` only, short and genuinely useful

```cpp
bool Container::setup_binfmt_misc() {
    if (config_.qemu_arm_path.empty()) {
        VINE_LOGE("qemu_arm_path not set in config");
        return false;
    }
    // ...
}
```

### Style: dashes

Use a hyphen, comma, or period instead of an em dash in code comments, doc
strings, commit messages, and documentation. This is a house convention,
not a Kotlin or C++ standard.

## Branching strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, always buildable. Direct pushes blocked. |
| `dev` | Integration branch for ongoing work. Merge requests land here first. |
| `feature/<name>` | New features, branched from `dev` |
| `fix/<name>` | Bug fixes, branched from `dev` (or `main` for hotfixes) |
| `docs/<name>` | Documentation-only changes |
| `rom/<name>` | ROM image builds and tooling |

Examples: `feature/framebuffer-surfaceview`, `fix/qemu-binfmt-registration`,
`docs/building-qemu-cross-compile`, `rom/android-7-aosp-build`.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/).

```text
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no behavior change |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `build` | Build system / dependencies |
| `ci` | CI configuration |
| `chore` | Maintenance (updating `.gitignore`, etc.) |

Scopes (optional but encouraged): `ui`, `native`, `container`, `qemu`,
`rom`, `service`, `jni`, `theme`, `deps`.

```text
feat(container): implement pivot_root namespace isolation
fix(qemu): use F flag in binfmt_misc registration for chroot compatibility
docs(building): add qemu-arm cross-compile instructions per host ABI
ci: add renovate config for gradle and gitlab-ci
refactor(native): move AArch32 detection to vine_utils
```

Rules: keep the subject line under 72 characters, use the imperative mood
("add" not "added"), reference issues in the footer (`Closes #42`), and
mark breaking changes with `BREAKING CHANGE:` in the footer.

## Opening a merge request

1. Fork the repo and branch from `dev` (not `main`)
2. Make your changes
3. Confirm the checks CI will run also pass locally:

   ```bash
   ./gradlew ktlintCheck
   ./gradlew lint
   ./gradlew test
   ```

4. Add or update tests if your change touches logic. Changes to the native
   engine also need `sudo sh app/src/main/cpp/tests/native/run_tests.sh` on a
   Linux machine, see [BUILDING.md](../guides/BUILDING.md#running-the-tests)
5. Update the [documentation](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation) (and inline comments, sparingly) if needed
6. Open the merge request against `dev`, fill in the merge request template, and link related issues

CI runs lint, build, and test automatically. A maintainer will review within
a few days; requested changes are normal, not a rejection. Approved merge requests are
squash-merged into `dev`.

## Issue reporting

Bug reports should include:

- VineOS version (Settings → About)
- Device model and Android version
- Host CPU ABI list (Settings → About → Host ABI, or `adb shell getprop ro.product.cpu.abilist`)
- Steps to reproduce, as specific as possible
- Expected vs actual behavior
- Logcat output: `adb logcat -s VineRuntime` during the issue, with the relevant section pasted in
- ROM version, if the issue happens inside a running instance

Feature requests should describe the use case, how you'd expect it to
work, and any alternatives considered.

## Contributing ROM images

Building and contributing AOSP-based ROM images is one of the
highest-impact ways to help. See [BUILDING.md](../guides/BUILDING.md#building-aosp-rom-images)
for the full guide. Requirements for acceptance:

- Built from AOSP source, no proprietary blobs in the system image
- Boots in VineOS, either as a container ROM (the init patch and display writer from the `rom/` kit) or with a `vm` profile for a machine VineOS offers. Google's Android Emulator system images (goldfish, ranchu) do not qualify, see [ANDROID_X86.md](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/blob/main/rom/ANDROID_X86.md) for a ROM that boots without root
- Minimal size: strip unnecessary system apps, keep only what's needed to boot and run user apps
- Dual ABI for ARM ROMs: both `arm64-v8a` and `armeabi-v7a` libraries in `/system/lib` and `/system/lib64`
- SHA-256 hash provided for integrity verification
- For container ROMs, a VineOS-specific `init.vine.rc`
- No Google Play Services in the base image; GApps are an optional layer the user installs

ROM images are distributed via the VineOS CDN and contributed through a
manifest merge request, not uploaded to the git repo directly (they're large binaries).

## Security vulnerabilities

**Do not open a public issue for security vulnerabilities.** Report them
privately as a confidential GitLab issue; see
[SECURITY.md](SECURITY.md) for the full policy and response timeline.
