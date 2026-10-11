# Setting up and running VineOS releases

Everything needed to get the release pipeline in `.gitlab-ci.yml` working,
from zero to a signed APK attached to a GitLab release. This is the guide
referenced from [BUILDING.md](BUILDING.md), pulled out on its own since
it's easy to miss buried in a longer doc.

## 1. Generate a signing keystore

Skip this if you already have one.

```bash
keytool -genkey -v -keystore vineos-release.jks -alias vineos -keyalg RSA -keysize 2048 -validity 10000
```

You'll be prompted for a store password, a key password (can be the
same as the store password), and some certificate identity fields
(name, org, etc., these can be anything, they're not security-relevant).
Keep the `.jks` file and both passwords, you need all three for both
local builds and the CI/CD variables below.

## 2. Local builds (optional, only needed if you build release APKs yourself)

Create `keystore.properties` in the project root (already in
`.gitignore`, never commit it):

```properties
storeFile=/path/to/your/vineos-release.jks
storePassword=your_store_password
keyAlias=vineos
keyPassword=your_key_password
```

`app/build.gradle.kts` reads this automatically. Without it,
`./gradlew assembleRelease` still works but produces an unsigned APK,
so a plain checkout never fails to build just because nobody's set up
signing locally.

## 3. GitLab CI/CD variables

This is the part that actually matters for the release pipeline, which
runs on GitLab's runners and has no access to your local
`keystore.properties`. It needs four CI/CD variables instead.

In the main repository on GitLab: **Settings → CI/CD → Variables → Add
variable**, add each of these. Tick **Protect variable** on all four and
**Mask variable** wherever GitLab accepts it, and untick **Expand variable
reference** so a `$` in a password is kept literally:

| Variable | Value |
|---|---|
| `RELEASE_KEYSTORE_BASE64` | The keystore file, base64-encoded (command below) |
| `RELEASE_STORE_PASSWORD` | The keystore's store password |
| `RELEASE_KEY_ALIAS` | The key alias (`vineos` if you used the command above) |
| `RELEASE_KEY_PASSWORD` | The password for that specific key |

Protected variables are only exposed to pipelines that run on a protected
branch or tag, so start the release pipeline from `main`, which is
protected by default. GitLab refuses to mask values with spaces or some
special characters; if that happens to a password, leave **Mask variable**
off for that one and keep **Protect variable** on.

To get the base64 value for `RELEASE_KEYSTORE_BASE64`:

```bash
base64 -w 0 vineos-release.jks > keystore.b64
cat keystore.b64
```

Copy the entire single-line output as the variable's value. Delete
`keystore.b64` afterward, it was only there to get the text onto your
clipboard, no reason to leave a plaintext copy sitting around.

**Back up the `.jks` file itself somewhere outside the repo** (password
manager file storage, an encrypted drive, wherever), in addition to it
being in the CI/CD variables. A variable can be overwritten or deleted by
mistake, and anyone with the Maintainer role can reveal its value in the
project settings, so treat that role accordingly. If the keystore is ever
lost, every future release needs a new signing key, and Android treats a
different key as a different app: existing installs can't upgrade in
place, everyone has to uninstall and reinstall, losing their local
instance data. The file is the only real backup, the CI/CD variable alone
isn't one.

## 4. Running a release

The release pipeline starts manually, not on tag push, since releases
deserve a conscious decision after seeing CI pass rather than
happening automatically the moment a tag lands.

**One-time setting first.** The release is started by filling in
variables on the **New pipeline** form, and GitLab.com disables that for
new projects (the default is "No one allowed", since GitLab 17.7). While it
is disabled the form shows no variables at all, only an "Inputs" box that
says there are none. In the main repository open **Settings → CI/CD →
Variables**, set **Minimum role to use pipeline variables** to
**Maintainer**, and click **Save changes** under that option. Only the
Owner role can change this setting once it is set. It does not affect the
four signing variables from section 3, which stay protected and are
unrelated to this form.

1. Push whatever commit you want to release to `main` (a tag isn't
   required to exist beforehand, the pipeline creates the GitLab release
   and its tag together).
2. On GitLab: **Build → Pipelines → New pipeline**, and pick `main`.
3. Fill in the three variables the form offers:
   - **`RELEASE_VERSION_TAG`**: e.g. `v0.2.0` or `v0.2.0-beta.1`, must
     match `vX.Y.Z` or `vX.Y.Z-suffix`, the pipeline rejects anything else
     before it does any building. Leave it empty and you get an ordinary
     CI run instead of a release.
   - **`RELEASE_NOTES`**: a short header for the release description,
     optional, defaults to a generic placeholder line.
   - **`RELEASE_PRERELEASE`**: `true` by default, since the project's
     pre-1.0. GitLab releases have no pre-release flag, so `true` adds
     "(pre-release)" to the release title and a note to the description.
4. Run it. The pipeline: validates the tag format (`release-validate`),
   then builds and signs the release APK and builds a debug APK alongside
   it (`release-build`), running `testDebugUnitTest` and
   `testReleaseUnitTest` as a safety gate before either build, verifying
   the release APK's signature with `apksigner`, uploading both APKs to
   the package registry and generating release notes with git-cliff.
   Finally `release-publish` creates the GitLab release with both APKs
   attached.

The account that starts the pipeline must be allowed to create tags
matching the version, since `release-publish` creates the tag.

## 5. Where things end up

- The GitLab release itself: **Deploy → Releases**, tagged with whatever
  version you entered.
- Two APKs attached to it: `VineOS-<version>.apk` (the one to
  actually install) and `VineOS-<version>-debug.apk` (debuggable,
  for troubleshooting only). They are stored in the project's **Package
  registry** (**Deploy → Package registry**, package `vineos`).
- Job artifacts (same two APKs, useful if you want them without
  digging through the Releases page): the `release-build` job's page,
  kept for 90 days.

## 6. If a release run fails

- **The New pipeline form shows no variables**: the project setting
  **Minimum role to use pipeline variables** is on "No one allowed", see
  the one-time setting at the start of section 4.
- **Tag format rejected**: check the `release-validate` job's log, it
  prints the exact regex it expects.
- **Keystore decode produces an empty file**: `RELEASE_KEYSTORE_BASE64`
  is missing, empty, wasn't the actual base64 text (e.g. you pasted
  a filename by mistake), or isn't available because the pipeline didn't
  run on a protected branch. Re-run the `base64 -w 0` command and check
  the output isn't empty before pasting it in.
- **Unit tests fail**: same tests as the `unit-tests` job, fix them the
  same way you would there. The release pipeline runs
  `testReleaseUnitTest` too, see the comment above
  `android.onlyEnableUnitTestForTheTestedBuildType` in `gradle.properties`
  if that one specifically is what's failing.
- **apksigner verification fails**: means signing didn't actually
  apply, almost always a wrong password in one of the four variables,
  double check each one wasn't truncated or has a stray trailing
  newline when it was pasted in.
- **Package upload fails with 401 or 403**: check **Settings → CI/CD →
  Job token permissions** and that package registry access is enabled
  for the project.
- **`release-publish` can't create the tag**: the person who started the
  pipeline lacks permission to create tags matching the version, or a
  protected tag rule blocks it.
