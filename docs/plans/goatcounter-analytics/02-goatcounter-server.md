# GoatCounter server: config in the repo, then owner setup

**Type:** HITL

## Parent PRD

`docs/prd/goatcounter-analytics.md`

## What to build

A self-hosted GoatCounter at `stats.studiobeckett.ca`, with all of its config
versioned in the repo and a runbook the owner executes on the droplet. Claude
cannot SSH to the droplet, so this slice has two parts. See PRD
"Implementation Decisions → Server", "Deploy-config tests" and "Runbook".

**Part A — agent, in the repo:**

- A systemd unit for GoatCounter that listens on `127.0.0.1` only, on a port
  distinct from the API's. It sets `MemoryMax=128M`, restarts on failure, and
  keeps its SQLite database in a dedicated data directory.
- The **full** Caddyfile in the repo: the existing `rmtfinder.` block,
  unchanged, plus a `stats.` block reverse-proxying to GoatCounter.
- The pinned GoatCounter version, recorded in one place.
- pytest checks, following the existing deploy-script test pattern:
  - the unit listens on `127.0.0.1` only and sets a memory cap
  - Caddy's `stats.` port matches the unit's port
  - the `rmtfinder.` block still proxies to the API port
- A runbook in `docs/plans/`. Verify the exact GoatCounter CLI commands
  (serve flags, site/user creation, migrations) against GoatCounter's
  documentation for the pinned version. Don't assume them. Cover:
  1. memory check (`free -m`)
  2. DNS A record for `stats.` at Namecheap, and waiting until it resolves
  3. installing the versioned binary plus a symlink
  4. data directory and service
  5. diff the live Caddyfile against the repo, then `caddy validate`, copy
     and reload
  6. creating the site and admin user, with the dashboard private
  7. post-install memory check
  8. one-time `?notrack` on each owner device
  9. upgrade procedure (back up the DB file, install the new binary
     alongside, stop, run migrations explicitly, switch the symlink, start,
     smoke test), plus rollback (point the symlink back)
  10. the rule "change Caddy config in the repo, then copy, never edit only
      on the server"
  11. the "what looks wrong" checklist (spike from one referrer or screen
      size; Book clicks without matching city views)
  12. creating and revoking a view-only secret link
- Commands in the runbook use Git Bash/Linux syntax, one per code block.

**Part B — owner, on the droplet (HITL):** execute the runbook up to a
working, private dashboard at `https://stats.studiobeckett.ca`.

## Acceptance criteria

- [ ] Unit file, full Caddyfile and pinned version are in the repo
- [ ] pytest config checks exist and pass; they fail if the Caddy and unit
      ports drift apart or the listen address leaves `127.0.0.1`
- [ ] Runbook's GoatCounter commands are checked against the docs for the
      pinned version
- [ ] Runbook covers every step listed above, in an order that works
      (DNS resolves before the Caddy reload)
- [ ] **Owner:** `https://stats.studiobeckett.ca` loads with a valid
      certificate and requires login
- [ ] **Owner:** `rmtfinder.studiobeckett.ca` still works after the Caddy reload
- [ ] **Owner:** GoatCounter is not reachable directly on its port from outside
- [ ] **Owner:** memory check after install shows healthy headroom; the
      service shows its memory cap
- [ ] **Owner:** the service survives `sudo reboot`

## Blocked by

None - can start immediately

## User stories addressed

- User story 23
- User story 24
- User story 25
- User story 26
- User story 27
- User story 28
- User story 29
- User story 30
- User story 31
- User story 32
- User story 33
- User story 34
- User story 35
- User story 36
- User story 45
