---
name: do-work
description: "Execute a unit of work end-to-end: plan, implement test-first with pytest, validate, then commit. Use when user wants to do work, build a feature, fix a bug, or implement a phase from a plan."
---

# Do Work

Execute a complete unit of work: plan it, build it, validate it, commit it.

## Workflow

### 1. Understand the task

Read any referenced plan or PRD. Explore the codebase to understand the relevant files, patterns, and conventions. If the task is ambiguous, ask the user to clarify scope before proceeding.

If the work corresponds to a local issue doc (a slice file under `docs/plans/<slug>/`, e.g. `docs/plans/scraper-coverage/01-happy-path.md`), read it and its parent PRD, and note its path — you will mark it done in the final step. Do NOT use `gh` or GitHub; issues live as local markdown files.

### 2. Plan the implementation (optional)

If the task has not already been planned, create a short plan (files to touch, steps, sequencing) and save it to `docs/plans/<feature-name>.md`, matching the format of existing plans in `docs/plans/`.

### 3. Implement

Use strict red/green/refactor, one test at a time, in a tracer-bullet style.

**Non-negotiable rule: never write implementation code before a test that fails without it.** Each slice MUST follow this order:

1. Write a single failing test for the smallest vertical slice of behavior.
2. **Run that test and observe it fail (red).** Actually execute it with `pytest` and confirm the failure is the expected one (e.g. missing import, wrong value, wrong exception) — not a typo or unrelated error. Do not skip or assume this step; the red run is the proof the test is meaningful.
3. Write the minimum code to make it pass — nothing more.
4. **Run the test again and confirm it passes (green).**
5. Refactor if needed, keeping the test green.
6. Repeat from step 1 for the next slice of behavior.

Hard constraints:

- Do NOT write all tests upfront — write one, red, green, then move on.
- Do NOT write the implementation and its test together, or the implementation first "to save time." If you already have implementation code with no failing test behind it, delete/stub it and re-derive it test-first.
- Each test targets one thin vertical slice through the system (e.g. one adapter method, one filter rule, one runner behavior) — not the whole scrape pipeline at once.
- Prefer testing against fixture HTML/JSON captured from real responses over live network calls in tests.

### 4. Validate

Run the test suite and fix any issues. Repeat until it passes cleanly.

```
venv\Scripts\python.exe -m pytest
```

If the repo later adds a linter/type-checker (e.g. ruff, mypy), run those here too.

### 5. Commit

Once the test suite passes, commit the work.

### 6. Mark the issue done

If the work corresponds to a local issue doc, mark it done once the commit has landed and all of its acceptance criteria are met:

1. Verify every acceptance-criteria checkbox in the slice file is satisfied. If any is not, leave the boxes unchecked and tell the user what remains.
2. Check off the completed acceptance-criteria boxes (`- [ ]` → `- [x]`) in the slice file, and record the commit SHA in the file (e.g. a "Done in `<sha>`" note near the top). Reference the slice path in the commit message.
3. Do NOT mark the manual-QA slice (the HITL gate) done yourself — it is always human-verified. After finishing the last AFK slice, tell the user that only the manual-QA gate remains and that checking it off is theirs to do.

If the work has no associated issue doc, skip this step.
