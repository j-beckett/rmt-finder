---
name: prd-to-issues
description: Break a PRD into independently-gradable local issue markdown files as vertical slices. Use when the user wants to turn a PRD into issues or tasks.
---

# PRD to Issues

Break a PRD into independently-grabbable issues using vertical slices (tracer bullets).

Issues are written as **local markdown files in a per-PRD folder under `docs/plans/`** — do NOT create issues on GitHub or use `gh issue create`.

## Process

### 1. Locate the PRD

Ask the user for the PRD as a local file path (e.g. `docs/prd/02-search.md`) and read it directly with the Read tool.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code.

### 3. Draft vertical slices

Break the PRD into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (scraper/adapter, data model, output, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

Always create a final QA issue with a detailed manual QA plan for all items that require human verification. This QA issue should be the last item in the dependency graph, blocked by all other slices. It should be HITL.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories from the PRD this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Write the issue files

Write each approved slice as a markdown file in a per-PRD folder under `docs/plans/`, named after the PRD slug — e.g. for `docs/prd/scraper-coverage.md`, the folder is `docs/plans/scraper-coverage/`. Create the folder if it does not exist. Do NOT use `gh` or create anything on GitHub.

Name files with a zero-padded ordinal and a short name, e.g. `docs/plans/scraper-coverage/01-happy-path.md`, `docs/plans/scraper-coverage/02-resilience.md`, `docs/plans/scraper-coverage/03-qa.md`. This keeps a feature's slices grouped and ordered on disk.

The parent PRD lives at `docs/prd/<slug>.md`; reference it by that path (no issue number needed). Reference blocking slices by their path rather than an issue number.

Use the issue body template below.

<issue-template>
# <Slice title>

**Type:** AFK | HITL

## Parent PRD

`docs/prd/<slug>.md`

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation. Reference specific sections of the parent PRD rather than duplicating content.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- `docs/plans/<slug>/<blocking-file>.md` (if any)

Or "None - can start immediately" if no blockers.

## User stories addressed

Reference by number from the parent PRD:

- User story 3
- User story 7

</issue-template>

Do NOT modify the parent PRD file.
