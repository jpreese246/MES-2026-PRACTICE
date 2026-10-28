# MES Workshop 2026 — Agent Handoff

**Purpose:** Orient the incoming agent (PM or Dev) to current state. **Read second**, after `docs/claude_project_instructions.md`.
**Maintained by:** the PM (all sections except `Dev status`, which the Dev overwrites after each run).

> This is an orientation doc, not a second copy of the rules. Where it disagrees with `claude_project_instructions.md`, the instructions win and this file gets corrected.

---

## Dev status (latest Dev run — overwritten by the Dev each run)

| Field | Value |
|---|---|
| Task | VIS-001 — Press 1 SCADA view in Perspective |
| Spec | `docs/tasks/task_VIS-001_press1_scada_perspective.md` |
| Status | ✅ Done — ready for PM verification |
| Date | 2026-10-21 |
| Summary | Project bind-mounted at `ignition/projects/mes-2026/`; `press1` library + 2 s gateway timer buffering the 16 tags; `/press1` Overview (banner, tiles, process flow) live and verified on 102 and 101 faults; window selector and gateway-buffer trends; Tunnel Dryer, Web & Print, Production (jobs table) and Alarms & State (% tiles, alarm summary, event log) built and verified live. All AC greps clean; second session shows the same sample count. PM fix applied: sampling-gap guard (`GAP_S`), plus a versioned globals key so an open Designer's stale library can't wipe the buffer. |
| Commit | `VIS-001: Press 1 SCADA view in Perspective with gateway trend buffer` (approved by Walker 2026-10-21; local only, not pushed) |

The full report is in the spec's `## Dev Report` section.

> **PM note, 2026-10-21:** VIS-001 has been verified by the PM, approved by Walker and closed. Commit `72dc415` is pushed to `iiot-university/mes-workshop-2026`. No Dev task is open.

---

## 📚 Workshop reference docs — read these before writing any spec

The plant, the sim and the MES requirements are already written. **Read in this order:**

| # | Doc | What it gives you |
|---|---|---|
| 1 | `docs/about_4_0_printing.md` | The story: fictional company 4.0 Printing, Press 1, products, value stream, how the line misbehaves, manual processes, leadership questions. **Anything not written here, ask about rather than assume.** |
| 2 | `docs/sim_spec_press1.md` | The raw-layer signals: namespace, 16 tags, state and fault codes, job table, loop timing, reference values per loop, consumer rules. |
| 3 | `docs/mes_requirements.md` | What the MES must do: Work Orders, Scheduling, Downtime, OEE, data model, MES-published UNS topics, AI hooks, acceptance criteria. All items confirmed by Walker, Oct 20. Walker's word overrides. |
| — | `docs/sim_build_guide.md` | Only for building or changing a UNS Studio sim. Engine rules and probe results. Not needed for the MES build. |
| — | `docs/sim/fourzero_printing_press1.json` | The sim definition, a copy of the file UNS Studio loads. Do not hand-edit. Changes go through the spec and `create_simulator` or `update_simulator`. |

**Non-negotiables from those docs**

- The sim is **raw layer only**. No work orders, OEE, downtime reasons, planned stops or schedule data are ever simulated. The MES computes or captures them.
- The MES **records and reconciles; it does not control the press.** The sim loops jobs 101 to 105 and ignores the MES.
- **Do not stop, start or update the sim during class.** A restart resets the counters to 0 and restarts the loop.
- Cast every sim value on ingest. The same tag can arrive as integer or float. Meters are cumulative, so use deltas and treat a drop to 0 as a restart.
- The topic root is `40Printing/Dallas/Press Room/Press 1` (DEC-005). The dot in `4.0 Printing` broke Ignition. The company name in display text stays "4.0 Printing".

---

## ⏱️ Current state — 2026-10-21

**Phase:** Day 1 build complete. Day 2 (Oct 22) is the Core Four build.

**What is built:**
- **INFRA-001** — CoreFlux 2.2.0 (`127.0.0.1:1886`), Ignition 8.3.10 (http://localhost:8089, user `admin`, password in `.env`), PostgreSQL 16 (5434).
- **INFRA-004** — the sim publishes to the new CoreFlux.
- **DEC-005** — topic root `40Printing/Dallas/Press Room/Press 1`.
- **VIS-001** — Press 1 SCADA page http://localhost:8089/data/perspective/client/mes-2026/press1, project `mes-2026` in `ignition/projects/mes-2026/`, gateway buffer in `press1.v2`.

See `docs/completed_development.md`.

**What is in progress:** nothing.

**Open bugs:** none. BUG-001 (CoreFlux SUBACK QoS order) is worked around. See `docs/bug_log.md`.

**Waiting on the lead:**

- A byte-for-byte copy of the renamed sim JSON from UNS Studio's `config/simulators/` for `docs/sim/` (VERA/Walker).
- The next build step for Day 2.

## ▶️ Next step

1. Walker decides how the Core Four get press data: the `press1` buffer, typed Ignition tags (UNS-002), or Maestrohub (UNS-001, INFRA-003). This was deferred by DEC-002.
2. Day 2 sequence from `docs/backlog.md`: DB-001/DB-002 (tables and seed) and INFRA-002 (Ignition DB connection), then WO-001 onward.
3. Repo copy of the sim definition: replace `docs/sim/fourzero_printing_press1.json` with a byte-for-byte copy of the renamed file once VERA/Walker provides it.

## ⚠️ Traps and standing warnings

*(Things a fresh agent will get wrong without being told. Remove an entry when it stops being true.)*

- **The new CoreFlux (2.2.0) refuses an empty MQTT client ID** ("identifier rejected"). Every client — UNS Studio, MQTT Engine, Maestrohub, Timebase, CLI tests (`mosquitto_pub -i …`) — must send one. Anonymous connections are otherwise accepted.
- **CoreFlux 2.2.0 returns SUBACK granted QoS out of order for mixed-QoS subscribes** (BUG-001). Clients that check granted QoS (MQTT Engine does) disconnect. Keep each client's subscriptions at one QoS.
- **Topic root is `40Printing`** (DEC-005). Older docs and the stale `[MQTT Engine]4.0 Printing/…` tags show the old dotted root. Never read them.
- **Views in `mes-2026` were written by a generator kept outside the repo.** The view files are the source of truth. Never regenerate over Designer edits.
- **An open Designer runs its own copy of project library code on the gateway.** After a library change, update or restart the Designer. The versioned store key (`press1.v2`) exists because two copies once fought over one `getGlobals()` entry.
- **Perspective binding trap:** a property binding on a whole object (`view.params`) delivers `None` to its transform with no log line. Bind a leaf instead.
- **Do not reach for sim data the sim does not have.** Scheduled changeover time, ideal speed, planned stops and overrides live in MES master data or MES records, not in the UNS feed.
- **A deleted UNS Studio sim leaves its tags behind.** Stale tags do not mean a live sim.
- **Sim JSON must come from the file, never from a rendered text block.** A markdown renderer turns `*` into italics and corrupts formulas.

---

*Convention: replace the Current state block at each close-out rather than stacking dated blocks forever. If history matters, it belongs in `completed_development.md` or `decision-log.md`.*
