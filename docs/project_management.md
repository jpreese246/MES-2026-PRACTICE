# Project Management

**Project:** MES Workshop 2026
**Status:** Canonical workflow document
**Last updated:** 2026-10-20

---

## 1. Roles

- **PM** — Claude Code session running `/pm`. Plans, writes specs, maintains living docs, verifies Dev output by reading files. Never writes production code.
- **Dev** — a separate Claude Code session running `/dev <spec>`. Implements one spec, runs the gates, reports through files.
- **Lead (Walker or VERA)** — makes all product decisions, approves specs, runs GUI-only steps, runtime-tests.

## 2. Task lifecycle

See `docs/development_workflow.md` §1. In short: **spec → Dev → Dev Report → PM verify → lead runtime-test → PM close-out.**

## 3. Task IDs

`<AREA>-NNN` (e.g. `INFRA-001`, `SIM-003`, `BUG-012`). Follow-up fixes to a verified-failing task are `<ID>-fix1`, `-fix2`. Slices of a large task are `<ID>-S1`, `-S2`.

## 4. Task Spec Format

File: `docs/tasks/task_<ID>_<slug>.md`. The worked example is `docs/tasks/_archive/task_EXAMPLE-001_example_task.md`. Sections, in order:

| Section | Owner | Purpose |
|---|---|---|
| Header (Status, Priority, Effort, Depends on, Bug) | PM (Dev updates Status) | At-a-glance state |
| Background | PM | Why the task exists; what the user experiences after |
| What Already Exists (Do Not Rewrite) | PM | Working code/infra the Dev must not touch, with paths and line refs |
| What to Build | PM | Exact implementation — files, signatures, contracts, error handling |
| Acceptance Criteria | PM | Testable checkboxes; the PM verifies each against the code |
| Files to Modify | PM | Table of path → change |
| Dev Instructions | PM | 2–4 sentence restatement + every hard constraint |
| Dev Report | **Dev** | What was built, files, gate output, deviations, open questions |
| PM Verification | PM | Rule 7 findings, added after the Dev reports |

**Rules for writing specs:**
- Read the relevant source before writing. Never spec from memory.
- Check `completed_development.md` and `bug_log.md` first.
- Never leave an architecture decision to the Dev. If the Dev would have to guess, the spec is incomplete.
- Name every contract/user doc that must change in the same commit (Rule 11).

## 5. Dev Command Format

The PM gives the lead this, to run in a **separate terminal**:

```
claude "/dev docs/tasks/task_<ID>_<slug>.md"
```

The `/dev` command loads the Dev role, reads the instructions and the spec, and binds the Dev to report through the spec's `Dev Report` and `agent_handoff.md`.

## 6. Verification Discipline (Rule 7)

After the Dev reports done, the PM:

1. Reads the Dev Report and the handoff's Dev status.
2. Runs `git status` / `git diff` to find every changed file — including any the Dev did not mention.
3. Reads each changed file and its surrounding context; checks for collateral damage and scope creep.
4. Checks each Acceptance Criterion against the code, and re-runs the gates where cheap.
5. Writes findings under `## PM Verification` in the spec — pass, or exactly what failed.

## 7. Task Index

One row per task for its whole lifecycle — edit in place, never append a second row.

**Status values:** 📝 Specced · 🔨 In progress · 🔍 Awaiting PM verify · 🧪 Awaiting lead test · ✅ Complete · ⛔ Blocked · 🗄️ Superseded

| ID | Summary | Spec | Status | Lead-verified |
|---|---|---|---|---|
| INFRA-001 | Dev stack: CoreFlux 2.2.0 (MQTT on 1886), Ignition 8.3.10 (8089), PostgreSQL 16 (5434) in docker-compose | `docs/tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md` | ✅ Complete | Walker 2026-10-20 |
| VIS-001 | Press 1 SCADA view in Perspective (`mes-2026`), raw PLC data, gateway in-memory trend buffer | `docs/tasks/task_VIS-001_press1_scada_perspective.md` | ✅ Complete | Walker 2026-10-21 |
| EXAMPLE-001 | Format example from the template. | `docs/tasks/_archive/task_EXAMPLE-001_example_task.md` | 🗄️ Archived | — |

## 8. Bug Log Workflow

A bug gets a `docs/bug_log.md` entry when found. Before it is fixed it gets a spec (`task_BUG-NNN_<slug>.md`) and a task-index row. It is marked Fixed, with the root cause, only at close-out after Rule 7 verification.

## 9. Common Failure Modes

- Spec written from memory; the code had moved on.
- Acceptance Criteria that can't be checked by reading code or running a command.
- Dev report accepted without reading the diff.
- Task-index row flipped to Complete without the `completed_development.md` entry in the same turn.
- `agent_handoff.md` left describing last week.
