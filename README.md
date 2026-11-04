# VineOS Documentation

[![Pipeline status](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation/badges/main/pipeline.svg)](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation/-/pipelines)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/discord/1558189985230889033?logo=discord&logoColor=white&label=Discord&color=5865F2)](https://discord.gg/sVgCAdgGgR)

The documentation for [VineOS](https://gitlab.com/Hexadecinull/VineOS/VineOS),
a free, open-source, ad-free Android-on-Android virtual machine. Everything
here is plain Markdown, rendered by GitLab.

## The VineOS repositories

| Repository | What it contains |
|---|---|
| [VineOS](https://gitlab.com/Hexadecinull/VineOS/VineOS) | The Android app, the native runtime, the guest side ROM kit, and CI |
| [VineOS-Website](https://gitlab.com/Hexadecinull/VineOS/VineOS-Website) | The project website |
| [VineOS-Documentation](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation) | This repository |

## Guides

For people who want to use, build, or release VineOS.

- **[USAGE.md](guides/USAGE.md)**: how to use the app, downloading ROMs,
  creating and running instances, display settings, home screen shortcuts,
  snapshots, and troubleshooting.
- **[BUILDING.md](guides/BUILDING.md)**: building the Android app,
  cross-compiling `qemu-arm` for each supported host ABI, building the QEMU
  libraries of the no-root machine engine, building AOSP ROM images, and the
  CI/CD pipeline.
- **[RELEASE_SETUP.md](guides/RELEASE_SETUP.md)**: signing keystore, GitLab
  CI/CD variables, and how to run a release.
- **[ROM_STORE_SETUP.md](guides/ROM_STORE_SETUP.md)**: hosting your own ROM
  store and the website.

## Reference

For people who want to know how VineOS works.

- **[ARCHITECTURE.md](reference/ARCHITECTURE.md)**: the Kotlin app layers,
  the C++ engine and root helper, the virtual machine engine, root and Shizuku
  detection, instance lifecycle, display and input pipelines, storage,
  networking, ABI compatibility, testing, and CI/CD.
- **[ROM_INTEGRATION.md](reference/ROM_INTEGRATION.md)**: the contract between
  the engine and a ROM: boot properties, the init marker, the framebuffer,
  the guest agent, the virtual machine profile, and what is still unproven.
- **[NOROOT_RESEARCH.md](reference/NOROOT_RESEARCH.md)**: what Wireless
  Debugging and Shizuku can and can't unlock, and why the no-root path
  VineOS ships is a QEMU virtual machine inside the app.

## Project

How the project is run, and the policies that apply to it.

- **[CONTRIBUTING.md](project/CONTRIBUTING.md)**: how to contribute code,
  documentation, or ROM images, coding standards, branching, and commit
  message conventions.
- **[CODE_OF_CONDUCT.md](project/CODE_OF_CONDUCT.md)**: expected behavior for
  everyone participating in the project.
- **[SECURITY.md](project/SECURITY.md)**: how to report a vulnerability,
  response timelines, and the security design model.
- **[PRIVACY.md](project/PRIVACY.md)**: what data the app handles, which is
  very little, and why.
- **[TERMS.md](project/TERMS.md)**: terms of use, license, and liability.

Everything here is kept in sync with the current state of the `main` branch
of VineOS. If something looks out of date, that's a documentation bug, so
[open an issue](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation/-/issues)
or a merge request.

## Contributing to the docs

1. Fork this repository and branch from `main`.
2. Edit or add Markdown files. Keep paragraphs hard-wrapped around 80
   columns and use a comma, hyphen, or period instead of an em dash.
3. Run the checks locally, they are the same ones CI runs:

   ```bash
   npm ci
   npm run lint
   ```

4. Open a merge request and fill in the template.

`npm run lint` runs [markdownlint](https://github.com/DavidAnson/markdownlint-cli2)
on every Markdown file, then `scripts/check_links.py`, which verifies that
every relative link and heading anchor resolves. The link checker needs
Python 3.9 or newer and nothing else.

## Community

Questions, ideas, or just want to hang out? Join the
[VineOS Discord](https://discord.gg/sVgCAdgGgR).

## License

Like the rest of VineOS, this documentation is licensed under the GNU General
Public License v3.0. See [LICENSE](LICENSE).

## Project policies

- **[USER_AGREEMENT.md](project/USER_AGREEMENT.md)**: the agreement shown in the
  app at first run and under Settings.
- **[PRIVACY.md](project/PRIVACY.md)**: what VineOS stores and which network
  requests it makes.
- **[TERMS.md](project/TERMS.md)**: terms of service.
- **[SECURITY.md](project/SECURITY.md)** and
  **[CODE_OF_CONDUCT.md](project/CODE_OF_CONDUCT.md)**.

## Guides added in 0.2.0

- **[Troubleshooting](guides/TROUBLESHOOTING.md)**: logs, privilege levels, Shizuku and
  Wireless debugging, Android 7 boot checklist.
- **[Device identity](guides/DEVICE_IDENTITY.md)**: spoofing the model, serial and build
  fingerprint of an instance.

## Added in 0.2.5

- The no-root virtual machine engine: see
  [Engines: with and without root](guides/USAGE.md#engines-with-and-without-root),
  [Booting as a virtual machine](reference/ROM_INTEGRATION.md#booting-as-a-virtual-machine)
  and [Virtual machine engine](reference/ARCHITECTURE.md#virtual-machine-engine-025).
- Root managers and Shizuku forks: see
  [Root is refused or not found](guides/TROUBLESHOOTING.md#root-is-refused-or-not-found).
- [Developer options](guides/USAGE.md#developer-options) and
  [building the QEMU libraries](guides/BUILDING.md#building-the-qemu-machine-engine).
