# CI/CD (deploy on push to main)

**Type:** HITL

## Parent PRD

`docs/prd/vertical-slice.md`

## Decisions (resolved 2026-07-15)

- **Push-based deploy from GitHub Actions** (over server-side polling or a
  webhook listener): a `deploy` job in the existing CI workflow runs on
  every push to `main`, gated on the backend and frontend test jobs
  passing. Chosen because the whole pipeline is visible in one workflow
  file and it adds no new internet-facing service to the droplet.
- **The frontend is built on the CI runner** and shipped as the job
  artifact that was tested. This retires the "build on the PC, scp
  `dist/` up" step from slice 07; Node still never touches the server.
- **The server stays a plain git checkout.** Deploy is `git pull
  --ff-only` + `pip install` + restart. The repo is public, so https
  pulls need no credentials. The SQLite DB lives in the gitignored
  `data/`, out of git's reach.
- **Restarting `rmt-scheduler` mid-scrape is accepted:** a killed run
  shows up as incomplete and the next 15-minute tick recovers. No drain
  logic.
- **Host keys are pinned** in `deploy/known_hosts` (host public keys are
  public by design) so the runner never trusts-on-first-use. The only
  secret is the deploy SSH private key.

## What runs where

- `.github/workflows/ci.yml` — `deploy` job: downloads the tested
  `frontend/dist` artifact, rsyncs it to the server, pipes
  `deploy/deploy.sh` over SSH, then curls the public URL.
- `deploy/deploy.sh` — runs on the droplet as `rmt`: pull, pip install,
  restart both services, wait for the API to answer.

---

## Runbook (one-time setup)

Steps marked **[you]** happen on your PC (Git Bash) or in the GitHub UI.

### Phase 1 — deploy key

1. **[you]** Generate a dedicated keypair (no passphrase; it lives only
   in GitHub secrets):

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/rmt_deploy -C "github-actions-deploy" -N ""
   ```

2. **[you]** Install the public half on the server:

   ```bash
   ssh rmt@rmtfinder.studiobeckett.ca 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/rmt_deploy.pub
   ```

3. **[you]** Add the private half as a repo secret, **base64-encoded**
   (a single line survives any clipboard/browser newline mangling; the
   workflow decodes it). Copy it:

   ```bash
   base64 -w0 < ~/.ssh/rmt_deploy | clip.exe
   ```

   Then GitHub → rmt-finder → Settings → Secrets and variables →
   Actions → New repository secret. Name: `VPS_DEPLOYMENT_KEY`, value:
   paste (one long line, no BEGIN/END markers — that's correct).

### Phase 2 — passwordless service restart

4. **[you]** Let `rmt` restart exactly the two app services and nothing
   else (sudoers matches the full argument list, so this must stay in
   sync with the `systemctl restart` line in `deploy/deploy.sh`):

   ```bash
   ssh rmt@rmtfinder.studiobeckett.ca
   echo 'rmt ALL=(root) NOPASSWD: /usr/bin/systemctl restart rmt-api rmt-scheduler' | sudo tee /etc/sudoers.d/rmt-deploy
   sudo chmod 440 /etc/sudoers.d/rmt-deploy
   sudo visudo -c        # must report: parsed OK
   sudo -k && sudo -n systemctl restart rmt-api rmt-scheduler   # proves no password needed
   ```

### Phase 3 — verify the pinned host keys

5. **[you]** Confirm `deploy/known_hosts` matches what the server itself
   reports (guards against the keyscan having been intercepted):

   ```bash
   ssh rmt@rmtfinder.studiobeckett.ca 'ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub'
   ssh-keygen -lf deploy/known_hosts
   ```

   The ed25519 fingerprints must be identical.

### Phase 4 — first deploy

6. **[you]** Commit and push this slice to `main`, then watch the
   Actions tab. The deploy job should go green and end with a successful
   curl of the live site.

## Acceptance criteria

- A push to `main` with passing tests updates the live site with no
  manual steps: new commit visible in `git log` on the server, both
  services restarted (`systemctl show -p ActiveEnterTimestamp rmt-api`),
  site still serving.
- A push with a failing test does **not** deploy (deploy job skipped).
- A pull request runs tests but never deploys.
- The scraper cadence survives a deploy: the next `runs` row lands
  within the normal interval.
