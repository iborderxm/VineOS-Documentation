# Hosting your own VineOS ROM store

VineOS fetches its ROM list from a single JSON file (the "manifest"),
then downloads and verifies individual `.vrom` files from URLs listed
in that manifest. There's no special server software involved, any
plain static file host works. This guide covers a Debian box running
nginx, since that's a common, solid default, but any static HTTP(S)
server works identically.

## 1. The two manifest.json files, and why there are two

This trips people up, so it's worth being explicit up front:

- **The store manifest** (`manifest.json`, served at
  `/roms/manifest.json`) lists every available ROM and is what the app
  fetches over the network. This is what this guide is about.
- **The `.vrom` internal manifest** is a *different* `manifest.json`,
  bundled *inside* each `.vrom` zip file, describing that one ROM's
  own contents. It's what powers local-file import (Home → ROMs →
  import icon) when someone picks a `.vrom` off their device with no
  network involved. See [BUILDING.md](BUILDING.md)'s "ROM image format
  (.vrom)" section for that one's exact layout, you'll need it when
  you package a ROM in the first place.

Both need to exist and agree with each other (same `androidVersion`,
`apiLevel`, etc.), but they're separate files serving separate paths
through the app.

## 2. Server layout

Any layout works as long as the manifest's URLs resolve to the right
files, but a simple one:

```text
/var/www/vineos-roms/
└── roms/
    ├── manifest.json
    ├── android-7.1.2-arm64.vrom
    ├── android-7.1.2-arm64.vrom.sha256
    └── ...
```

The manifest sits next to the ROMs because the app and the website both
request `/roms/manifest.json`. Older versions of this guide kept it one
level up, at `/var/www/vineos-roms/manifest.json`. The nginx config in
section 5.2 still serves that location as a fallback, but new setups
should use the layout above.

The `.sha256` sidecar files aren't required by the app, they're just
handy for you to `sha256sum -c` against before publishing.

## 3. The store manifest format

This is parsed directly into the app's `ROMManifest`/`ROMImage` Kotlin
classes (`app/src/main/java/com/hexadecinull/vineos/data/models/Models.kt`),
field-for-field, no renaming:

```json
{
  "version": 1,
  "roms": [
    {
      "id": "android-7.1.2-arm64",
      "displayName": "Android 7.1.2 Nougat",
      "androidVersion": "7.1.2",
      "apiLevel": 25,
      "description": "Stock AOSP 7.1.2, arm64-v8a with 32-bit compat",
      "downloadUrl": "https://vineos.hexadecinull.dpdns.org/roms/android-7.1.2-arm64.vrom",
      "sha256": "<sha256 of the WHOLE .vrom file, see section 4>",
      "sizeBytes": 734003200,
      "minHostApiLevel": 26,
      "supportedAbis": ["arm64-v8a", "armeabi-v7a"],
      "has32BitSupport": true,
      "releaseDate": "2026-01-15"
    }
  ]
}
```

Notes on specific fields:

- `id`: anything unique and URL-safe. The app also generates its own
  `local-<uuid>` IDs for locally-imported ROMs, so avoid the `local-`
  prefix here to keep the two namespaces visibly distinct.
