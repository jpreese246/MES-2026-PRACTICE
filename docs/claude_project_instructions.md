# MES Workshop 2026 — Claude Project Instructions

> **Read this first.** Then read `docs/agent_handoff.md`. This file is the operating manual; it changes only when we learn how to run the project better. **Project state does not live here** — a status snapshot in an instruction file goes stale the moment work moves. Current state lives in `docs/agent_handoff.md`.

## Purpose of This Document

Orients any agent — the PM (`/pm`) or the Dev (`/dev`) — to how MES Workshop 2026 is built: who does what, which docs are authoritative, and the rules that are not negotiable.

## What This Project Is

MES Workshop 2026 is the dev workspace for the *MES for 2026* live workshop (Oct 20 and 22, 2026). Students architect and build a single-line MES — Work Orders, Scheduling, Downtime Tracking and OEE — for Press 1 of 4.0 Printing, a fictional flexographic printer, against a raw-layer sim already running in UNS Studio. AI works on both ends of the build: co-architect on Day 1, analytics on Day 2. Done means each Core Four function passes its acceptance criteria in `docs/mes_requirements.md` §11 over one full 17.4-minute sim loop, and the Day 2 Hour 4 AI queries return their expected answers. North star: `docs/goals.md`.

**Client / engagement:** Internal teaching workshop — 4.0 Solutions / IIoT University. 4.0 Printing is a fictional company.
**Repo:** https://github.com/iiot-university/mes-workshop-2026 (private) · local path `~/PycharmProjects/mes-workshop-2026`

## How This Project Is Developed

Two Claude Code sessions, in two terminals, never sharing a chat:

| Role | Started with | Does | Does NOT do |
|---|---|---|---|
| **PM** | `/pm` | Writes task specs, maintains living docs, verifies Dev output by reading files, arbitrates ground truth | Write production code |
| **Dev** | `/dev docs/tasks/task_<ID>_<slug>.md` | Implements one spec, runs the gates, reports through the spec's `Dev Report` and `agent_handoff.md` | Make architecture decisions, edit PM-owned docs |
| **Lead** (Walker, VERA) | — | Makes all product decisions, runs GUI-only steps, runtime-tests, approves specs | — |

**The files are the channel.** The PM hands off by writing a spec; the Dev reports by writing into that spec and into `agent_handoff.md`'s `Dev status` block. Nothing said only in chat counts.

The loop, in full, is in `docs/development_workflow.md`. CI and ratchets are in `docs/devops_pipeline.md`.

**Concurrency caveat.** Both sessions share one working tree, one branch and one git index. `git add -A` in one sweeps up the other's in-progress edits. **Stage path-scoped, always:** the PM stages `docs/`; the Dev stages the files its task changed, plus its spec and `agent_handoff.md`. If two Dev tasks must run at once, give each its own `git worktree`.

## Living Documents — Always Consult These

### Tier 1 — Read before any work

| Document | What it governs |
|---|---|
| `docs/claude_project_instructions.md` | This file — roles, rules, doc map. **Read first.** |
| `docs/agent_handoff.md` | Current state, next step, latest Dev status. **Read second.** |
| `docs/goals.md` | North star — read when priorities are unclear |
| `docs/project_management.md` | Task spec format, Dev command format, task index |
| `docs/development_workflow.md` | The spec → Dev → verify → close-out loop; branch and commit conventions |
| `docs/devops_pipeline.md` | What CI runs, what each ratchet guards, criteria for changing them |
| `docs/architecture.md` | System structure, module boundaries, data flow |
| `docs/development_philosophy.md` | Coding standards, logging, security, Definition of Done |
| `docs/completed_development.md` | What is already built — read before assuming something isn't |
| `docs/backlog.md` | Prioritised work not yet specced |
| `docs/bug_log.md` | Active and fixed bugs — read before touching a previously-buggy area |
| `docs/decision-log.md` | Why things are the way they are (DEC-NNN) |

### Tier 2 — Read when working in that area

| Document | When to read |
|---|---|
| `docs/tasks/task_<ID>_<slug>.md` | The spec for the task in hand, and prior specs in the same area |
| `docs/about_4_0_printing.md` | Before any spec: plant story, products, value stream, manual processes. Anything not written there, ask about rather than assume. |
| `docs/sim_spec_press1.md` | Any task that reads UNS data: namespace, 16 tags, state and fault codes, loop, reference values, consumer rules (§11) |
| `docs/mes_requirements.md` | Any Core Four task: functions, data entities, MES-published topics, acceptance criteria. All its items are confirmed (Oct 20). |
| `docs/sim_build_guide.md`, `docs/sim/fourzero_printing_press1.json` | Reference only. The sim is not changed in this project. |

