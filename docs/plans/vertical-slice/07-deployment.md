# Deployment (v1: VPS + systemd + Caddy)

**Type:** HITL

## Parent PRD

`docs/prd/vertical-slice.md`

## Decisions (resolved 2026-07-14)

- **Goal:** a living pipeline. The scraper runs 24/7 in production; the
  accumulating run history is the portfolio artifact.
- **Scraping from a datacenter IP is acceptable:** janeapp.com serves
  booking pages directly from its Rails app (no Cloudflare/bot-management
  edge) and its robots.txt is `User-agent: * / Allow: /` (only GPTBot is
  disallowed). A 1–2s courtesy sleep between clinics is added anyway.
- **Host:** smallest VPS (~$5 USD/mo — Hetzner US-West or DigitalOcean),
  treated as a time-boxed job-search expense. The Pi 4 stays in the
  backlog as a post-hire migration slice.
- **URL:** `rmtfinder.studiobeckett.ca` — one A record on the existing
  Namecheap domain. HTTPS via Caddy's automatic Let's Encrypt.
- **v1 is deliberately Docker-free:** venv + two systemd services.
  Containerizing is its own later slice, done after bare-metal works so
  the Docker commit has a before/after story.
- **Same-origin serving:** FastAPI serves the built frontend via a
  StaticFiles mount, so the browser fetches `/api/availability` from the
  same origin — CORS and `VITE_API_BASE_URL` plumbing become no-ops in
  prod.

## Later slices (not this one)

Nightly DB backup off-box → Docker Compose → static-JSON snapshot
publishing (serving decoupled from ingestion) → CI/CD → Pi migration.
Monetization (featured listings) is parked; its trigger is the first
clinic willing to pay, and it reopens scraping posture, not just naming.

---

## Runbook

Steps marked **[Claude]** are code changes made in this repo (user
verifies and commits per the usual workflow). Steps marked **[you]**
happen in a browser or SSH session.

### Phase 0 — prerequisites

1. **[you]** Verify and commit slice 05 (still uncommitted). Deployment
   deploys committed `main`.

### Phase 1 — code changes

2. **[Claude]** Courtesy sleep: 1–2s between clinics in
   `backend/scraper/runner.py` (injectable for tests).
3. **[Claude]** Same-origin serving: mount the frontend build in
   `backend/api.py` — serve `frontend/dist/` at `/` with an SPA-style
   fallback to `index.html`, keeping `/api/*` routes first. Path anchored
   to the repo root like `config.py` does, and tolerant of `dist/` being
   absent (dev machines without a build).
4. **[Claude]** Relative API base: add `frontend/.env.production` with
   `VITE_API_BASE_URL=` (empty ⇒ same-origin fetches in prod builds; dev
   keeps the localhost default).
5. **[you]** Run the tests, eyeball the diff, commit.
6. **[you]** Build the frontend on the PC: `npm run build` in
   `frontend/` (Node is never installed on the server; `dist/` is copied
   up in Phase 4).

### Phase 2 — provision the VPS

7. **[you]** Create an account at Hetzner (or DigitalOcean). Create the
   smallest instance — Ubuntu 24.04 LTS, US-West/SFO region (closest to
   Victoria; on DO pick **SFO3**, not legacy SFO1). Public **IPv4**
   required (the A record points at it); enable IPv6 too if it's free.
   Add your SSH public key during creation (generate one first if
   needed: `ssh-keygen -t ed25519`) — adding a key at creation also
   disables SSH password auth. Note the server's public IPv4.
