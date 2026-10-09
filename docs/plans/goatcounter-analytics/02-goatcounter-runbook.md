# Runbook — GoatCounter at stats.studiobeckett.ca

For the owner to run on the droplet (slice 02, Part B). Commands are for the
droplet as `rmt` unless marked **laptop** (Git Bash). Each step ends with how
you know it worked; if a check fails, stop there.

Pinned version: `deploy/GOATCOUNTER_VERSION` (v2.7.0). Config in the repo:
`deploy/goatcounter.service`, `deploy/Caddyfile`. GoatCounter commands below
were checked against the v2.7.0 source/help (`serve`, `db create site`,
`db migrate`, `version`); see `02-goatcounter-server-plan.md` for sources.

Layout on the droplet:

| What | Where |
|---|---|
| Binaries (one per version) | `/opt/goatcounter/goatcounter-vX.Y.Z` |
| Symlink the service runs | `/opt/goatcounter/goatcounter` |
| Database | `/var/lib/goatcounter/db.sqlite3` (owned by user `goatcounter`) |
| Listens on | `127.0.0.1:8081` (Caddy proxies `stats.` to it) |

---

## 0. Before you start

**0a. Working sudo.** If you don't know the `rmt` password: DigitalOcean
panel → droplet → Access → **Reset root password** (power-cycles the droplet,
~1 min downtime; new password is emailed). Then Access → **Recovery Console**,
log in as `root`, and run:

```bash
passwd rmt
```

Worked if, back as `rmt`, this prints `root` after asking for the new password:

```bash
sudo whoami
```

**0b. This slice is deployed**, so the droplet's checkout has the config:

```bash
cat ~/rmt-finder/deploy/GOATCOUNTER_VERSION
```

Worked if it prints `v2.7.0`. If "No such file", push/deploy the commit first.

## 1. Memory check (before)

```bash
free -m
```

Worked if the `available` column is roughly 200MB or more (244MB on
2026-10-09) and swap exists. Note the number for step 7.

## 2. DNS record for stats.

Namecheap → Domain List → studiobeckett.ca → Manage → Advanced DNS → Add New
Record: **A Record**, Host **stats**, Value: the same IP as the `rmtfinder`
record, TTL Automatic.

Wait until it resolves (usually minutes). **laptop:**

```bash
nslookup stats.studiobeckett.ca
```

Worked if the answer shows the droplet's IP (the same as
`nslookup rmtfinder.studiobeckett.ca`). Don't go past step 5's diff until this
works: Caddy needs it to get the certificate on reload.

## 3. Install the pinned binary

Set the version for this shell session (rerun if you reconnect):

```bash
GC=$(cat ~/rmt-finder/deploy/GOATCOUNTER_VERSION)
```

Create the service user (no login shell):

```bash
sudo useradd --system --home-dir /var/lib/goatcounter --shell /usr/sbin/nologin goatcounter
```

```bash
sudo install -d -m 755 /opt/goatcounter
```

```bash
curl -fL -o /tmp/goatcounter.gz "https://github.com/arp242/goatcounter/releases/download/$GC/goatcounter-$GC-linux-amd64.gz"
```

```bash
gunzip -f /tmp/goatcounter.gz
```

```bash
sudo install -m 755 /tmp/goatcounter "/opt/goatcounter/goatcounter-$GC"
```

```bash
sudo ln -sfn "/opt/goatcounter/goatcounter-$GC" /opt/goatcounter/goatcounter
```

```bash
/opt/goatcounter/goatcounter version
```

Worked if it prints version `v2.7.0`. Optional: `sha256sum` the binary and
note it, so a later reinstall can be compared.

## 4. Data directory, site and admin user, then the service

The service won't start without a database, so the site is created first.

```bash
sudo install -d -o goatcounter -g goatcounter -m 750 /var/lib/goatcounter
```

Create the site and your admin login. It asks for a password interactively
(keeps it out of shell history); put it in your password manager.

```bash
sudo -u goatcounter /opt/goatcounter/goatcounter db create site -createdb -db sqlite+/var/lib/goatcounter/db.sqlite3 -vhost stats.studiobeckett.ca -user.email YOUR_EMAIL
```