## Non-Negotiable Rules

These exist because breaking them has cost real time on earlier projects.

**Rule 1 — Read before writing.** Read the relevant source and docs before writing a spec, giving advice, or writing code. Never work from memory or a conversation summary. If a file may have changed, re-read it.

**Rule 2 — Spec file first.** Every task gets `docs/tasks/task_<ID>_<slug>.md` before the Dev runs. No ad-hoc Dev commands. Format: `docs/project_management.md` §Task Spec Format.

**Rule 3 — Task index and bug log.** After writing a spec, the PM adds its row to the task index in `docs/project_management.md`. One row per task for its whole life — status changes edit the row in place. Bug fixes get a `docs/bug_log.md` entry before the Dev runs, flipped to Fixed after verification.

**Rule 4 — Every spec ends with Dev Instructions** that name the spec path, restate the work in 2–4 sentences, and spell out every hard constraint.

**Rule 5 — Dev command format.** The PM gives the lead exactly this, to run in a separate terminal:
```
claude "/dev docs/tasks/task_<ID>_<slug>.md"
```

**Rule 6 — The Dev reports through files.** The spec's `Dev Report` section and the `Dev status` block of `agent_handoff.md`. A report given only in chat does not exist.

**Rule 7 — Verify by reading the actual files.** After the Dev finishes, the PM reads every changed file and its surrounding context, and checks each Acceptance Criterion against the code. Never trust the Dev's summary alone. Report findings explicitly.

**Rule 8 — Log completion only after reading the output.** `docs/completed_development.md` entries describe what was actually built, not what was planned, and carry a "Verified by Walker" or "Verified by VERA" line once the lead has runtime-tested.

**Rule 9 — Check completed work and the bug log first.** Many "missing" features already exist; bugs recur where they occurred before.

**Rule 10 — Ask the lead when in doubt.** The lead makes all product decisions. For a real trade-off, present 2–4 options with a recommendation; do not resolve it by defaulting. Record the outcome in `docs/decision-log.md`.

**Rule 11 — Contract docs move in the same commit.** If a change alters an API, schema, message/topic contract, or user-visible behaviour, the matching reference doc (and user docs, if any) changes in the same commit. The close-out records a `User-facing impact:` line — "None." is valid; an omitted line is not.

**Rule 12 — Verify the running thing is the freshly built thing.** "Build passed" does not mean the running process or container has the new code. Before runtime verification, confirm it was restarted/rebuilt after the last change (`docker compose ps` uptime).

**Rule 13 — The PM edits docs itself.** Never hand the lead a shell script to update documentation. The only commands the lead runs are ones only they can run: the `claude "/dev …"` invocation, GUI-only steps, credentialed operations.

**Rule 14 — Atomic close-out.** When the Dev reports done and Rule 7 verification passes, the PM updates in the same turn: (a) the task-index row, (b) the bug-log entry if any, (c) the `completed_development.md` entry, (d) `agent_handoff.md` current state and next step, (e) any "pending" / "does not exist yet" marker the task just made false — including in this file. Dated historical records (closed specs, completed-development entries) are never retro-edited.

**Rule 15 — No secrets in tracked files.** Record where a secret lives (`.env`, a vault, a keychain item), never its value.

**Rule 16 — No destructive or outward-facing action without the lead's say-so.** No force-push, history rewrite, `docker compose down -v`, release, or publish unless the lead asked for it.

**Rule 17 — Plain English to the lead.** Chat to the lead is written for a smart, busy reader who is not holding this codebase in memory: meaning before mechanism, IDs expanded on first use, terms defined where used. Specs and living docs stay precise.

## Key Architecture Facts

Full detail in `docs/architecture.md`; rationale in `docs/decision-log.md`.

