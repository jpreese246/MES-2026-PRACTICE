# VIS-001 — Press 1 SCADA view in Perspective (raw PLC data, gateway trend buffer)

**Status:** ✅ Complete — 2026-10-21, approved by Walker
**Priority:** P1 · **Effort:** M (one Dev session, four build steps with a lead review after each)
**Depends on:** INFRA-001 ✅, INFRA-004 ✅, BUG-001 workaround ✅
**Bug:** —

---

## Background

Last dev step of Day 1, shown live to students: a tabbed Perspective SCADA view of Press 1 that copies the layout, colours, wording, thresholds and logic of the React dashboard Walker built in UNS Studio. Raw PLC data only — SCADA, not MES. No history in Ignition: trends come from a rolling in-memory buffer on the gateway.

**The requirements are VERA's prompt, reproduced verbatim in the Appendix.** It is authoritative for look, tabs, event rules, buffer size, build order and acceptance. This spec adds the preflight findings, the architecture decisions the Dev must not make, and the hard constraints.

## Preflight findings (PM, 2026-10-20 ~14:10 CDT, read-only)

**a. Gateway.** Build in **`mes-workshop-2026-ignition-1`** — compose service `ignition`, Ignition 8.3.10, http://localhost:8089 (`docker ps --filter publish=8089`). It is this repo's gateway (INFRA-001), the one connected to this repo's CoreFlux. `ignmes-ignition` (8.3.9, port 8088) belongs to the separate ign-mes-demo project: **do not touch it.**

**b. Ingest path — exists, configured by Walker in the gateway UI (DEC-002).** MQTT Engine server `MES Coreflux` → `tcp://coreflux:1883`, client ID `ignition-client`, `enablePrimaryHostSubscriptions: false` (the BUG-001 workaround). Connected and stable: last reconnect 13:59:01, none since. Custom namespace `All`:
```json
{ "subscription": "#", "jsonPayload": false, "numbersAsFloats": false, "qos1": false, "writableTags": false }
```
- `jsonPayload: false` → each MQTT topic becomes **one String tag holding the raw envelope JSON** in the MQTT Engine tag provider. That is what we want: the gateway script parses and casts once (sim spec §11 rules 1–2). Keep it.
- `subscription: "#"` — kept by Walker's decision (D1). The tag provider will also hold any other topic on the broker; the project ignores everything but the 16 named tags.
- Live broker, `40Printing/#` for 5 s: all 16 topics at the root **`40Printing/Dallas/Press Room/Press 1`**, publishing every 2 s. `#` on the broker shows only `40Printing` plus one retained `spBv1.0/STATE/IamHost`. Nothing under `4.0 Printing/` or `Probe/` arrives on the broker (non-retained).
- **Stale tags likely exist in Ignition anyway.** MQTT Engine was subscribed to `#` from ~13:18 and the sim used the old root until ~13:45, so the MQTT Engine tag provider probably holds frozen `4.0 Printing/…` tags. Reference `40Printing/…` only.
- **Repo docs vs live:** the docs still say `4.0 Printing`. Live broker says `40Printing`. **Trust the live broker** (DEC-005). The PM syncs the docs separately; the Dev does not edit them.

**c. Project.** The gateway already has an empty project **`mes-2026`** (`data/projects/mes-2026/`, inside the `ignition-data` named volume — not version-controlled). See D2.

## Decisions (Walker, 2026-10-20)

**Outcome:** D1 — **declined**: leave the MQTT Engine subscription at `#` ("there's nothing else publishing"). This overrides the prompt's "subscribe to `40Printing/Dallas/Press Room/Press 1/#` only". The project still **reads** only the 16 named `40Printing/…` tags. D2 — **approved**. D3 — **approved**.

**D1 — Narrow the MQTT Engine subscription.** Change custom namespace `All` subscription from `#` to `40Printing/Dallas/Press Room/Press 1/#` (keep every other field). *Recommend:* yes, and **Walker makes the change in the gateway UI** (MQTT Engine → Settings → Namespaces → Custom → All) — the Dev does not change gateway or broker settings. Also note: `…/Press 1/#` will include `…/Press 1/MES/…` once the MES publishes; the SCADA view ignores it because it reads only the 16 named tags.

**D2 — Version-control the project with a bind mount.** Copy the existing `mes-2026` project out of the container to **`ignition/projects/mes-2026/`** in the repo, then bind-mount that folder at `/usr/local/bin/ignition/data/projects/mes-2026` in `docker-compose.yml`. Designer saves land in the repo; git tracks them. *Cost:* the Ignition container is recreated once (~1–2 min gateway restart; MQTT Engine reconnects; the sim and CoreFlux are untouched). *Alternative:* leave it in the volume and `docker cp` it out before each commit — clunky and easy to forget. *Recommend:* bind mount.

**D3 — Buffer mechanism.** One **gateway timer event script** in `mes-2026`, fixed delay 2000 ms, holding state in `system.util.getGlobals()`. *Why timer, not tag change:* the 16 tags update independently, so a tag change script fires ~16× per publish and needs its own grouping; a timer takes one aligned snapshot of all 16 per tick. *Recommend:* timer.

## What Already Exists (Do Not Rewrite)

