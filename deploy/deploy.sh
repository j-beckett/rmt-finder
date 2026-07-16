#!/usr/bin/env bash
# Server-side deploy, run as the rmt user on the droplet. The GitHub Actions
# deploy job pipes this script over SSH (`ssh ... 'bash -s' < deploy/deploy.sh`)
# after rsyncing the freshly built frontend into frontend/dist, so the version
# that runs is always the one from the commit being deployed.
set -euo pipefail

cd "$HOME/rmt-finder"

git pull --ff-only
venv/bin/pip install --quiet -r requirements.txt

# Must match the sudoers entry in /etc/sudoers.d/rmt-deploy exactly
# (sudoers matches on the full argument list).
sudo systemctl restart rmt-api rmt-scheduler

# Don't declare success until the API is answering again.
for _ in {1..10}; do
    if curl -fsS localhost:8000/api/availability > /dev/null 2>&1; then
        echo "deploy ok: $(git rev-parse --short HEAD)"
        exit 0
    fi
    sleep 2
done

echo "API did not come back after restart" >&2
exit 1
