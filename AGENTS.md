# rmt-finder — Agent Workflow

rmt-finder scrapes RMT (registered massage therapist) availability from clinic booking platforms (Jane App, Geomatry) so open slots can be found without checking each clinic site individually.

## The loop

1. **Grill** — Use the `grill-me` skill to stress-test an idea before writing code. Resolve every branch of the decision tree with one question at a time.
2. **PRD** — Use the `prd` skill to turn the grilled idea into a product requirements doc (problem, users, scope, acceptance criteria). Save output to `docs/prd/`.
3. **Issues (optional)** — Use the `prd-to-issues` skill to break a PRD into local vertical-slice issue docs under `docs/plans/<slug>/`.
4. **Plan** — Have the agent sketch a short technical implementation plan from the PRD (files to touch, steps, sequencing) and save it to `docs/plans/<feature-name>.md`. This is the first step of the `do-work` skill below — there's no separate `plan` skill to invoke.
5. **Implement** — The rest of `do-work`: write tests first (red/green/refactor with pytest), validate, then commit.

## Skills

| Skill | Path | Purpose |
|-------|------|---------|
| grill-me | `.claude/skills/grill-me/` | Stress-test a plan or design |
| prd | `.claude/skills/prd/` | Write a product requirements doc |
| do-work | `.claude/skills/do-work/` | Plan, implement (test-first), validate, and commit a unit of work |
| prd-to-issues | `.claude/skills/prd-to-issues/` | (optional) Break a PRD into local issue docs (`docs/plans/<slug>/`) as vertical slices |

## What's already built

- `backend/scraper/` — adapters (Jane App, Geomatry) that fetch and parse clinic availability
- `backend/scraper/runner.py` — runs all configured clinics and aggregates results
- `backend/scraper/clinics.py` — clinic list and exclusion dict
- `backend/main.py` — CLI entrypoint; prints results and writes a timestamped JSON snapshot to `data/`
- `backend/tests/` — pytest suite (currently a smoke test on `models.py`; scraper/adapter coverage not yet built)

## Commands

```bash
venv\Scripts\python.exe backend\main.py   # run the scraper
venv\Scripts\python.exe -m pytest         # run tests
```

## Definition of done (every feature)

- Acceptance criteria from the PRD are met
- New backend logic has pytest coverage written test-first (red/green/refactor)
- `pytest` passes
- No dedup of results added unless filtering has already been proven clean — duplicates usually signal a filtering bug, not a display problem
