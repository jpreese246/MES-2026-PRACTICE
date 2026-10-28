# Backlog

**Project:** MES Workshop 2026
**Maintained by:** the PM
**Format:** Work not yet specced, grouped by priority. When an item is specced it gets a task ID, a row in the task index (`project_management.md`), and a pointer from here to its spec. Done items are struck through, not deleted, until the next tidy.

**Priority:** P0 blocking · P1 needed for the next milestone · P2 degrades experience, workaround exists · P3 polish / later
**Effort:** S (one Dev run) · M (2–3 runs) · L (4+ runs — split it)

Build sequence approved by Walker 2026-10-20. Each item is verified against `docs/mes_requirements.md` (§ named per item). Effort is the PM's estimate.

---

## Current milestone — Day 1: dev stack up, live tags in Ignition, process visuals

Walker, 2026-10-20: "Today's only task after standing up the dev environment is to build process visuals in perspective based on a prompt I will get from VERA."

### ~~INFRA-001 — CoreFlux, Ignition and PostgreSQL in docker-compose~~

**Status:** ✅ Complete 2026-10-20 → `docs/tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md`
**Priority:** P0 · **Effort:** S
**Origin:** Walker, 2026-10-20 (build sequence; "stand up Ignition and CoreFlux first")

Replace the template skeleton with pinned CoreFlux, Ignition and PostgreSQL services on non-colliding host ports. Verify all healthy and a test message round-trips through the broker.

### INFRA-002 — Ignition database connection to PostgreSQL

**Status:** Not specced
**Priority:** P1 · **Effort:** S
**Origin:** Walker, 2026-10-20 (build sequence)

The Ignition service itself moved into INFRA-001. What remains: the gateway's database connection to `db`. Not needed for VIS-001, so it can follow today's visuals. Licensing is a GUI-only step for Walker.

### INFRA-003 — Maestrohub, Timebase, Timebase Atlas

**Status:** Not specced
**Priority:** P1 · **Effort:** S
**Origin:** Walker, 2026-10-20 (build sequence)

Add the three services, pinned. Verify containers up and UIs reachable.

### ~~INFRA-004 — Broker cut-over (Walker-run)~~

**Status:** ✅ Done by Walker 2026-10-20, no sim restart (DEC-004)
**Priority:** P0 · **Effort:** S
**Origin:** Walker, 2026-10-20

Walker repoints the UNS Studio sim from the existing CoreFlux container (`coreflux-mqtt`, host port 1884) to this stack's CoreFlux (`127.0.0.1:1886`, from INFRA-001), once, before students pull data. May restart the sim and reset its counters. Log as a DEC in `decision-log.md`. Verify all 16 tags arrive on the new broker and the `4.0 Printing` level works.

### UNS-001 — Maestrohub ingest of the 16 raw tags

**Status:** Not specced
**Priority:** P0 · **Effort:** M
**Origin:** Walker, 2026-10-20 (build sequence)

Subscribe to the 16 tags, unwrap the envelope, cast every value, route to Ignition (`docs/sim_spec_press1.md` §11, `docs/mes_requirements.md` §2). Verify types stay correct through a Setup, Run and Fault cycle.

### UNS-002 — 16 live tags in Ignition (first visible)

**Status:** Covered for Day 1 by VIS-001 (MQTT Engine string tags, parsed and cast in the `press1` gateway library — DEC-002). Revisit only if the Core Four need real typed Ignition tags rather than the buffer
**Priority:** P0 · **Effort:** S
**Origin:** Walker, 2026-10-20 (build sequence)

The 16 tags appear in Ignition with live values, plus a bare live-values table. First thing students can see.

### ~~VIS-001 — Press 1 process visuals in Perspective~~

**Status:** ✅ Complete 2026-10-21 → `docs/tasks/task_VIS-001_press1_scada_perspective.md` (from VERA's prompt, 2026-10-20)
**Priority:** P1 · **Effort:** M (to confirm once the prompt arrives)
**Origin:** Walker, 2026-10-20 (quoted above)

Process visuals of Press 1 in Perspective, built on the UNS-002 tags. Scope comes from VERA's prompt; the PM writes the spec from it. Open question: anything in the prompt not covered by the workshop docs goes to Walker.

---

## Later

Day 1 / before Day 2:

- UNS-003 — Timebase records the 16 tags; trend over one loop
- DB-001 — The nine tables (`docs/mes_requirements.md` §7)
- DB-002 — Seed: 5 products, 10 work orders (101–105 twice, two tight due dates), schedule in sim order (§3, §7)

Work Orders (test visual Day 2 Hr 2):

- WO-001 — Run attribution, Running and Complete from the PLC, meter deltas with restart handling, publish `WorkOrder/Active` (§3)
- WO-002 — Work order test table; verify §3 values over one loop
- WO-003 — Manual actions: create, release, hold, cancel, close, reassign (§3)

Scheduling (test visual Day 2 Hr 2):

- SCHED-001 — Planned start and end, plan-vs-actual test table (§4)
- SCHED-002 — Readiness entry and "started without readiness" flag (§4)
- SCHED-003 — Override capture, `ScheduleOverride` publish, reconcile; four outcomes via the demo recipe (§4.1)

Downtime (test visual Day 2 Hr 3):

- DT-001 — Event detection (debounce, 101/102/103/Unclassified), `downtime_event`, `Downtime/CurrentClass` (§5)
- DT-002 — Setup split into planned changeover and overrun; two 14 s overruns (§5)
- DT-003 — Planned stop entry, `PlannedStop` publish, conflict flag (§5)
- DT-004 — Downtime test table and totals by class; 15 alarms per loop (§5)

OEE (test visual Day 2 Hr 3):

- OEE-001 — `oee_interval` writer, one row per minute per product (§6)
- OEE-002 — Window aggregation, `OEE/*` publish, four tiles and per-job table; within 1–2 points of §6

Day 2 Hr 4:

- AI-001 — Timebase Atlas model and the §9 AI queries
- VIS-002 — Real MES visuals in one pass

## Parked / won't do

- None yet.
