# User Agreement

**Version 1.0, effective October 2026. Applies to VineOS 0.1.1-alpha and later.**

This agreement is between you and the VineOS project (the maintainers and
contributors of VineOS, together "we"). It covers the VineOS Android app, its
native engine, and the guest ROM kit. By finishing the first-run setup,
installing, building, or using VineOS you accept it. If you do not accept it,
do not use VineOS.

VineOS is free software under the GNU General Public License v3.0. Nothing
here limits the rights the GPL gives you over the source code. Where this
agreement and the GPL conflict about source code or redistribution, the GPL
wins. The [Terms of Service](TERMS.md) and the [Privacy Policy](PRIVACY.md)
are part of this agreement.

## 1. What VineOS does

VineOS runs one or more separate Android systems ("instances") on your device
by creating Linux namespaces and mounting a ROM image. It needs elevated
privileges to do that, which you provide through root or through Shizuku.
Some ROMs need a 32 bit translation layer (QEMU user mode emulation) to run
on phones that cannot execute 32 bit code natively.

VineOS is alpha software. It can fail to boot a ROM, use a lot of battery,
memory or storage, and in the worst case disturb the host system. Read the
[Security notes](SECURITY.md) before enabling root in an instance.

## 2. Privileged access

- You decide whether VineOS gets root or Shizuku access. VineOS only uses it
  to start and manage the instances you start and, in the Terminal, to run
  commands you type yourself.
- The Terminal runs exactly what you enter, with exactly the privileges of
  the target you selected. Commands run as root or as the ADB shell user can
  damage your device or delete data. You are responsible for what you run.
- Shizuku and its forks are separate projects with their own licenses and
  terms. VineOS only talks to the service they expose.
- Do not run commands or scripts from people you do not trust.

## 3. Device identity settings (spoofing)

Instances can present a different brand, model, serial number, Android ID and
build fingerprint to the apps inside them. These settings exist for testing,
compatibility and privacy.

- You may use them only where doing so is lawful and allowed by the terms of
  the services you use.
- You must not use them to commit fraud, evade a ban or a security control
  you are not allowed to evade, impersonate someone, or defeat licensing,
  anti cheat or payment protections.
- Presenting a different device does not make an app or service treat you
  differently in a way you are entitled to rely on. Services may detect
  emulation anyway and may restrict or close your account. That risk is yours.

## 4. ROMs and the software you run inside instances

- VineOS ships no ROM. Whether you may download, build, modify or run a given
  ROM depends on that ROM's own license and source. That is your
  responsibility.
- Software you install inside an instance, and the accounts you sign in to
  there, are outside VineOS and governed by their own terms.
- Do not use VineOS to run software in a way its developer prohibits.

## 5. Acceptable use

You agree not to use VineOS to attack, probe or disrupt any system or person,
to access data you are not authorised to access, to distribute malware, or to
break the law that applies to you. You may not remove the license notices from
VineOS or misrepresent who wrote it.

## 6. Logs and diagnostic reports

VineOS keeps an in-app log and can save or share it, and can build a
diagnostic report. A report contains technical details about your device,
Android build, kernel, ABIs, Shizuku state and recent log lines. It can
include device identifiers such as the build fingerprint. VineOS never sends
it anywhere. If you attach one to a bug report, you decide what to share. Look
through it first.

## 7. No warranty

VineOS is provided "as is", without warranty of any kind, express or implied,
including merchantability, fitness for a particular purpose and
non-infringement. We do not promise that it will boot any given ROM, run
without errors, protect your data, or keep running in the background.

## 8. Limitation of liability

To the maximum extent the law allows, the VineOS maintainers and contributors
are not liable for any direct, indirect, incidental, special, consequential or
punitive damages, or for any loss of data, device damage, account action,
lost profit or lost time, arising from your use of VineOS or of anything you
run with it, even if we were told such damage was possible. Some places do not
allow these limits. In those places the limits apply as far as the law
permits.

## 9. Your data

VineOS has no accounts, no analytics and no advertising, and does not send
your data to us or to third parties. See the [Privacy Policy](PRIVACY.md) for
what it stores on your device and the network requests it does make.

## 10. Contributions

If you contribute code, translations or documentation, you license them under
GPL-3.0 (or CC BY-SA 4.0 for documentation where the repository says so) and
confirm you have the right to do that. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 11. No affiliation

VineOS is an independent community project. It is not affiliated with,
endorsed by or sponsored by Google, the Android Open Source Project, the
Shizuku project or any device maker. "Android" is a trademark of Google LLC.

## 12. Changes and ending the agreement

We may update this agreement as the project grows. Material changes will be
listed in the release notes and the new text will be shown in the app. You may
stop using VineOS at any time by uninstalling it. Sections 7 and 8 continue to
apply after that.

## 13. Contact

Questions go to the [issue tracker](https://gitlab.com/Hexadecinull/VineOS/VineOS/-/issues).
Security problems follow the process in [SECURITY.md](SECURITY.md).