```bash
sudo ls -l /var/lib/goatcounter
```

Worked if `db.sqlite3` is listed, owned by `goatcounter`.

Install and start the service:

```bash
sudo cp ~/rmt-finder/deploy/goatcounter.service /etc/systemd/system/goatcounter.service
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl enable --now goatcounter
```

```bash
systemctl status goatcounter --no-pager
```

Worked if `active (running)` and the `Memory:` line shows a max of 128M. Then:

```bash
ss -tln
```

Worked if there's a line `127.0.0.1:8081` (and **not** `0.0.0.0:8081` or `*:8081`).

## 5. Caddyfile: diff, validate, copy, reload

Only once step 2 resolves. First see what would change:

```bash
diff /etc/caddy/Caddyfile ~/rmt-finder/deploy/Caddyfile
```

Expected: only the `# Source of truth` comment and the `stats.` block are
added. **If anything else differs** (someone edited the server copy), stop:
bring that change into `deploy/Caddyfile` in the repo first.

```bash
caddy validate --adapter caddyfile --config ~/rmt-finder/deploy/Caddyfile
```

Worked if it ends with `Valid configuration`. Then:

```bash
sudo cp ~/rmt-finder/deploy/Caddyfile /etc/caddy/Caddyfile
```

```bash
sudo systemctl reload caddy
```

Worked if both sites answer over HTTPS. **laptop:**

```bash
curl -sSI https://stats.studiobeckett.ca
```

Expect an `HTTP/2` status line and no certificate error (the first request
can take a few seconds while the certificate is issued). And the main site
still works:

```bash
curl -fsS https://rmtfinder.studiobeckett.ca/api/availability | head -c 200
```

If the certificate failed, look at Caddy's log on the droplet:

```bash
sudo journalctl -u caddy --since "10 min ago" --no-pager
```

GoatCounter is not reachable directly. **laptop**, should time out or be
refused (it binds to 127.0.0.1, and ufw only allows 22/80/443):

```bash
curl -m 5 http://rmtfinder.studiobeckett.ca:8081/
```

## 6. Dashboard is private

Open `https://stats.studiobeckett.ca` in your browser and log in with the
email and password from step 4. Then **Settings** → "Dashboard viewable by"
should say **Only logged in users** (the default for new sites); leave it.

Worked if an **incognito** window at the same URL shows the login page, not
stats.

## 7. Memory check (after) and reboot

```bash
free -m
```

Worked if `available` dropped by roughly GoatCounter's size (~30–60MB) and
is still well above 100MB.

```bash
systemctl show goatcounter -p MemoryMax
```

Worked if `MemoryMax=134217728` (128MB).

Then check everything comes back after a reboot:

```bash
sudo reboot
```

Reconnect after a minute:

```bash
systemctl is-active goatcounter caddy rmt-api rmt-scheduler
```

Worked if it prints `active` four times, and step 5's two laptop `curl`s
still work.

## 8. Opt out each of your own devices (`?notrack`)

Only after slice 03 (frontend tracking) is deployed. On each browser/device
you use, visit once:

`https://rmtfinder.studiobeckett.ca/?notrack`

Worked if, after browsing a city and clicking a slot on that device, no new
hit appears on the dashboard (give it ~10s; GoatCounter stores hits every
10s). `?notrack=off` turns tracking back on. Clearing site data, a new
browser, or incognito means tracked again. The full smoke test is slice 04.

## 9. Upgrading GoatCounter (and rolling back)

Read the release notes for every version between the current and new one
first (github.com/arp242/goatcounter/releases), looking for migration notes.

1. In the repo, change `deploy/GOATCOUNTER_VERSION`, commit, deploy. On the
   droplet, note the old and new versions:

   ```bash
   readlink /opt/goatcounter/goatcounter
   ```

   ```bash
   NEW=$(cat ~/rmt-finder/deploy/GOATCOUNTER_VERSION)
   ```

2. Install the new binary **alongside** the old one: step 3's `curl`,
   `gunzip` and `install` commands with `$NEW` in place of `$GC` (don't run
   the `ln` yet).

   ```bash
   "/opt/goatcounter/goatcounter-$NEW" version
   ```