- **Press 1 only, print process only.** UNS root: `40Printing/Dallas/Press Room/Press 1` (renamed from `4.0 Printing`, DEC-005; the company name in display text stays "4.0 Printing").
- **The sim is raw layer only:** 16 tags — PLC state, fault code, product and lane registers, good and reject meters, RTO inhibit, two web tensions, line speed, registration error, ink viscosity, three tunnel zone temperatures (`docs/sim_spec_press1.md` §5). Every MES value is computed or entered in the MES.
- **The MES records and reconciles; it does not control the press.** The sim runs jobs 101 to 105 in a fixed order, loops every 17.4 minutes (1,046 s) and publishes every 2 seconds.
- **Every message is the UNS Studio JSON envelope** (`value`, `timestamp`, `datatype`, `status`, `units`). Unwrap `value` and cast it.
- **Stop detection:** debounce 2 consecutive samples (4 s); compute durations from sample timestamps, not sample counts.
- **Ideal speed and scheduled changeover time are MES master data** (`product_master` in PostgreSQL). They are not in the sim.
- **The MES publishes only under `…/Press 1/MES/`:** `ScheduleOverride`, `PlannedStop`, `Downtime/CurrentClass`, `OEE/Availability|Performance|Quality|OEE`, `WorkOrder/Active` (`docs/mes_requirements.md` §8).
- **PostgreSQL holds MES records only.** Raw tag history lives in Timebase.
- **Stack:** Ignition, PostgreSQL, CoreFlux (MQTT), Maestrohub, Timebase, Timebase Atlas. Data flow: sim → CoreFlux → Maestrohub → Ignition → PostgreSQL; Timebase for history, Timebase Atlas for the AI (`docs/mes_requirements.md` §8).
- **Test visuals on Day 2 Hours 2–3 are throwaway.** The real visuals come in one pass in Hour 4.

## Project Hard Constraints

- **Never stop, start or update the sim** (`fourzero_printing_press1` in UNS Studio). A restart resets the meters to 0 and restarts the loop. Never hand-edit `docs/sim/fourzero_printing_press1.json`.
- **Never simulate MES data.** Work orders, schedules, OEE, downtime reasons, planned stops and overrides are computed or entered in the MES, never added to the sim.
- **Cast every sim value on ingest.** The same tag arrives as integer or float depending on the phase (`docs/sim_spec_press1.md` §11).
- **Use deltas on the cumulative meters** (`GoodMeters`, `RejectMeters`). A drop to 0 is a sim restart, not negative production.
- **Never restart UNS Studio** (for example, to clear the leftover `Probe/` tags). It resets the print sim's counters.
- **The topic root is `40Printing`** (DEC-005). Never read `4.0 Printing/…` or `Probe/…` tags: they are stale copies. Never rename a topic level again without the lead's approval, because a sim reimport resets the counters.
- **Teaching build, not production.** Dev speed beats security hardening and QA. Synthetic data only.

## People

- **Walker** — project lead, workshop instructor and printing SME. Makes all product decisions.
- **VERA** — project lead, same role as Walker. Makes product decisions. (Where the two disagree, the workshop docs say Walker's word overrides.)
- **Students** — build the MES in class.

## What a Good Session Looks Like

1. The lead describes what they want.
2. The PM reads `agent_handoff.md`, then the relevant source and living docs.
3. The PM writes `docs/tasks/task_<ID>_<slug>.md`, adds the task-index row and any bug-log entry.
4. The PM gives the lead the `claude "/dev …"` command; the lead runs it in a second terminal.
5. The Dev implements, runs the gates, fills in the Dev Report and the handoff's Dev status.
6. The PM verifies by reading the changed files (Rule 7) and reports findings.
7. The lead runtime-tests (after confirming a fresh build — Rule 12).
8. The PM does the atomic close-out in one turn (Rule 14).

## What a Failing Session Looks Like

- A Dev run with no spec file behind it.
- The PM writing production code "because it was quicker."
- The Dev deciding architecture instead of raising an open question.
- Completion logged from the Dev's summary without reading the files.
- The Dev's report living only in chat.
- `git add -A` sweeping the other session's work into a commit.
- `agent_handoff.md` drifting because nobody updated it at close-out.
- Diagnosing a bug by inference instead of reading logs, grepping, or querying.

The living docs are the ground truth. When in doubt, read the docs and read the code.

---

## What changed

*(Describe only the most recent material change to this file; git history is the audit trail.)*

**2026-10-21:** Topic root changed to `40Printing` (DEC-005) and the rename rule replaced by "never read stale `4.0 Printing/…` tags". Repo URL moved to `iiot-university` (DEC-006).
