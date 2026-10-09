# Implementation plan — Slice 02: GoatCounter server

Issue: `docs/plans/goatcounter-analytics/02-goatcounter-server.md`
Status: Part A built 2026-10-09, awaiting the user's manual check before
commit. Part B (droplet) is the owner's, via the runbook.

## Decisions

- **Version: GoatCounter v2.7.0** (2025-12-15), the latest release. Static
  `linux-amd64` binary (droplet is `x86_64`, Ubuntu 24.04). Recorded only in
  `deploy/GOATCOUNTER_VERSION`; the unit runs a symlink, so it never names
  a version.
- **Port 8081** on `127.0.0.1`: free on the droplet (`ss -tln` 2026-10-09
  shows 22, 53, 80, 443, 2019, 8000), distinct from the API's 8000.
- **`-tls http`**: the documented "no TLS" value in v2.7.0 (the help's proxy
  example says `-tls none`, which is not in the documented value list).
  Caddy terminates TLS and sends `X-Forwarded-For`/`X-Forwarded-Proto` by
  default, which GoatCounter's proxy docs expect.
- **No `-automigrate`**: v2.7.0 `serve` only warns on pending migrations and
  keeps running, so upgrades run `db migrate` explicitly.
- **Dedicated `goatcounter` system user**, DB at
  `/var/lib/goatcounter/db.sqlite3`, binaries in `/opt/goatcounter/`.
- **Live Caddyfile** (pasted 2026-10-09) goes in verbatim as `deploy/Caddyfile`
  with one header comment and the new `stats.` block appended.
- The API port the `rmtfinder.` block must match is taken from
  `deploy/deploy.sh`'s health check (the API unit isn't in the repo).

## Steps (test-first, one at a time)

`backend/tests/test_deploy_config.py`, in the `test_deploy_script.py` style
(read files, assert on text):

1. Unit listens on `127.0.0.1` only (`-listen` present, host is
   `127.0.0.1`). → `deploy/goatcounter.service`.
2. Unit sets `MemoryMax` (and not `infinity`). → add to the unit.
3. Caddy's `stats.` block proxies to the unit's port. → `deploy/Caddyfile`.
4. Caddy's `rmtfinder.` block proxies to `127.0.0.1:<deploy.sh port>`.
   → live block copied in.
5. GoatCounter's port differs from the API's.
6. `deploy/GOATCOUNTER_VERSION` is a single `vX.Y.Z` line.

Then check that each test fails when its config drifts (a mutated copy), and
write `docs/plans/goatcounter-analytics/02-goatcounter-runbook.md`.

## Sources checked (v2.7.0)

- Release + assets: github.com/arp242/goatcounter/releases/tag/v2.7.0
- `serve` flags: `cmd/goatcounter/serve.go` at tag `v2.7.0`
- Proxy setup (`help listen`): `cmd/goatcounter/help.go` at `v2.7.0`
- `db create site`, `db migrate`: `cmd/goatcounter/db.go` at `v2.7.0`
- Pending-migration behaviour: `cmd/goatcounter/main.go` (`connectDB`)
- Dashboard visibility (default `private`): `settings.go`,
  `tpl/settings_main.gohtml` at `v2.7.0`