8. **[you]** First login and basic hardening:

   ```bash
   ssh root@<SERVER_IP>
   adduser rmt                 # app + login user
   usermod -aG sudo rmt
   rsync --archive --chown=rmt:rmt ~/.ssh /home/rmt   # copy the SSH key
   ufw allow OpenSSH
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   apt update && apt upgrade -y
   apt install -y python3-venv git unattended-upgrades
   ```

   From here on, work as `rmt`: `ssh rmt@<SERVER_IP>`.

   **Once `ssh rmt@<SERVER_IP>` is confirmed working** (not before —
   lockout risk), disable root SSH login:

   ```bash
   echo 'PermitRootLogin no' | sudo tee /etc/ssh/sshd_config.d/99-no-root.conf
   sudo systemctl restart ssh
   ```

   Security posture, for the record: key-only SSH (password auth is
   disabled automatically when the instance is created with an SSH key —
   verify with `sudo sshd -T | grep passwordauthentication`), no root
   login, unattended security patches, firewall allows only 22/80/443,
   and uvicorn binds to 127.0.0.1 so the only internet-facing processes
   are SSH and Caddy. SSH stays on port 22 — moving it is obscurity, not
   security, once password auth is off. `fail2ban` is optional
   belt-and-suspenders if SSH log noise bothers you.

### Phase 3 — DNS

9. **[you]** Namecheap → Domain List → studiobeckett.ca → Manage →
   Advanced DNS → Add New Record:
   - Type: **A Record**, Host: **rmtfinder**, Value: **<SERVER_IP>**, TTL:
     Automatic.

   Propagation is usually minutes. Check with
   `nslookup rmtfinder.studiobeckett.ca` — do this before Phase 5, since
   Caddy needs the DNS record in place to obtain its certificate.

### Phase 4 — the app on the server

10. **[you]** As `rmt` on the server:

    ```bash
    git clone https://github.com/<user>/rmt-finder.git ~/rmt-finder
    cd ~/rmt-finder
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
    ```

11. **[you]** Copy the frontend build up from the PC (PowerShell):

    ```powershell
    scp -r frontend/dist rmt@<SERVER_IP>:rmt-finder/frontend/
    ```

12. **[you]** Smoke-test before wiring anything permanent:

    ```bash
    cd ~/rmt-finder/backend
    ../venv/bin/python main.py          # one scrape run; watch it succeed
    ../venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000
    # in a second SSH session:
    curl localhost:8000/api/availability | head -c 400
    ```

### Phase 5 — systemd services

13. **[you]** `/etc/systemd/system/rmt-api.service`:

    ```ini
    [Unit]
    Description=RMT Finder API
    After=network-online.target

    [Service]
    User=rmt
    WorkingDirectory=/home/rmt/rmt-finder/backend
    ExecStart=/home/rmt/rmt-finder/venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    ```

14. **[you]** `/etc/systemd/system/rmt-scheduler.service` — identical
    except `Description=RMT Finder scraper scheduler` and
    `ExecStart=/home/rmt/rmt-finder/venv/bin/python scheduler.py`.

15. **[you]** Enable both (enable ⇒ they also start on reboot):

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now rmt-api rmt-scheduler
    systemctl status rmt-api rmt-scheduler
    journalctl -u rmt-scheduler -f     # watch the first scheduled scrape
    ```

### Phase 6 — Caddy (HTTPS)

16. **[you]** Install Caddy (official apt repo, from
    caddyserver.com/docs/install):

    ```bash
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update && sudo apt install -y caddy
    ```

17. **[you]** Replace `/etc/caddy/Caddyfile` with:

    ```
    rmtfinder.studiobeckett.ca {
        reverse_proxy 127.0.0.1:8000
    }
    ```

    Then `sudo systemctl reload caddy`. Caddy fetches and renews the TLS
    certificate itself.

### Phase 7 — acceptance

- `https://rmtfinder.studiobeckett.ca` loads with a valid certificate and shows
  real slots.
- The scheduler is writing: `runs` table gains a row every 15 minutes
  (`journalctl -u rmt-scheduler` or the site's last-updated line).
- Survives reboot: `sudo reboot`, wait a minute, site is back and a new
  scrape lands within the interval.
- After ~24h: failure counts in the run history are the same shape as
  local runs (confirms no datacenter-IP throttling).

## Acceptance criteria

Phase 7's four checks, verified by the user.
