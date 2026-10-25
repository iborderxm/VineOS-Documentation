# Device identity

Each instance can present a different device to the apps inside it. The
settings are under **Instance settings, Device identity** and are saved per
instance. Nothing is applied until you turn on **Present a different device**.

Use this only where it is allowed. See section 3 of the
[User Agreement](../project/USER_AGREEMENT.md).

## What you can set

| Field | What it changes |
| --- | --- |
| Brand, manufacturer, model, device codename, product name, marketing name | `ro.product.*` including the per partition variants (`system`, `vendor`, `odm`, `product`, `system_ext`) |
| Board and chipset platform | `ro.product.board`, `ro.board.platform` |
| Serial number | `ro.serialno`, `ro.boot.serialno` and the `androidboot.serialno` kernel argument |
| Android ID | The `android_id` secure setting, written after boot |
| Device name | The `device_name` global setting and the Bluetooth name, written after boot |
| Build ID, build display ID, incremental version, security patch | `ro.build.id`, `ro.build.display.id`, `ro.build.version.incremental`, `ro.build.version.security_patch` |
| Build fingerprint | `ro.build.fingerprint` and its partition variants |

Leave a field empty and the ROM keeps its own value. With **Build the
fingerprint automatically** on and no fingerprint typed, VineOS composes
`brand/product/device:release/buildid/incremental:user/release-keys` from the
other fields and the ROM's Android version. A fingerprint made up this way is
consistent but not real, and apps that cross check it against a database can
still notice.

The preset chips fill brand, manufacturer, model, codename, product name,
marketing name, board and platform for a few real phones. Press **New serial
and Android ID** for fresh random identifiers.

## How it works

The engine never edits the ROM image. At every start, inside the new mount
namespace and after the system and vendor images are mounted read only, it:

1. reads `/system/build.prop` and `/vendor/build.prop`,
2. rewrites every occurrence of each overridden key (Android keeps the first
   definition of a read only property, so duplicates must all change) and
   appends keys the file lacked,
3. writes the result to `spoof/` in the instance folder and bind mounts it over
   the original file inside the guest.

The same values are also written into the managed block of the ramdisk's
`default.prop`, so the result does not depend on the load order of an Android
version. Values are validated before use: printable ASCII only, 91 characters
at most, no line breaks. Unknown keys are dropped, and the engine accepts
short names such as `model`, never raw property names.

A second instance without spoofing still sees the real image, which the
engine tests check.

## Limits

- Apps can detect emulation through many other signals (CPU details, sensors,
  `/proc`, timing, Play Integrity). A changed model name does not hide those.
- Telephony identifiers (IMEI, phone number) are not spoofed because instances
  have no radio.
- The Android ID and device name are set after boot, so an app that runs
  before that, very early, can see the original for a moment.