- `downloadUrl`: must be a full, absolute URL (it's passed straight
  to OkHttp's request builder). HTTPS strongly recommended, plain HTTP
  works but the ROM (an Android system image) travels in the clear.
- `sha256`: **the hash of the entire `.vrom` file as downloaded**,
  not the per-component hashes from the `.vrom`'s own internal
  manifest. This is what `ROMRepository.verifyFile()` actually checks
  after downloading; get this one wrong and every download will fail
  verification and get deleted. Section 4 covers the exact command.
- `minHostApiLevel`: optional, defaults to 26 if omitted.
- `supportedAbis`: the ABI(s) the ROM's `system.img` was built for,
  e.g. `["arm64-v8a"]`. This drives the native/QEMU badge shown in the
  ROMs list (see `AbiCompat.romRunMode`), and armeabi-v7a can go here
  too if the image genuinely supports both.

Don't include `isLocal`, `localPath`, `isDownloaded`, or
`downloadState`, those are client-side-only fields the app fills in
itself; anything you put there in the manifest gets ignored and
overwritten on the client anyway.

## 4. Computing the sha256 the app actually checks

```bash
sha256sum android-7.1.2-arm64.vrom
```

Use that exact value (lowercase hex, the app compares
case-insensitively but lowercase is conventional) as the `sha256`
field for that ROM. Recompute and update the manifest every time you
replace a `.vrom` file, a stale hash here means every install fails
with a "SHA-256 verification failed" error and the partial download
gets deleted.

## 5. Hosting: website on GitLab Pages, ROMs on your own server

The website is deployed to GitLab Pages and the ROM store runs on your own
box. Both answer on `vineos.hexadecinull.dpdns.org`, and the DNS record for
that name stays pointed at GitLab Pages. Only the `/roms` path goes through
a Cloudflare Tunnel:

```text
vineos.hexadecinull.dpdns.org/*         DNS record, then GitLab Pages (the website)
vineos.hexadecinull.dpdns.org/roms/*    Cloudflare Worker, then Cloudflare Tunnel, then nginx on your box
roms-origin.hexadecinull.dpdns.org      Tunnel hostname, only ever called by the Worker
```

A tunnel route on `vineos.hexadecinull.dpdns.org` with the path `/roms`
cannot work on its own. Cloudflare creates a tunnel route by pointing the
hostname's DNS record at the tunnel, which would replace the record that
points at GitLab Pages, and a hostname can only have one DNS target. The
setting that could split one hostname by path without code (an Origin Rule
with a DNS record override) is Enterprise only, so a small Worker does that
split instead. The app and the website keep using
`https://vineos.hexadecinull.dpdns.org/roms/manifest.json`, so neither needs
to change. If your box is offline the website stays up and the ROM list
shows its "not live yet" message.

Do the steps in order, since each one can be tested before the next.

### 5.1 Put the ROM files in place

```bash
sudo mkdir -p /var/www/vineos-roms/roms

# .vrom files plus a manifest.json (run generate_manifest.py from a clone of the main VineOS repo)
sudo cp path/to/*.vrom /var/www/vineos-roms/roms/
python3 scripts/generate_manifest.py \
    --roms-dir /var/www/vineos-roms/roms \
    --base-url https://vineos.hexadecinull.dpdns.org/roms \
    --output /var/www/vineos-roms/roms/manifest.json

sudo chown -R www-data:www-data /var/www/vineos-roms
```

### 5.2 nginx config

Install nginx if it's not already there (`sudo apt install nginx`), then
save this as `/etc/nginx/sites-available/vineos`, adjusting paths if you
used different ones above:

```nginx
server {
    listen 80;
    server_name roms-origin.hexadecinull.dpdns.org;

    root /var/www/vineos-roms;

    location = /roms/manifest.json {
        try_files /roms/manifest.json /manifest.json =404;
        add_header Cache-Control "no-cache";
    }

    location /roms/ {
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
        return 404;
    }
}
```

Then enable it and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/vineos /etc/nginx/sites-enabled/vineos
sudo nginx -t && sudo systemctl reload nginx
```

This server only serves `/roms/`, the website itself is not on this box.
It listens on plain port 80 with no TLS block because the tunnel in 5.3
reaches it over localhost and Cloudflare handles public TLS. Directory
listing is off, so `/roms/` itself answers 403, which is expected. Range
requests work out of the box, which is what lets interrupted ROM downloads
resume.

Check it locally, this should print the manifest:

```bash
curl -s -H 'Host: roms-origin.hexadecinull.dpdns.org' http://localhost/roms/manifest.json
```

`no-cache` on the manifest means clients always revalidate before using a
cached copy, useful since you'll be editing it whenever you add a ROM. The
long `max-age` on `/roms/` is safe specifically because `.vrom` filenames
should be treated as immutable. If you update a ROM, give the new file a
new name (e.g. bump a version suffix) rather than overwriting the old one
in place, so any CDN or browser cache in front of it can't serve stale
bytes under an unchanged URL.

### 5.3 Cloudflare Tunnel

No port forwarding on your router and no certificate on the origin box,
`cloudflared` makes an outbound-only connection to Cloudflare, so nothing
needs to accept inbound connections from the internet directly. The tunnel
route here is the `/roms` path: only requests under `/roms/` are passed to
nginx, everything else gets a 404.

```bash
# on the Debian box
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install cloudflared

cloudflared tunnel login
cloudflared tunnel create vineos
cloudflared tunnel route dns vineos roms-origin.hexadecinull.dpdns.org
```

That last command creates a proxied CNAME for `roms-origin` only. It does
not touch the `vineos` record. Then write the config:

```bash
sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml << 'EOF'
tunnel: vineos
credentials-file: /root/.cloudflared/<TUNNEL-ID>.json
ingress:
  - hostname: roms-origin.hexadecinull.dpdns.org
    path: ^/roms/
    service: http://localhost:80
  - service: http_status:404
EOF

sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

Swap `<TUNNEL-ID>` for the actual ID `cloudflared tunnel create` printed, or
run `cloudflared tunnel list` to look it up again.

If you already have this tunnel from an earlier setup, keep the first two
lines of `config.yml` and replace only the `ingress` section:

```bash
sudo cp /etc/cloudflared/config.yml /etc/cloudflared/config.yml.bak
sudo sed -i '/^ingress:/,$d' /etc/cloudflared/config.yml
sudo tee -a /etc/cloudflared/config.yml << 'EOF'
ingress:
  - hostname: roms-origin.hexadecinull.dpdns.org
    path: ^/roms/
    service: http://localhost:80
  - service: http_status:404
EOF
cloudflared tunnel route dns vineos roms-origin.hexadecinull.dpdns.org
sudo systemctl restart cloudflared
```

A tunnel managed from the Cloudflare dashboard has no `config.yml` on the
box, so skip the commands above and add the route there instead. Open
Networking, Tunnels, your tunnel, Routes, Add route, Published application
(older dashboards: Zero Trust, Networks, Tunnels, your tunnel, Public
Hostname, Add a public hostname). Enter the subdomain `roms-origin` with the
domain `hexadecinull.dpdns.org`, the service `http://localhost:80`, and if the
form has a Path field, `^/roms/`. If it has none, leave it empty, nginx
already answers 404 for everything outside `/roms/`. Check DNS, Records
afterwards, Cloudflare normally creates the proxied `roms-origin` record
itself. The running `cloudflared` picks the route up without a restart.

Test it before moving on, this should print the manifest:

```bash
curl -s https://roms-origin.hexadecinull.dpdns.org/roms/manifest.json
```

### 5.4 The website on GitLab Pages

1. In the VineOS-Website project, open Deploy, Pages, New Domain, and add
   `vineos.hexadecinull.dpdns.org`. GitLab then shows the DNS records it
   wants.
2. In the Cloudflare DNS settings of the `hexadecinull.dpdns.org` zone,
   create exactly those records. The `vineos` record must be **Proxied**
   (orange cloud), otherwise the Worker in 5.5 never sees the request. The
   verification TXT record stays as it is.
3. Under SSL/TLS, Overview, set the encryption mode to **Full**. Flexible
   mode loops forever against GitLab's HTTPS redirect.

If the certificate for the domain stays pending in GitLab, switch the
`vineos` record to DNS only until GitLab shows the domain as verified with
a certificate, then switch the proxy back on.

### 5.5 The Worker

The Worker lives in the VineOS-Website repository, in `worker/`. It does
one thing: for `/roms/*` it fetches the same path from
`roms-origin.hexadecinull.dpdns.org` and streams the answer back, including
range requests. Anything that is not `GET` or `HEAD` is refused.

```bash
git clone https://gitlab.com/Hexadecinull/VineOS/VineOS-Website.git
cd VineOS-Website/worker
npx wrangler login
npx wrangler deploy
```

`wrangler.toml` already contains the route `vineos.hexadecinull.dpdns.org/roms/*`
for the `hexadecinull.dpdns.org` zone and the `ORIGIN` variable. To do it
from the dashboard instead, create a Worker named `vineos-roms-proxy`
under Workers & Pages, paste in `worker.js`, add a text variable `ORIGIN`
with the value `https://roms-origin.hexadecinull.dpdns.org`, then add the
route `vineos.hexadecinull.dpdns.org/roms/*` under Settings, Domains &
Routes. The free Workers plan is plenty for this.

The Worker answers a plain-text `Not found` (404) for any path outside
`/roms/`, including the root of its own `workers.dev` address, so that
answer in the dashboard preview is expected and means the Worker is
running. To test it before adding the route, open the `workers.dev` address
Cloudflare shows on the Worker's page with `/roms/manifest.json` added at
the end. That should print the manifest, and it checks the Worker, the
tunnel and nginx without involving the `vineos` DNS record at all.

### 5.6 Without Cloudflare Tunnel

The Worker only needs an HTTPS URL to forward to, set as `ORIGIN`. If
your box has a public IP and forwarded ports 80 and 443, skip 5.3, point a
DNS record for `roms-origin.hexadecinull.dpdns.org` at it, and get a
certificate with certbot:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d roms-origin.hexadecinull.dpdns.org
```

certbot rewrites the nginx config in place to add the `443 ssl` block and
a `80 to 443` redirect, you don't need to hand-write that part.

## 6. Where the app points

`ROMRepository.kt` already hardcodes your domain:

```kotlin
private const val MANIFEST_URL = "https://vineos.hexadecinull.dpdns.org/roms/manifest.json"
```

Nothing to change here unless the domain itself changes later, in
which case that's the one line to update.

## 7. A helper script for generating the manifest

`scripts/generate_manifest.py` (in the main VineOS repository) scans a
directory of `.vrom` files, reads each one's embedded internal
manifest for the descriptive fields, computes the whole-file sha256
the app actually verifies, and writes out a ready-to-serve
`manifest.json`. Usage:

```bash
python3 scripts/generate_manifest.py \
    --roms-dir /var/www/vineos-roms/roms \
    --base-url https://vineos.hexadecinull.dpdns.org/roms \
    --output /var/www/vineos-roms/roms/manifest.json
```

Re-run it any time you add, remove, or replace a `.vrom` file, it
regenerates the whole manifest from what's actually on disk rather
than hand-editing JSON, so the sha256 can never drift out of sync with
the real file.

## 8. Testing before you point real users at it

```bash
curl -s https://vineos.hexadecinull.dpdns.org/roms/manifest.json | python3 -m json.tool
```

confirms the manifest itself is valid JSON and reachable through the whole
chain. If it isn't, what you see tells you where to look:

| What `/roms/manifest.json` returns | Likely cause |
|---|---|
| A GitLab Pages 404 page | The Worker route is missing, or the `vineos` DNS record is DNS only |
| A Cloudflare 502, 530 or 1033 error | The tunnel is down, check `sudo systemctl status cloudflared` on the box |
| A Cloudflare 1016 error | The `roms-origin` DNS record or the tunnel route for it is missing |
| A Cloudflare 1101 error | The Worker has no `ORIGIN` variable, add it under the Worker's Settings, Variables and Secrets |
| A plain-text `Not found` | The path does not start with `/roms/`, expected for the root of the Worker's `workers.dev` address |
| A plain nginx 404 page | `manifest.json` is missing from `/var/www/vineos-roms/roms/` |
| A 403 on `/roms/` | Expected, directory listing is off |

Beyond that,
build a debug APK pointed at your `MANIFEST_URL`, and check the ROMs
tab actually lists what you expect and that a full download completes
and passes verification, that's the real end-to-end test.

## 9. Certificate pinning

`NetworkModule.kt` has a `CertificatePinner` slot for the ROM store
host, currently disabled with placeholder values (pinning with a wrong
value breaks every download outright, so it stays off until real pins
are in).

**Since you're using Cloudflare Tunnel, read this first:** with the
domain proxied through Cloudflare (the orange-cloud `vineos` DNS record),
the TLS connection the app
actually makes terminates at **Cloudflare's edge**, not your origin
box. Running the command below against `vineos.hexadecinull.dpdns.org`
correctly captures whatever the app really sees, that part still
works, but it means you're pinning Cloudflare's certificate, not one
you personally control the renewal of. Cloudflare rotates their edge
certs on their own schedule, out of your control, and that cert may be
shared across many unrelated Cloudflare customers on the same shared
pool, so it's less predictable than pinning your own certbot-managed
cert would be. Given that, a reasonable call here is to **leave
pinning off** and rely on the sha256 file-integrity check (section 4)
plus Cloudflare's own edge security instead, revisit this if you ever
move off Cloudflare Tunnel to a setup where you control the origin
cert's lifecycle directly. If you do want it anyway, pin Cloudflare's
root/intermediate CA rather than the leaf, root CAs change on the
order of years, not Cloudflare's routine leaf rotation.

Generate the primary pin:

```bash
openssl s_client -connect vineos.hexadecinull.dpdns.org:443 -servername vineos.hexadecinull.dpdns.org </dev/null 2>/dev/null \
  | openssl x509 -pubkey -noout \
  | openssl pkey -pubin -outform der \
  | openssl dgst -sha256 -binary \
  | openssl enc -base64
```

That gives you one pin (the current leaf certificate's public key
hash). Pin a **second, backup** value too, so a routine cert renewal
doesn't lock the app out before you can ship an update, either:

- run the same command against your certbot renewal's *next* cert if
  you can get at it ahead of time (only applicable without
  Cloudflare Tunnel, see 5.6), or
- more simply, pin the intermediate or root certificate instead of
  (or alongside) the leaf, since those change far less often, whether
  it's Let's Encrypt's ~90-day leaf rotation or Cloudflare's own edge
  cert rotation. `openssl s_client -showcerts` against the same host
  shows the full chain; run the same pubkey/dgst pipeline against the
  intermediate or root cert in that output instead of the leaf.

Put both values (prefixed `sha256/`, matching what the commands above
already output) into `ROM_STORE_PIN_PRIMARY` and
`ROM_STORE_PIN_BACKUP` in `NetworkModule.kt`. Pinning only activates
once neither still contains the placeholder text, so a half-finished
edit fails safe rather than silently breaking downloads.
