# mes-workshop-2026

Development repo for the **MES for 2026** live workshop (4.0 Solutions / IIoT University, Oct 20 and 22, 2026). Students architect, build and run a single-line Manufacturing Execution System (work orders, scheduling, downtime tracking, OEE) with AI working on both ends of the build.

> **4.0 Printing is a fictional company.** The plant, products, customers, numbers and people in the documents and the sim are invented for teaching. Nothing here describes a real business.

Created from the `40solutions/mes-dev-template` pattern (commit `4ffc966`).

## Workshop documents

Start with these, in this order. Agents read the same order (`docs/agent_handoff.md`).

| Doc | Purpose |
|---|---|
| `docs/about_4_0_printing.md` | The simulated plant and its value stream |
| `docs/sim_spec_press1.md` | The raw-layer sim: tags, states, fault codes, loop, reference values |
| `docs/mes_requirements.md` | The Core Four MES requirements |
| `docs/sim_build_guide.md` | Rules for building sims in UNS Studio |
| `docs/sim/fourzero_printing_press1.json` | The sim definition (UNS Studio simulator format) |

## The two-terminal workflow

Every project runs **two Claude Code sessions side by side** in the repo root:

| Terminal | Start with | Role |
|---|---|---|
| **1 — PM** | `claude`, then `/pm` | Writes task specs to `docs/tasks/`, maintains the living docs, verifies the Dev's work by **reading the changed files**. **Never writes production code.** |
| **2 — Dev** | `claude "/dev docs/tasks/task_<ID>_<slug>.md"` | Implements that one spec, runs the gates, and reports back **through files**. |

**The two sessions never talk to each other directly.** The handoff goes through files only:

```
 PM ──writes──▶ docs/tasks/task_<ID>_<slug>.md ──read by──▶ Dev
 Dev ──writes──▶ spec's "## Dev Report"  +  docs/agent_handoff.md "Dev status" ──read by──▶ PM
```

One cycle:

1. Tell the PM what you want. It writes the spec and gives you the exact `claude "/dev …"` command.
2. Paste that command into terminal 2. The Dev implements the spec and fills in its Dev Report.
3. Back in terminal 1, tell the PM the Dev is done. It reads the actual diff, checks every acceptance criterion, and reports what it found.
4. You runtime-test. Then the PM closes out the task: task index, bug log, completed-development log and handoff, all in one turn.

Both sessions share one git index, so **each stages only its own paths** (PM: `docs/`; Dev: the files it changed). Neither ever runs `git add -A`.

## Doc reading order

Every session, PM or Dev, starts the same way:

1. **`docs/claude_project_instructions.md`**: the operating manual. Roles, rules, and the map of every other doc.
2. **`docs/agent_handoff.md`**: current state, next step, the workshop reference docs, and the latest Dev status.

Then read what the task needs. The Tier-1 table in the instructions file lists every doc and when it applies.

There is **no root `CLAUDE.md`**, on purpose. The operating manual lives in `docs/`, where both agents read it explicitly.

## What's in here

```
.claude/
  skills/pm/SKILL.md        /pm  — PM role
  skills/dev/SKILL.md       /dev — Dev role
  settings.local.json       starter permissions
docs/
  claude_project_instructions.md   read first
  agent_handoff.md                 read second
  about_4_0_printing.md  sim_spec_press1.md  mes_requirements.md  sim_build_guide.md
  sim/fourzero_printing_press1.json
  architecture.md  backlog.md  bug_log.md  completed_development.md
  decision-log.md  development_philosophy.md  development_workflow.md
  devops_pipeline.md  goals.md  project_management.md
  tasks/_archive/task_EXAMPLE-001_example_task.md   spec format example
docker-compose.yml          local stack: CoreFlux, PostgreSQL, Ignition
.env.example                env var names for docker-compose
.gitignore
```

## Local setup

```bash
cp .env.example .env            # fill in; .env is git-ignored
grep -rn '{{' --exclude-dir=.git .   # every placeholder still to fill
```
