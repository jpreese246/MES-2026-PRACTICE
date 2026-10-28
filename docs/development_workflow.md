# Development Workflow

**Project:** MES Workshop 2026
**Audience:** the lead, the PM session (`/pm`), the Dev session (`/dev`).

---

## 1. The loop

```
   1. PM writes spec            → docs/tasks/task_<ID>_<slug>.md, task-index row, bug-log entry
   2. Lead approves spec        → (optional for small tasks; required for anything architectural)
   3. Lead starts the Dev       → second terminal: claude "/dev docs/tasks/task_<ID>_<slug>.md"
   4. Dev implements            → code + contract docs, gates run
   5. Dev reports               → spec's Dev Report + agent_handoff.md Dev status
   6. PM verifies (Rule 7)      → reads every changed file; checks each Acceptance Criterion
   7. Lead runtime-tests        → against a fresh build/restart (Rule 12)
   8. PM close-out (Rule 14)    → task index, bug log, completed_development, handoff — one turn
   9. Commit                    → per §3; push only when the lead says so
```

**Step 6 gates step 8.** Never write "Verified by the lead" before the lead has verified.

**If verification fails**, the PM records what failed in the spec (under a `## PM Verification` heading) and writes a `<ID>-fix1` spec, or — for a trivial miss — sends the same spec back to the Dev with the gap named. The PM still does not fix it themselves.

## 2. Two sessions, one tree

The PM and the Dev share a working tree, a branch and a git index.

- **Stage path-scoped.** PM: `git add docs/`. Dev: the files it changed + its spec + `docs/agent_handoff.md`. **Never `git add -A` or `git add .`.**
- **One Dev task at a time per tree.** For parallel Dev work, use `git worktree add ../<repo>-<ID> -b <ID>-<slug>`.
- **One writer to the Docker stack at a time.** Only the Dev runs `docker compose up`, `restart` or `pull`. The PM runs read-only `docker compose ps` and `logs`.

## 3. Branches and commits

**Branch policy:** direct to `main` for the workshop (Oct 20–22, 2026); no PRs. Record any change to this policy in `decision-log.md`.

**Commit message:**
```
<TASK-ID>: <what changed, imperative, ≤72 chars>

<optional body: why, not what — the spec already says what>
```

Typical sequence for one task: `Spec <ID>: …` (PM) → `<ID>: …` (Dev) → `Docs: close out <ID>` (PM).

## 4. Pull request (when the branch policy uses PRs)

Title: `<TASK-ID>: <summary>`

```markdown
**Spec:** docs/tasks/task_<ID>_<slug>.md

## What changed
<2–4 sentences>

## User-facing impact
<One line, or "None.">

## Verification
- [ ] PM Rule-7 verified against the actual changed files
- [ ] Lead runtime-tested against a fresh build (Rule 12)
- [ ] Close-out landed (Rule 14)
- [ ] Contract/user docs updated in this PR, or N/A (Rule 11)
```

## 5. Invariants that no workflow change softens

- No production code from the PM session.
- No secrets in tracked files.
- No destructive git and no push without the lead's say-so.
- Never stop, start or update the sim, and never restart UNS Studio.
