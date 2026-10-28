# Completed Development

**Project:** MES Workshop 2026
**Maintained by:** the PM
**Format:** Reverse chronological. Each entry describes what was **actually built**, verified by reading the files (Rule 7) — not what was planned.

---

## How to use this log

Every completed task gets an entry, written by the PM at close-out (Rule 14). Entries are **not edited after they are written**, except to add the "Verified by" line. Corrections become new entries.

## Entry template

```
### {ID} — {short headline}

**Date:** YYYY-MM-DD
**Spec:** [`tasks/task_{ID}_{slug}.md`](tasks/task_{ID}_{slug}.md)
**Commit:** {hash}
**Verified by {Walker | VERA}:** ✅ YYYY-MM-DD — "{quote}"  (or ⏳ pending runtime test)

**What was built:** concrete deliverables.
**Files touched:** paths.
**Deviations from spec:** what the Dev did differently, and why it was acceptable — or "None."
**User-facing impact:** what a user would notice, and which docs changed — or "None."
```

---

### VIS-001 — Press 1 SCADA view in Perspective with gateway trend buffer

**Date:** 2026-10-21
**Spec:** [`tasks/task_VIS-001_press1_scada_perspective.md`](tasks/task_VIS-001_press1_scada_perspective.md)
**Commit:** 72dc415
**Verified by Walker:** ✅ 2026-10-21 — "if thats ok -- then apprvoed"

**What was built:** Ignition project `mes-2026`, now in the repo at `ignition/projects/mes-2026/` and bind-mounted into the gateway (D2). Project library `press1` reads the 16 MQTT Engine string tags under `[MQTT Engine]40Printing/Dallas/Press Room/Press 1` (one `ROOT` constant), unwraps the envelope and casts once, and keeps a 1,800-row (60 min) buffer in `system.util.getGlobals()['press1.v2']`. It also tracks meter deltas with restart handling, events (2-sample debounce, backdated, split on fault-code change), jobs observed, and a 10 s sampling-gap guard. A gateway timer `press1Tick` (2000 ms fixed delay, own thread) calls `press1.tick()`. Perspective page `/press1` (`Press1/Main`) has five tabs (Overview, Tunnel Dryer, Web & Print, Production, Alarms & State) and a 5/15/30/60 min window selector, and its trends use `ia.chart.timeseries` with "gateway buffer, N samples" footers. Colours live only in the project stylesheet. URL: http://localhost:8089/data/perspective/client/mes-2026/press1
**Files touched:** `docker-compose.yml` (one bind-mount line), `ignition/projects/mes-2026/**`.
**Deviations from spec:**
- Project reloads use the gateway's "Scan File System" button.
- `alarm_summary` counts since gateway start.
- Extra red `NO DATA` pill when the newest sample is more than 10 s old.
- Fixed axis tops (state trend 0–4, zone trend 250 °F).
- MES words trimmed from the reference footnotes.
- Versioned store key `press1.v2`, so an open Designer running old library code cannot wipe the live buffer.
- Views are written by a generator kept outside the repo. The files in the repo are the source of truth.
**User-facing impact:** The new SCADA page above. `docs/architecture.md` §1, §2, §5 updated at close-out. The buffer empties on any gateway restart. It also stops sampling while the Mac sleeps, and the gap guard keeps events and jobs honest.

### INFRA-001 — Dev stack: CoreFlux, Ignition and PostgreSQL

**Date:** 2026-10-20
**Spec:** [`tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md`](tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md)
**Commit:** 87af5b0
**Verified by Walker:** ✅ 2026-10-20 — "sim is pointed at 1886, no restart — close it out"

**What was built:** `docker-compose.yml` (project `mes-workshop-2026`) with three pinned services: `coreflux` (CoreFlux 2.2.0; host 127.0.0.1 1886 MQTT, 8084 web, 5004 API; volume `coreflux-data`), `db` (PostgreSQL 16.15; host 5434; DB/user `mes`) and `ignition` (8.3.10 Standard, host 8089, MQTT Engine/Transmission modules; now `depends_on` coreflux and a healthy db). Template `broker`/`app` services removed. `.env.example` lists the five new variable names; `.env` holds the generated secrets locally. All three healthy; MQTT round trip verified from the host and in-network. Walker then repointed the sim to 1886 (INFRA-004, DEC-004); all 16 sim topics confirmed on the new broker.
**Files touched:** `docker-compose.yml`, `.env.example`.
**Deviations from spec:** AC 6 test run with explicit MQTT client IDs — CoreFlux 2.2.0 refuses an empty client ID. Accepted; recorded as a trap in `agent_handoff.md` and in `architecture.md` §2.
**User-facing impact:** Ignition at http://localhost:8089, CoreFlux web UI at http://localhost:8084, the sim's broker is now `127.0.0.1:1886`. `docs/architecture.md` §1, §2, §5, §6 updated at close-out.