3. Stop, then back up the whole data directory. Copying while stopped means
   SQLite isn't mid-write. Replace `vOLD` with the old version:

   ```bash
   sudo systemctl stop goatcounter
   ```

   ```bash
   sudo cp -a /var/lib/goatcounter /var/lib/goatcounter.bak-vOLD
   ```

4. Run migrations explicitly with the **new** binary. See what's pending
   (exits 1 if anything is):

   ```bash
   sudo -u goatcounter "/opt/goatcounter/goatcounter-$NEW" db migrate -db sqlite+/var/lib/goatcounter/db.sqlite3 pending
   ```

   ```bash
   sudo -u goatcounter "/opt/goatcounter/goatcounter-$NEW" db migrate -db sqlite+/var/lib/goatcounter/db.sqlite3 all
   ```

   Worked if running `pending` again exits 0 and lists nothing.

5. Switch the symlink and start:

   ```bash
   sudo ln -sfn "/opt/goatcounter/goatcounter-$NEW" /opt/goatcounter/goatcounter
   ```

   ```bash
   sudo systemctl start goatcounter
   ```

6. Smoke test: `systemctl status goatcounter --no-pager` is active with no
   "pending migrations" warning in its log lines, the dashboard loads and
   shows past data, and a new incognito visit to RMT Finder appears.

**Rollback** (new version misbehaves). Stop it, point the symlink back:

```bash
sudo systemctl stop goatcounter
```

```bash
sudo ln -sfn /opt/goatcounter/goatcounter-vOLD /opt/goatcounter/goatcounter
```

If step 4 ran any migrations, the old binary may not understand the new
schema, so also restore the backup (hits since the upgrade are lost). Move
the upgraded data aside rather than deleting it:

```bash
sudo mv /var/lib/goatcounter /var/lib/goatcounter.failed-$NEW
```

```bash
sudo cp -a /var/lib/goatcounter.bak-vOLD /var/lib/goatcounter
```

```bash
sudo systemctl start goatcounter
```

Then revert `deploy/GOATCOUNTER_VERSION` in the repo. Delete old binaries and
backups only once the new version has run fine for a while.

## 10. Rule: config changes go through the repo

Never edit `/etc/caddy/Caddyfile` or `/etc/systemd/system/goatcounter.service`
only on the server. Change `deploy/Caddyfile` / `deploy/goatcounter.service`
in the repo, run `pytest` (the config checks catch port and listen-address
drift), commit, deploy, then copy with step 5 (Caddy) or step 4's `cp` +
`daemon-reload` + `sudo systemctl restart goatcounter` (unit). The diff in
step 5 is there to catch a server-only edit before it gets overwritten.

## 11. What looks wrong

Check these when numbers jump or look odd:

- **A spike from one referrer** you don't recognize: likely referrer spam or
  a bot. Look at its pages; real visitors view a city and sometimes click.
- **A spike from one screen size** or one browser version: likely one bot
  or a scripted client.
- **Book clicks without matching city views** (e.g. `book/` hits on a day
  with few or no `/victoria` or `/langford` views): either a bot hitting the
  count endpoint directly or broken page-view tracking. Every real Book
  click follows a city view.
- **Views of a city drop to zero** while the site works: check the script
  still loads (browser devtools, Network tab, `count.js`) and that you're
  not looking from an opted-out browser.
- **Lots of `/unknown-city`**: a broken shared link; its title shows the bad
  value.

GoatCounter keeps detected bots out of the main stats already; these are
for what slips through.

## 12. View-only secret link (e.g. for a job application)

Create: dashboard → **Settings** → "Dashboard viewable by" → **Logged in
users or with secret token** → set "Secret token" (8–40 letters/digits;
use a random one) → Save. Copy the **Secret access URL** shown there.

Worked if that URL opens the dashboard in an incognito window.

Revoke: set "Dashboard viewable by" back to **Only logged in users** → Save
(or change the token to kill only the old link). Worked if the old URL now
shows the login page in incognito.
