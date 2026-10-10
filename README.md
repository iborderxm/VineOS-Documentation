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
| [VineOS](https://gitlab.com/Hexadecinull/VineOS/VineOS) | The Android app, the native runtime, and CI |
| [VineOS-Website](https://gitlab.com/Hexadecinull/VineOS/VineOS-Website) | The project website |
| [VineOS-Documentation](https://gitlab.com/Hexadecinull/VineOS/VineOS-Documentation) | This repository |

## Guides

For people who want to use, build, or release VineOS.

- **[USAGE.md](guides/USAGE.md)**: how to use the app, downloading ROMs,
  creating and running instances, settings, and troubleshooting.
- **[BUILDING.md](guides/BUILDING.md)**: building the Android app,
  cross-compiling `qemu-arm` for each supported host ABI, building AOSP ROM
  images, and the CI/CD pipeline.
- **[RELEASE_SETUP.md](guides/RELEASE_SETUP.md)**: signing keystore, GitLab
  CI/CD variables, and how to run a release.
- **[ROM_STORE_SETUP.md](guides/ROM_STORE_SETUP.md)**: hosting your own ROM
  store and the website.

## Reference

For people who want to know how VineOS works.

- **[ARCHITECTURE.md](reference/ARCHITECTURE.md)**: the Kotlin app layers,
  the C++ native runtime, JNI bridge, instance lifecycle, display and input
  pipelines, ABI compatibility, testing, and CI/CD.
- **[NOROOT_RESEARCH.md](reference/NOROOT_RESEARCH.md)**: what Wireless
  Debugging and Shizuku can and can't unlock, toward a no-root path.

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