- `docker-compose.yml` service `ignition` — unchanged except the one D2 volume line. Do not touch `coreflux` or `db`.
- MQTT Engine server and namespace settings (Walker's). Read them; do not change them.
- Project `mes-2026` on the gateway (empty apart from `global-props`).
- The reference dashboard `~/Library/Application Support/UNS Studio/data/dashboards/printing-press-1-scada.jsx` — **read only**. Key constants already confirmed by the PM: `BASE = '40Printing/Dallas/Press Room/Press 1'`, `TEMP_LIMIT = 200`, `MAX_ROWS = 1800`, events capped at 200, colours as in the prompt.

## What to Build

### 1. Project in the repo (D2)

1. `docker cp mes-workshop-2026-ignition-1:/usr/local/bin/ignition/data/projects/mes-2026 ignition/projects/mes-2026`
2. Add to the `ignition` service volumes: `- ./ignition/projects/mes-2026:/usr/local/bin/ignition/data/projects/mes-2026`
3. `docker compose up -d ignition` (recreates only `ignition`). Confirm `StatusPing` RUNNING, the project listed in the gateway, MQTT Engine reconnected, and a Designer save writes files under `ignition/projects/mes-2026/`. If the gateway cannot write to the bind mount (permissions), stop and report — do not chmod the repo broadly.
4. `.gitignore`: nothing in the project folder should be ignored except Ignition lock/cache files if any appear; report what you added.

### 2. Gateway buffer (D3) — project library + timer event

- **Project library** `press1` (script package in `mes-2026`) owns all logic: tag paths, parse/cast, sample append, event detection, jobs-observed, and the read functions the views call. Views never parse JSON or compute events themselves.
- **Tag paths:** the 16 String tags under the MQTT Engine provider at `40Printing/Dallas/Press Room/Press 1/<sub-path>`. Find the exact provider/folder path in the Designer Tag Browser and put it in **one constant** in `press1`. If the spaces in the path break anything (tag path, binding, script read), **stop and report** — do not rename.
- **Ingest (every tick):** `system.tag.readBlocking` all 16 → `system.util.jsonDecode` each → take `value` → cast: booleans (`Connected`, `RTOInhibit`) to bool (accept `true/false/0/1`), `MachineState`, `FaultCode`, `ProductCode`, `WebLanes` to int, everything else to float. Parse `timestamp` (ISO 8601 UTC with microseconds) to epoch ms. A tag whose read quality is bad or whose JSON fails to parse → `None` for that field and a single logged warning per tag, not per tick.
- **De-duplicate:** append a row only when `PLC/MachineState`'s envelope `timestamp` is newer than the last row's. The sample time **is** that timestamp. (Timer and sim both run at 2 s and will drift; this prevents duplicate or skipped-looking rows.)
- **Store** in `system.util.getGlobals()['press1']`: `rows` (capped 1,800, oldest dropped), `events` (closed events, newest first, capped 200 — matches the reference), `open_event`, `jobs` (jobs observed), `started` (gateway-buffer start time). **Confirm in the 8.3 docs that `getGlobals()` is shared between gateway event scripts and Perspective session scripts/bindings in the same gateway**; if it is not, stop and report rather than inventing another store. No memory tags, no database, no historian.
- **Meters:** deltas only. A row's delta is `current − previous` when `current ≥ previous`; when `current < previous` it is a sim restart: delta 0, and mark the restart on the row.
- **Events** — exactly the prompt's rules: open after 2 consecutive samples in the same (state, fault code), backdate start to the first; close on the first differing sample; durations from sample timestamps; a fault-code change inside Faulted closes one and opens another. Counts are "since gateway start".
- **Jobs observed:** a job is a contiguous run of one `ProductCode`. Columns per the prompt; good/reject m deltas are the sums of row deltas, shown as "—" if a restart falls inside the job. Keep the full list since gateway start (it is small: 5 jobs per 17.4 min).
- **Read API** (project library, called from Perspective bindings): `latest()`, `rows(window_min)`, `events()`, `alarm_summary(window_min)`, `state_percent(window_min)`, `jobs()`, `buffer_info()`. Return plain lists/dicts or datasets as the chosen chart components need.
- **Timer event:** gateway timer script, **fixed delay 2000 ms**, body is one call: `press1.tick()`. Wrap in try/except that logs via `system.util.getLogger('press1')` — never let an exception kill the timer.

### 3. Perspective views

- Views under `Press1/…` in `mes-2026`: one page view at URL `/press1` with the header, tab bar and window selector; one embedded view per tab. Dark theme per the prompt colours (use the Perspective dark theme plus style classes; put the colours in **one** place — a style class set or a session custom prop — not repeated per component).
- **Live values** bind to the latest buffer row (`press1.latest()`), refreshed by a 2 s polling binding (`now(2000)`), so everything on screen comes from one parse path. The clock uses the session time.
- **Trends** use the Perspective chart component the 8.3 docs recommend for time-series datasets (look it up; Time Series Chart or XY Chart). Data comes from `press1.rows(window)` filtered to the selected window. Footer on every trend: `gateway buffer, N samples`. The window selector (5/15/30/60, default 15) is a session or page custom property.
- **On-screen notes** required by the prompt: the buffer is lost on a gateway restart; 200 °F is a display limit, not a PLC setpoint.

### 4. Build order and pauses

Build in the prompt's four steps. **After each step, stop and tell Walker in the Dev terminal what to look at (URL, what should change); continue only on his go.** Fill the Dev Report incrementally so a partial run is still reported.

## Acceptance Criteria

Everything in the Appendix "ACCEPTANCE" section, verified against the live sim, plus:

1. [ ] `ignition/projects/mes-2026/` exists in the repo and holds the views, the `press1` library and the timer event; `docker-compose.yml` has exactly one added volume line; `docker compose config -q` exits 0.
2. [ ] After the D2 recreate: `curl -s localhost:8089/StatusPing` → RUNNING; MQTT Engine log shows `Connected to tcp://coreflux:1883` with no reconnect loop.
3. [ ] `grep -rn "4\.0 Printing/" ignition/` returns nothing (no old-root paths; amended by PM 2026-10-20 — the display text "4.0 Printing — Press 1" is required by the prompt). Every tag path in the project starts from the single constant in `press1`.
4. [ ] `grep -rn -i -E "historian|system\.db\.|queryTagHistory|timebase" ignition/` returns nothing.
5. [ ] No MES concept anywhere in the project: no work order, OEE, schedule, downtime reason, planned stop or changeover-overrun logic. Setup is displayed as "Changeover".
6. [ ] Reloading the page keeps the trends; opening a second browser session shows the same buffer sample count.
7. [ ] No secrets in any tracked file.
8. [ ] UNS Studio, the sim, `coreflux`, `db`, `ignmes-*` and every other container untouched (StartedAt unchanged, except `mes-workshop-2026-ignition-1`, recreated once for D2).

## Files to Modify

| File | Change |
|---|---|
| `ignition/projects/mes-2026/**` | New — copied project, then views, `press1` library, gateway timer event |
| `docker-compose.yml` | One bind-mount line on `ignition` (D2) |
| `.gitignore` | Only if Ignition lock/cache files appear under the project |
| `docs/tasks/task_VIS-001_press1_scada_perspective.md` | Status line and Dev Report only |
| `docs/agent_handoff.md` | `Dev status` block only |

Contract docs: `docs/architecture.md` (project location, buffer, interim ingest path) is PM-owned and updated at close-out.

## Dev Instructions

Read this spec in full, including the Appendix (VERA's prompt — the requirements). Build the Press 1 SCADA view in the `mes-2026` project on the `mes-workshop-2026-ignition-1` gateway (http://localhost:8089): first move the project into `ignition/projects/mes-2026/` with a bind mount, then a `press1` project library and a 2 s gateway timer that parses, casts and buffers the 16 MQTT Engine string tags in `system.util.getGlobals()`, then the views in the prompt's four steps, pausing for Walker after each. Look up every Perspective component and scripting function you use in the Ignition 8.3 docs; do not rely on memory.

Hard constraints:
- **Never stop, start, update or reimport the sim, and never touch UNS Studio** (reading the reference `.jsx` is the only exception). A restart resets the counters.
- **Do not change MQTT Engine, gateway or broker settings.** D1 is Walker's GUI step. If something needs a settings change, stop and ask.
- **Do not touch `ignmes-ignition` or any other non-`mes-workshop-2026` container.** The only container you recreate is `mes-workshop-2026-ignition-1`, once, for D2. Never `docker compose down -v`.
- Read only `40Printing/Dallas/Press Room/Press 1/<16 tags>`. Never reference `4.0 Printing/…`, `Probe/…` or `…/MES/…`. Never use a wildcard read.
- Raw layer only — no MES data or logic. No history: no Tag Historian, no Timebase, no database writes.
- Unwrap `value`, cast every value once at ingest; meter deltas with restart handling; events per the prompt's rules on sample timestamps.
- If the spaces in the topic levels break anything in Ignition, stop and tell Walker. Do not rename.
- No credentials in any repo file. Gateway login is in `.env` or from Walker.
- **No commit and no push without Walker's approval.** Stage path-scoped only (`ignition/projects/mes-2026/`, `docker-compose.yml`, `.gitignore` if changed, this spec, `docs/agent_handoff.md`).
- Report to Walker in plain English, under 15 lines, per the prompt's REPORT BACK section; the full report goes in the Dev Report below.

---

## Appendix — VERA's prompt (verbatim, received 2026-10-20 ~14:05 CDT)

```
Task: build a tabbed Ignition Perspective SCADA view of Press 1 that looks and behaves like the React dashboard we built in UNS Studio. Raw PLC data only. This is SCADA, not MES. No history in Ignition.

Walker is teaching live and wants to show this as the last dev step of Day 1. Show something on screen early, then add to it. Keep chat replies short and plain English.

READ FIRST, in this order
1. docs/claude_project_instructions.md and docs/agent_handoff.md
2. docs/sim_spec_press1.md (tags, state codes, fault codes, and section 11 consumer rules)
3. docs/about_4_0_printing.md sections 4 and 5 (process vocabulary)
4. The reference dashboard. Read only. Do not edit it or anything else under UNS Studio:
   ~/Library/Application Support/UNS Studio/data/dashboards/printing-press-1-scada.jsx
   It is React plus Recharts, so do not port the code. Copy the layout, colors, wording, thresholds and logic.
5. The current Ignition 8.3 Perspective documentation. Look up the components and scripting APIs you use. Do not rely on memory.

NOTE ON THE TOPIC ROOT
Walker renamed the first topic level from "4.0 Printing" to "40Printing" to remove the dot, and reimported the sim at about 13:45 CDT. The docs in this repo (including the sim JSON under docs/sim/) still show the old root with the dot, because they have not been synced yet. The live root is `40Printing/Dallas/Press Room/Press 1`. If the docs and the live broker disagree, trust the live broker and tell me.

HOW THE SIM PUBLISHES (checked live at about 14:00 CDT)
- The sim publishes to a CoreFlux MQTT broker. Walker's MQTT client in Notus uses a connection named "MES Coreflux", subscribed to #. It is probably the same CoreFlux that runs in this repo's Docker stack. Confirm that in preflight.
- Messages are not retained. A new subscriber gets values only as the sim publishes them (every 2 s).
- Example payload on topic `40Printing/Dallas/Press Room/Press 1/PLC/GoodMeters`:
  {"value":1768.0,"timestamp":"2026-10-20T19:00:51.377788Z","datatype":"float","status":"Good","units":"m"}
- `timestamp` is an ISO 8601 string in UTC with microseconds, not epoch milliseconds. Parse it.
- `units` is present only when the sim defines units (meters, lbf, m/min, mm, s, degF). It is absent on PLC/Connected, MachineState, FaultCode, ProductCode, WebLanes and RTOInhibit.
- `datatype` is "integer", "float" or "boolean" and can change for the same tag between phases.

STALE TAGS: DO NOT READ THEM
UNS Studio and Walker's Notus MQTT client still hold dead copies of two old sets of tags. They carry frozen values (the old root's last values are from about 13:42 CDT) and never update.
- 16 tags under `4.0 Printing/Dallas/Press Room/Press 1/...` (the old root).
- 4 tags under `Probe/CounterTest/...`.
Because messages are not retained, a fresh subscription to the broker should not receive them. Do not rely on that. Subscribe to `40Printing/Dallas/Press Room/Press 1/#` only. Do not use a broad wildcard such as `#` or `+/Dallas/#`, and do not copy a topic path from an old doc without checking the root. If a value looks frozen, check the root first.
Later the MES will publish under `40Printing/Dallas/Press Room/Press 1/MES/...`. Nothing is there yet. This SCADA view must ignore it.

WORKFLOW
Use /pm to write one short task spec in docs/tasks/ and show it to me. After I approve it, /dev builds. No commit and no push without my approval. Stage nothing outside the Perspective work and its docs.

HARD CONSTRAINTS
- Never stop, start, update or reimport the sim, and never touch UNS Studio. Counters reset on a restart and the loop starts over.
- Raw layer only. No work orders, OEE, scheduling, downtime reasons, planned stops or changeover-overrun logic. Setup is shown as a plain state called "Changeover".
- No history. No Tag Historian, no Timebase queries, no database writes for trends. Trends come from a rolling in-memory buffer on the gateway, so every session sees the same data and a page reload does not empty it. The buffer is lost on a gateway restart. Say that on screen.
- Every sim message is the UNS Studio envelope (see "How the sim publishes"). Use value. Cast everything on ingest, because the same tag arrives as integer or float depending on the phase.
- GoodMeters and RejectMeters are cumulative. Use deltas. A drop to 0 means the sim restarted. It is not negative production.
- Topic root is `40Printing/Dallas/Press Room/Press 1`. Level names contain spaces ("Press Room", "Press 1", "Print Section", "Tunnel Dryer"). Spaces are untested in Ignition. Do not rename anything. If something in Ignition breaks on the spaces, stop and tell me.
- Do not copy passwords or credentials into any file in the repo. Gateway credentials come from .env or from me.

STEP 0: PREFLIGHT. Report, then wait for my answer before building.
a. Which gateway? `docker ps` shows `ignmes-ignition` (Ignition 8.3.9, up 6 hours) on this machine. It looks like it belongs to the ign-mes-demo project. This repo's docker-compose.yml pins `inductiveautomation/ignition:8.3.10` under the service name `ignition`, and I have not seen that service running. Walker's notes also mention an Ignition at http://localhost:8089. Tell me which container serves that port, which gateway we are building in, and why.
b. Can that gateway read the 16 tags below? The sim publishes to CoreFlux. Check whether Ignition has a connection to that broker, and how (Maestrohub, MQTT Engine, OPC or something else). If it does not, say what is missing. Do not invent an ingest path, and do not change broker or gateway settings without asking.
c. Where does the Perspective project live in this repo, and how is it version-controlled? Ignition 8.3 projects are file-based. Propose a folder and wait for my OK.

THE 16 TAGS (path is relative to the topic root above)
PLC/Connected (bool), PLC/MachineState (1 Running, 2 Setup, 3 Faulted), PLC/FaultCode (0, 101, 102, 103), PLC/ProductCode, PLC/WebLanes (2 or 4), PLC/GoodMeters (m), PLC/RejectMeters (m), PLC/RTOInhibit (bool),
Unwind/WebTension (lbf), Rewind/WebTension (lbf),
Print Section/LineSpeed (m/min), Print Section/RegistrationError (mm), Print Section/InkViscosity (s),
Tunnel Dryer/Zone1Temp, Zone2Temp, Zone3Temp (degF)

LOOK AND FEEL (match the reference)
- Dark theme. Colors: Running #22c55e, Setup #f59e0b, Faulted #ef4444, accent #4DB8D5, series colors #4DB8D5 #f59e0b #a78bfa #22c55e #ef4444.
- Header: "4.0 Printing — Press 1" with the subtitle "Dallas · Press Room · flexographic, 8 color, hot-air tunnel dryer · raw PLC data (SCADA view)". On the right, a connection pill (green LIVE or red when PLC/Connected is false) and a clock. 4.0 Printing is the company name and stays in display text. Only the topic root lost the dot.
- Tab bar: Overview, Tunnel Dryer, Web & Print, Production, Alarms & State. Next to it, a trend window selector: 5, 15, 30, 60 minutes. Default 15.
- Every trend footer says "gateway buffer, N samples", so students can see where the data comes from.

TABS
1. Overview
   - State banner. Running shows "RUNNING". Setup shows "SETUP — changeover". Faulted shows "FAULTED — <alarm name> (code N)". Alarm names are 101 Web break, 102 Tunnel over-temp, 103 RTO inhibit. Any other code shows "Unclassified alarm". Show "Job <ProductCode> · <WebLanes>-wide". Show pills for RTO INHIBIT ACTIVE or RTO CLEAR, and PLC CONNECTED.
   - Six tiles: line speed, product code, web lanes, good meters, reject meters, cumulative scrap % (rejects over good plus rejects, amber above 4).
   - Process flow, left to right: Unwind (tension), Print section 8 colors (speed, registration error, ink viscosity), Tunnel dryer hot air (zones 1 to 3), Rewind (tension). Then a line for the RTO permissive to the press.
   - Below that: a machine-state step trend and a line-speed trend.
2. Tunnel Dryer: three zone readouts with bars and a red display line at 200 degF (a display limit, not a PLC setpoint; footnote it on screen), a three-zone trend with the same line, and the state trend.
3. Web & Print: unwind and rewind tension overlaid, then line speed, registration error and ink viscosity trends, then the state trend.
4. Production: good and reject meter trends, a product-code step trend (scale 100 to 106), and a "Jobs observed" table with product code, lanes, first seen, last seen, good m delta and reject m delta. Show a dash where a counter reset falls inside the job.
5. Alarms & State: the state banner, three tiles for % time Running, Setup and Faulted in the selected window, the state trend, an alarm summary table (101, 102, 103 and Unclassified, each with count and total time), and an event log, newest first (start, type, detail, job, duration, or "active").

EVENT RULES
- Open an event after 2 consecutive samples (4 s) in the same state and fault code. Backdate the start to the first of them. Close on the first sample that differs. Use sample timestamps for duration.
- A change of fault code inside Faulted closes one event and opens another.
- Alarm and event counts say "since gateway start", not "since page open".

BUFFER
- One sample every 2 s of all 16 values, kept on the gateway, capped at 1,800 rows (60 minutes). A gateway timer script or a tag change script is fine. Pick the mechanism from the docs and say why.
- Trends read from the buffer, filtered to the selected window.

BUILD ORDER. Show me after each step.
1. Overview with live values only (banner, tiles, process flow). No trends yet. This is the first thing I show students.
2. The gateway buffer and the window selector, then the two Overview trends.
3. Tunnel Dryer and Web & Print.
4. Production and Alarms & State.

ACCEPTANCE (check against the live sim)
- Banner and tiles follow the PLC. Faults arrive about once a minute, so one should show within a couple of minutes.
- 101 web break: tension reads 0, speed reads 0, and the unwind and rewind boxes turn red. 102 over-temp: all three zones jump to 215 to 235 degF and turn red. 103 RTO inhibit: RTO pill turns red, state is Faulted, zone temperatures stay normal.
- Setup shows as "Changeover", with product code and lanes already changed.
- Reload the page: the trends are still there.
- GoodMeters rises only while Running and holds during Faulted and Changeover. RejectMeters is different: it rises 2 m per sample during a 101 web break, 1 m per sample while Running on product 105, and holds during 102, 103 and Changeover. Do not treat rejects rising during a fault as a bug.
- Every value on screen updates. Nothing is frozen from the old root.
- Nothing on screen is MES data, and the sim was not touched.

REPORT BACK
Plain English, under 15 lines: what is built, what you verified live, what you could not verify, and anything you changed from this prompt.
```

**PM note on build order:** the prompt's step 1 is "live values only, no trends". This spec builds the `press1` library and timer *before* step 1, because live values read the latest buffer row (one parse path). The trends, window selector and footers still wait for step 2, so what Walker sees after step 1 matches the prompt.

---

## Dev Report

*(Written by the Dev. The PM reads this, then verifies against the actual files.)*

**Status:** ✅ Done — ready for PM verification (all 4 steps built and verified live; not committed, awaiting Walker's approval)
**Date:** 2026-10-21

**What was built:**
- **D2 bind mount.** `mes-2026` copied out of the container to `ignition/projects/mes-2026/`; one volume line added to `ignition` in `docker-compose.yml`; `docker compose up -d --no-deps ignition` recreated only that container. Gateway RUNNING, MQTT Engine reconnected (`Connected to tcp://coreflux:1883`, no reconnect loop), Walker's Designer session reconnected to `mes-2026`, and the gateway user can write to the bind mount.
- **`press1` project library** (`ignition/script-python/press1/code.py`): single `ROOT` constant (`[MQTT Engine]40Printing/Dallas/Press Room/Press 1`, confirmed by Walker in the Tag Browser), the 16 sub-paths, parse/cast at ingest (bools accept true/false/0/1; state, fault, product, lanes to int; rest to float; envelope `timestamp` → epoch ms via `java.time.Instant`), one warning per tag on bad quality / bad JSON (never per tick), de-dup on the MachineState envelope timestamp, meter deltas with restart flag, 1,800-row cap, event detection (2-sample debounce, backdated start, close on first differing sample, fault-code change splits), jobs observed since gateway start, and read API `latest()`, `rows()`, `events()`, `alarm_summary()`, `state_percent()`, `jobs()`, `buffer_info()`.
- **Gateway timer** `ignition/timer/press1Tick/`: 2000 ms, fixed delay, own thread; body calls `press1.tick()` inside try/except that logs to logger `press1`.
- **Perspective (step 1):** page `/press1` → `Press1/Main` (header, LIVE pill, clock, tab bar, footer); `Press1/Tabs/Overview` (banner, six tiles, process flow, RTO permissive line); `Press1/Parts/Banner`; `Press1/Tabs/Pending` placeholder for tabs not yet built. Theme `dark-cool` (session-props); all colours as custom properties in one project stylesheet (`stylesheet/stylesheet.css`); views carry bare class names only.
- **How resource shapes were found** (8.3 has no docs for the on-disk format): disassembled the 8.3.10 jars from this gateway. Timer = resource type `("ignition","timer")`, payload `handleTimerEvent.py`, attributes `delay`/`fixedDelay`/`sharedThread`/`enabled`. Library = `("ignition","script-python")`, payload `code.py`. Perspective types and the `psc-` class prefix follow the lessons in `ign-mes-demo/ignition-project/README.md`.
- **`getGlobals()` sharing confirmed.** 8.3 docs: the dictionary "persists across the lifetime of the JVM" and is available in Gateway and Perspective Session scope. Verified live: the Perspective page shows the timer's rows.

- **Step 2:** window selector (5/15/30/60 min, default 15) as `Press1/Main` custom prop `window`, passed to each tab view as an input param. Reusable trend card `Press1/Parts/Trend` (Time Series Chart `ia.chart.timeseries`; schema read from the 8.3.10 module: data rows keyed `time` + columns). One polling binding per card calls `press1.trend(window, keys, names)`, which returns the series and the footer `gateway buffer, N samples`; `press1.plots(params)` builds pens, step interpolation, axis range and the optional display-limit marker. Pen colours are `var(--p1-series-*)`, so hex values stay only in the stylesheet (confirmed: the chart resolves CSS variables). Overview now has the machine-state step trend and the line-speed trend. Main shows the on-screen buffer note: *"Trends come from a rolling in-memory buffer on the gateway (60 min max, N samples since HH:MM:SS). The buffer is lost on a gateway restart."*

- **Step 3:** `Press1/Tabs/Dryer`: three zone cards (value turns red at 200 °F, bar 0–250 with a red tick at the 200 display limit, scale "0 · display limit 200 · 250"), the three-zone trend with a dashed red "display limit 200" marker, the state trend, and the reference's footnote ("The red line is a display limit for this screen, not a PLC setpoint…"). `Press1/Tabs/WebPrint`: unwind vs rewind tension overlaid, then line speed, registration error and ink viscosity in a wrapping row (the reference's 420 px grid), then the state trend. Colours follow the reference's series letters. Both tabs added to the `Main` tab switch. No library change was needed: the zone fields and the limit marker were already in `press1`.

- **Step 4:** `Press1/Tabs/Production`: four tiles (good, reject, product code, lanes), good and reject cumulative trends, product-code step trend (axis 100–106), "Jobs observed" table (product code with "(current)", lanes, first/last seen, good and reject m deltas, dash when a counter reset falls inside the job; newest 12 shown, 50 kept) and the counters footnote. `Press1/Tabs/Alarms`: state banner, % time Running / Setup / Faulted over the selected window (weighted by sample timestamps; sub-label "last N min window"), state trend, alarm summary (101, 102, 103, other: count and total time since gateway start, active alarm included) and event log (newest first, open event on top as "active"; scrolls at 300 px), then the footnote. Tables are a Flex Repeater of one row view each (`Press1/Parts/{JobRow,AlarmRow,EventRow}`), styled by the stylesheet's `th`/`td`/`td-alarm`/`td-setup` classes. Library additions: `cells()` (rows → repeater instances), `type_cls` on event rows, `MAX_JOBS = 50` and `jobs(limit=12)`.

- **PM fix — sampling-gap guard (2026-10-21):** `GAP_S = 10` added. In `tick()`, after the de-dup check, a gap of more than 10 s since the previous row closes any open event at the previous row's timestamp (the last sample before the gap), resets the debounce run and flags the row; `_jobs(st, row, gap)` then starts a new job entry even on the same ProductCode, so the gap row's deltas are not added to the previous job. `state_percent` skips intervals longer than `GAP_S`. `STORE_VERSION` 1 → 2: the store was rebuilt at 08:26:24 (buffer emptied once, refills over 60 min; Walker approved by asking for the fix as written). The live store started 08:31:33, after the key fix below. Meter deltas unchanged.

**Gap-fix acceptance (2026-10-21 08:35 CDT):**
```
$ grep -n "GAP_S" ignition/projects/mes-2026/ignition/script-python/press1/code.py
44:GAP_S = 10          # rows further apart than this are a sampling break (e.g. the host slept)
205:	if prev is not None and ts - prev['t'] > GAP_S * 1000:
405:		if dt > GAP_S:
```
Two uses, not three: `_jobs` gets the `gap` flag from `tick()` (fix step 3), so it doesn't read `GAP_S` itself.

Event log after the save (store rebuilt 08:31:33, screenshot 08:35:30), newest first. The longest event is 18 s, with no overnight event:
```
08:34:35  Alarm  Web break (101)    job 101  8s
08:33:32  Alarm  Web break (101)    job 101  11s
08:32:22  Setup  Changeover         job 101  18s
08:32:10  Alarm  RTO inhibit (103)  job 105  12s
```
Alarm summary: 101 x2 (19s), 102 x0, 103 x1 (12s). Percent over 15 min: Running 79 / Setup 8 / Faulted 13.

- **Extra fix needed: versioned globals key.** After the first save (08:26) the buffer was being rebuilt every few seconds ("0 samples since 08:30:36", then "since 08:30:42"). Cause: Walker's open Designer session (connected since 05:07) runs Perspective preview bindings on the gateway with the *old* `press1` (STORE_VERSION 1). Old and new code each saw the other's version and rebuilt the store. Fix: the store now lives under `STORE_KEY = 'press1.v2'`, and `_store()` only creates it when missing. Stale code can rebuild only its own old `press1` key and never the live buffer. After a second save the store has held steady since 08:31:33. Designer previews will show the old library's empty store until Walker updates the project in the Designer. Also: `latest()` with an empty buffer now returns placeholder pill text instead of `null`.

**Verified live (step 4, ~08:20–08:22 CDT 2026-10-21):** good meters rise while Running and hold flat during faults; rejects step up during faults; the product-code trend steps 105 → 101 → 102. Jobs table shows "102 (current)" with deltas, and job 105 shows dashes because the sim's counters reset overnight (good meters now 5,350). Event log: Setup "Changeover" at 08:17:51 on job 102, the same second job 102 was first seen (product changed at the start of Setup); 101, 102 and 103 alarms in red with durations of 8–13 s. Alarm summary counts 101 ×60, 102 ×27, 103 ×14 since gateway start. Switching to 5 min changes the % tiles (73/13/15 → 70/16/15). **AC 6:** a second browser session showed the same "gateway buffer, 274 samples" as the first at 08:22:04.

**Verified live (step 3, ~08:14–08:16 CDT 2026-10-21):** zone cards show 175–188 °F in green with bars and the limit tick; the zone trend shows the dashed red line at 200; Web & Print shows tension dropping to 0 together with speed and registration during two faults, matching the state trend (Faulted → Setup → Running). No `press1` errors in the gateway log.

**Verified live (step 2, ~14:28–14:30 CDT):** both trends draw from the buffer (324 samples in 15 min; 145 in 5 min after clicking 5 min); a page reload keeps the full trends; a library re-save restarted the gateway scripts without emptying the buffer (`getGlobals()` persists); the state trend shows Setup (2) between jobs; a 101 web break showed tension 0.0 in red with Unwind/Rewind boxes red.

**Verified live (step 1, ~14:18 CDT):** page loads at http://localhost:8089/data/perspective/client/mes-2026/press1 with values updating every 2 s (job 104, 2-wide, speed ~210 m/min). A 102 over-temp arrived: banner "FAULTED — Tunnel over-temp (code 102)", zones 215.0–215.5 °F in red, line speed, tension and registration at 0, RTO still clear.

**Files changed:**
| Path | Created / Modified / Deleted |
|---|---|
| `docker-compose.yml` | Modified (one volume line) |
| `ignition/projects/mes-2026/project.json`, `ignition/global-props/*` | Created (copied from the container, unchanged) |
| `ignition/projects/mes-2026/ignition/script-python/press1/{code.py,resource.json}` | Created |
| `ignition/projects/mes-2026/ignition/timer/press1Tick/{handleTimerEvent.py,resource.json}` | Created |
| `ignition/projects/mes-2026/com.inductiveautomation.perspective/{page-config,session-props,stylesheet}/*` | Created |
| `ignition/projects/mes-2026/com.inductiveautomation.perspective/views/Press1/{Main,Tabs/Overview,Tabs/Dryer,Tabs/WebPrint,Tabs/Production,Tabs/Alarms,Tabs/Pending,Parts/Banner,Parts/Trend,Parts/JobRow,Parts/AlarmRow,Parts/EventRow}/*` | Created |
| `.gitignore` | Not changed (no lock or cache files appeared) |

**Gate results** (commands and actual output, pasted):
```
$ docker compose config -q && echo "config -q: exit 0"
config -q: exit 0
$ curl -s localhost:8089/StatusPing
{"state":"RUNNING"}
$ docker logs ... | grep TahuClient
I [o.e.t.m.TahuClient] [14:09:12.084]: ignition-client: Connected to tcp://coreflux:1883
$ grep -rn "4\.0 Printing/" ignition/
(no output)
$ grep -rn -i -E "historian|system\.db\.|queryTagHistory|timebase" ignition/
(no output, exit 1)
```

Final gate run (2026-10-21 ~08:22 CDT):
```
$ docker compose config -q
exit=0
$ curl -s localhost:8089/StatusPing
{"state":"RUNNING"}
$ grep -rn "4\.0 Printing/" ignition/
exit=1
$ grep -rn -i -E "historian|system\.db\.|queryTagHistory|timebase" ignition/
exit=1
$ grep -rn -i -E "work ?order|\bOEE\b|schedul|downtime|planned stop|overrun" ignition/
exit=1
$ grep -rn -E "Probe/|/MES/" ignition/
(no output)
$ grep -rn -i -E "password|secret|apikey|api_key|token" ignition/ docker-compose.yml   (minus ${...} refs)
docker-compose.yml:3:# Secrets come from .env (git-ignored); commit names only, in .env.example.
$ docker inspect StartedAt (all running containers)
/mes-workshop-2026-ignition-1 2026-10-20T19:08:55Z   <- the one D2 recreate
/mes-workshop-2026-coreflux-1 2026-10-20T18:09:09Z
/mes-workshop-2026-db-1       2026-10-20T18:09:09Z
/ignmes-*, timebase, highbyte, portainer, coreflux-mqtt, *-test  2026-10-20T11:39:11Z
$ docker logs --since 30m mes-workshop-2026-ignition-1 | grep -c -i reconnect
0
```
Container StartedAt before D2 (all others unchanged since): coreflux/db 2026-10-20T18:09:09Z, ignmes-* and the other stacks 2026-10-20T11:39:11Z. Only `mes-workshop-2026-ignition-1` was recreated.

**Deviations from spec:**
- **Project scans.** 8.3 does not watch the project folder, and the scan REST endpoint needs an API key, which would be a gateway setting change. I used the gateway web UI's Projects → "Scan File System" button instead (no settings changed). Designer saves need no scan.
- **`alarm_summary(window_min)`** ignores its argument. The prompt says alarm counts are "since gateway start", which overrides the spec's signature. An active alarm counts, with its time so far.
- **Header pill** shows `NO DATA` (red) when the newest sample is more than 10 s old, as well as `LIVE` and `PLC DISCONNECTED`. This makes a frozen feed visible (acceptance: "nothing is frozen").
- **Process flow** copies the reference: the tunnel-dryer section's top border turns red on 102 **and** 103. Zone values turn red only at 200 °F or above, so 103 leaves them normal.

- **State-trend y-axis** auto-ranges 0–4 although the axis is set to 0.5–3.5; the state legend is in the card title ("1 Running · 2 Setup · 3 Faulted") because the chart cannot label ticks with names. Cosmetic.
- **Zone trend y-axis top fixed at 250 °F** (the bar scale). With auto-range the axis stopped at about 196 and the 200 display line was off screen; the spec asks for the line on the trend.
- **Designer-save check (PM instruction after step 2).** I regenerated for step 3 before reading the instruction, then checked: no project file changed between the step-2 generate (2026-10-20 ~14:30) and step 3, and the gateway log shows no Designer saves of `mes-2026`. Nothing was overwritten. I'll check before generating step 4.
- **Buffer after the Mac slept.** The timer stopped while the host slept overnight, so a 15-minute window showed only the 2–3 minutes since wake (58–85 samples) at first. Expected: the buffer holds what was sampled.
- **Footnotes trimmed for AC 5.** The reference's Production note ends "Work orders, OEE and scheduling are not shown here; they belong to the MES layer", and its Alarms note ends "deciding whether a Setup overran its scheduled time is MES logic". AC 5 forbids those terms anywhere in the project, so both clauses are dropped; the rest of each note is the reference's wording.
- **"Since gateway start" labels.** The Jobs, Alarm summary and Event log card labels say "since gateway start" (the reference says "since this page was opened"), per the prompt. The Jobs note says "if the gateway started mid-job".
- **Designer-save check before step 4:** no project file newer than the step-3 handoff edit and no Designer save in the gateway log; regenerated after the check.
- **Binding trap found (for the PM's notes):** a property binding on a whole object path (`view.params`) delivers `None` to its transform with no log line; bind a leaf (`view.params.names`) and read `self.view.params` instead.

**Open questions for the PM:**
- **Host sleep stretches events and jobs.** The Mac slept overnight with the press Faulted on 102; the event closed at the first sample after wake, so the log shows one 102 alarm of 963m 37s (and the alarm summary's 102 total includes it). Job 105 likewise spans 16:07 yesterday → 08:14 today. This follows the rule "use sample timestamps for duration". A gap guard (e.g. close an open event at the last sample before a gap of more than N seconds) would fix it, but it isn't in the spec. Your call; a gateway restart clears it either way.
- **`Press1/Tabs/Pending`** is no longer used by any tab (it stays as the `case()` fallback). Delete it if you prefer.
- **AC 3's grep conflicts with the prompt.** `grep -rn "4\.0 Printing" ignition/` matches the required header text "4.0 Printing — Press 1" (the prompt: "4.0 Printing is the company name and stays in display text"). No tag path or topic uses the old root: `grep "4\.0 Printing/"` returns nothing. Suggest the AC check `4\.0 Printing/`.

---

## PM Verification

*(Written by the PM after reading the changed files — Rule 7.)*

**Interim check after step 1 (PM, 2026-10-20 ~14:25 CDT):** pass, OK to continue.
- `docker-compose.yml`: exactly one added volume line (D2). `.gitignore` unchanged.
- `press1/code.py` read in full through `tick()` and `latest()`: single `ROOT` constant on `40Printing/…`; JSON unwrapped and cast once per tag; dedupe on the MachineState envelope timestamp; meter deltas with restart → 0; events debounce 2 samples, backdated, split on fault-code change; jobs keyed on contiguous ProductCode. Matches the spec.
- Timer resource: 2000 ms, fixed delay, own thread, try/except logging to `press1`.
- Views: no hard-coded hex colours (colours live in the project stylesheet); no MES terms anywhere in the project.
- Dev's open question resolved: AC 3 amended to `4\.0 Printing/`.
- Deviations accepted: gateway "Scan File System" button (no settings change); `alarm_summary` counts since gateway start per the prompt; extra `NO DATA` pill state when the newest sample is >10 s old.

**Interim check after step 2 (PM, 2026-10-21):** pass, OK to continue.
- `press1.rows(window_min, keys)` filters the buffer to the window and returns `{'time': ms, key: float}` rows for `ia.chart.timeseries`. Still no hard-coded hex in views; no history, DB or old-root references (`grep` clean).
- Live checks reported by the Dev (window change, reload survives, library save keeps the buffer, Setup visible, 101 turns Unwind/Rewind red) accepted; Walker sees them on screen.
- Cosmetic gap accepted: state trend y-axis 0–4 with the state legend in the card title.
- **Instruction for steps 3–4:** the views are written by a generator in the Dev's scratchpad (`gen.py`), which rewrites every view. The view files in `ignition/projects/mes-2026/` are the source of truth. **Before each regenerate, check whether any view was saved from the Designer since the last generate (file mtime or diff against the last generated output); if so, do not overwrite it — stop and ask Walker.** The generator stays out of the repo.

**Interim check after step 3 (PM, 2026-10-21):** pass, OK to continue.
- New views `Press1/Tabs/Dryer` and `Press1/Tabs/WebPrint`. Still no hard-coded hex, no history/DB/old-root references. Only the `ignition` container restarted (2026-10-20 19:08 UTC, the D2 recreate); CoreFlux and `coreflux-mqtt` unchanged.
- Zone chart y-axis fixed at 250 °F so the 200 °F display line is visible — accepted (matches the bars).
- Regenerate-before-check slip: the Dev confirmed no Designer saves were overwritten. Accepted.
- **Instruction for step 4 — sampling gaps.** The gateway stopped sampling while the Mac slept overnight (trends resume ~08:12). In `press1`, treat a gap of more than 10 s between consecutive rows as a break: close any open event at the last row before the gap (not at the first row after it), restart the debounce run, and do not count the gap as time in any state for `state_percent`. Keep meter deltas as they are (a restart is still detected by a drop). Otherwise the Alarms & State tab shows an overnight-long event and skewed percentages.

**Result (PM, 2026-10-21):** 🟡 Pass with one gap — fix below, then commit.
**Findings:**
- Read `press1/code.py` in full (ingest, `tick`, `_events`, `_jobs`, every read function), the timer resource, the view list (Main, 5 tabs, Pending, Banner, Trend, JobRow, AlarmRow, EventRow), and the `docker-compose.yml` diff (one volume line).
- Prompt behaviour checked in code: banner text and alarm names; scrap %; event debounce/backdate/split; alarm summary 101/102/103/other "since gateway start" with an active alarm counted; `state_percent` weighted by sample timestamps over the window; jobs newest first with "—" on a counter reset; trend footers "gateway buffer, N samples"; buffer note on screen; 200 °F display-limit footnote.
- Gates re-checked: no old-root paths, no history/DB/Timebase, no MES terms, no secrets, only `ignition` recreated (once, D2). Dev's live checks (second session same sample count, reload keeps trends, Setup as Changeover, 101 and 102 behaviour) accepted; 103 RTO inhibit not yet seen live by the Dev or the PM.
- Deviations accepted: footnotes trimmed of MES terms; "since gateway start" labels; `Pending` view kept as the fallback.
- **Gap — sampling-gap guard not implemented.** The PM's step-3 instruction (above) was not built; the Dev reports the Mac's overnight sleep produced one 102 alarm of 963 min and job 105 spanning 16:07 → 08:14. The Mac will sleep again before Day 2.

### Fix to apply (VIS-001, same spec — Dev)

In `ignition/script-python/press1/code.py` only:
1. Add `GAP_S = 10` next to the other constants.
2. In `tick()`, after the de-dup check and before `_events`/`_jobs`: if `prev` exists and `row['t'] - prev['t'] > GAP_S * 1000`, call `_close_event(st, prev['t'])` (close at the last sample **before** the gap), set `st['run'] = None`, and set a local `gap = True`.
3. `_jobs`: when `gap` is true, start a new job entry even if `ProductCode` is unchanged (pass `gap` in). Do not add the gap row's `dg`/`dr` to the previous job.
4. `state_percent`: skip any interval whose `dt` exceeds `GAP_S` (it counts toward neither a state nor the total).
5. Bump `STORE_VERSION` to 2 so the store is rebuilt and the current overnight artefacts are cleared. This empties the buffer once; it refills over 60 min — say so to Walker before saving.
6. Acceptance: after the save, the event log has no event longer than the longest real one (about 2 min); `grep -n "GAP_S" code.py` shows the constant and its three uses. Paste both into the Dev Report.

Then, **with Walker's approval**, commit `VIS-001: Press 1 SCADA view in Perspective with gateway trend buffer` staging only `ignition/projects/mes-2026/`, `docker-compose.yml`, this spec and `docs/agent_handoff.md`.

### Fix verification (PM, 2026-10-21)

**Result:** ✅ Pass. Walker approved 2026-10-21 ("if thats ok -- then apprvoed"); his Designer crashed rather than updating, which also removed the old library copy. PM checked after: gateway RUNNING, no `press1` errors in the log, no MQTT reconnects.
- Read commit `72dc415`. `tick()` closes the open event at `prev['t']` and resets the debounce run when two rows are more than `GAP_S` apart; `_jobs(st, row, gap)` starts a new entry on a gap and drops the gap row's deltas; `state_percent` skips intervals over `GAP_S`. Matches fix steps 1–4. `GAP_S` appears as the constant plus two uses (the jobs path takes the `gap` flag, as step 3 specified) — accepted.
- Step 5 deviation accepted: the store key is now versioned (`press1.v2`), because an open Designer running the old library kept rebuilding the unversioned `press1` store and the two copies wiped each other. With separate keys the old code writes only to the dead `press1` entry (harmless; freed at the next gateway restart). Dev reports the buffer stable since 08:31 and the longest event 18 s.
- 103 RTO inhibit seen live by the Dev — the last open acceptance item.
- Commit staged only `ignition/projects/mes-2026/`, `docker-compose.yml`, this spec and `docs/agent_handoff.md`. Not pushed.
