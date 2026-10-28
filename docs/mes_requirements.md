# MES Requirements — Single-Line MES (Core Four)

*Status: v1.3, Oct 20, 2026. Scope, downtime model, the rush override design and the six open design calls from v1.1 are confirmed by Walker. v1.3: every remaining **(proposed)** item in §3–§10 was confirmed by Walker on Oct 20. The remaining functional detail (§3–§9) was filled in from the sim as built. Anything still marked **(proposed)** is VERA's pick and awaits Walker's confirmation. Expected values are VERA's arithmetic from the Sim Spec (§6, §7, §9), so check them against live deltas. This drives the Day 2 backend builds. See `about_4_0_printing.md` for the plant story and `sim_spec_press1.md` for the signals.*

## 1. Scope & Principles

- Single production line: **Press 1, a flexographic press. The print process only.** Laminating, slitting, bagging and prepress are out of scope.
- Runs against the sim defined in the Sim Spec.
- Core Four: Work Order Management, Scheduling, Downtime Tracking, OEE.
- MES data is computed or entered in the MES, never simulated.
- **Manual processes are part of the design (Walker).** The MES needs a manual capture surface for job readiness, schedule override and planned stop entry, and must stay correct when a human acts outside it. See About §5.1.
- **The MES records and reconciles. It does not control the press.** The sim loops its own job order and does not react to anything the MES does.
- Stack: Ignition, PostgreSQL, CoreFlux (MQTT), Maestrohub, Timebase, Timebase Atlas.
- Test visuals on Day 2 Hours 2–3 are throwaway. The real visuals come in one pass in Hour 4.

## 2. Inputs from the UNS

Root: `40Printing/Dallas/Press Room/Press 1`. All sim values arrive in the UNS Studio envelope, so Ignition reads `value`. Cast every value on ingest, because the same tag can arrive as integer or float depending on the phase (Sim Spec §11).

| Signal | Source (UNS path) | Used by |
| --- | --- | --- |
| Machine state (1 Running, 2 Setup, 3 Faulted) | `PLC/MachineState` | Downtime, OEE |
| Fault code (0, 101, 102, 103) | `PLC/FaultCode` | Downtime |
| RTO inhibit | `PLC/RTOInhibit` | Downtime (cross-check for 103) |
| Product code | `PLC/ProductCode` | Work Orders, Scheduling, OEE (ideal rate lookup) |
| Web lanes (2 or 4) | `PLC/WebLanes` | OEE (lane-meters), Scheduling |
| Good and reject meters (cumulative) | `PLC/GoodMeters`, `PLC/RejectMeters` | OEE, Work Orders |
| Tunnel zone temperatures | `Tunnel Dryer/Zone1Temp` to `Zone3Temp` | AI anomaly flagging |
| Web tension | `Unwind/WebTension`, `Rewind/WebTension` | AI anomaly flagging |
| Speed, registration, ink viscosity | `Print Section/LineSpeed`, `RegistrationError`, `InkViscosity` | OEE performance, AI quality flagging |

**Handling rules**

- Meters are cumulative. Compute produced and rejected meters as deltas. A drop to 0 means a sim restart, not negative production. **Observed Oct 20:** counters and the loop reset when the sim is restarted (Sim Spec §8).
- Stops last 4 to 6 samples. Debounce 2 consecutive samples (4 s). Use sample timestamps for duration.
- The product code and lane registers change at the start of the Setup phase, so a product change is visible before the press runs.
- The loop is 17.4 minutes and repeats, so the same alarm mix returns every loop. That suits the Day 2 test visuals.

## 3. Work Order Management

- **Purpose:** create and track print jobs for Press 1 from order entry to completion, and attribute the meters the press produces to the right job.
- **Status model (confirmed by Walker, Oct 20):** Planned, Released, Running, Complete, Closed. Side states: On Hold (for example proof not approved) and Cancelled. The MES sets Running and Complete from the PLC feed. People set the rest.
- **Functional requirements (confirmed by Walker, Oct 20):**
  1. Create a work order: product code, planned good meters, due date, priority (Normal or Rush), notes. Lanes, colors, substrate and scheduled changeover come from product master data (§7).
  2. Release, hold and cancel.
  3. Attribute runs. At each Setup to Running transition, link the run to a work order using the linkage rule below. An operator can reassign by hand.
  4. Track quantity from `GoodMeters` and `RejectMeters` deltas while a run is attributed. Show lane-meters (meters times lanes) beside meters.
  5. Complete a work order when the PLC product code changes to a different code. Compare good meters with planned meters and keep the difference as an over-run or under-run. Do not complete on quantity alone, because the sim produces a fixed number of meters per job visit.
  6. A person closes the work order after review.
- **Work order to run linkage (confirmed by Walker, Oct 20):** the PLC reports a product code, not a work order. The MES attributes a run to the earliest Released work order for that product code. An operator can reassign it by hand.
- **Data entities (confirmed by Walker, Oct 20):**
  - `work_order`: work_order_id, product_code, planned_meters, due_date, priority, status, hold_reason, created_at, released_at, started_at, completed_at, closed_at.
  - `work_order_run`: run_id, work_order_id, start_ts, end_ts, good_meters, reject_meters, attributed_by (auto or manual).
- **Seed data for Day 2 (confirmed by Walker, Oct 20):** ten work orders, two loops of the five jobs in sim order (101 to 105, then 101 to 105 again). Planned good meters equal what the sim produces per job visit: 600, 375, 450, 525 and 365. Stagger the due dates and make two of them tight, so the AI has at-risk orders to find.
- **Test visual criteria (Day 2 Hr 2):** a bare table with work order, product, status, planned m, good m, reject m, lanes, run start and run end.
  - On the first Running sample after a Setup, the matching work order moves to Running within one sample.
  - While Running, good meters rise by the job step per 2 s sample (8, 5, 6, 7, 5) and hold during Faulted.
  - When the product code changes, the work order moves to Complete with good meters of 600, 375, 450, 525 and 365 (plus or minus one step) and reject meters of 18, 18, 18, 18 and 83.
  - After a sim restart, no work order shows negative produced meters.
- **AI hook (Day 2 Hr 4):** "Which work orders are at risk of missing their due date?" and "Summarize what happened on this work order."

## 4. Scheduling

- **Purpose:** sequence the Press 1 queue, show planned starts and ends with changeover allowances, gate starts on readiness, and show when the press does something the schedule did not expect.
- **Functional requirements (confirmed by Walker, Oct 20):**
  1. Order released work orders into a sequence.
  2. Compute planned start and end per entry. Planned job time is the scheduled changeover plus the planned meters at the ideal speed (table below).
  3. Take the scheduled changeover from product master data.
  4. Capture job readiness by hand: plates and cylinders ready, ink ready, proof approved. A job is Ready only when all three are entered.
  5. Let a person move a job to the front or reorder the queue, with a reason (§4.1).
  6. Reconcile the PLC against the schedule at each Setup to Running transition (§4.1).
  7. Show plan against actual start and end.
- **Rules / constraints (confirmed by Walker, Oct 20):** changeover cost depends on color count, substrate and a lane change. A job cannot be marked Ready until plates, ink and proof are entered, and a person enters them. The press does not wait for the MES, so a job that starts without readiness is flagged as "started without readiness". A human override beats the MES sequence, and the MES must cope with a schedule it did not produce.
- **Data entities (confirmed by Walker, Oct 20):**
  - `schedule_entry`: entry_id, work_order_id, sequence, planned_start, planned_end, scheduled_changeover_s, status.
  - `job_readiness`: work_order_id, plates_ready, ink_ready, proof_approved, entered_by, entered_at.
  - `schedule_override`: see §4.1.
- **Expected plan against actual in the sim (VERA's arithmetic):**

| Job | Planned meters | Ideal run (meters over ideal speed) | Scheduled changeover | Planned total | Actual in sim | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| 101 | 600 | 144 s | 20 s | 164 s | 198 s | +34 s |
| 102 | 375 | 125 s | 30 s | 155 s | 224 s | +69 s |
| 103 | 450 | 135 s | 24 s | 159 s | 202 s | +43 s |
| 104 | 525 | 143 s | 20 s | 163 s | 214 s | +51 s |
| 105 | 365 | 137 s | 30 s | 167 s | 208 s | +41 s |
| Loop |  |  |  | 808 s | 1,046 s | +238 s |

The press runs about 30% behind plan. The gap comes from alarms, changeover overrun and sim speed below ideal. Plan against actual will drift, which is useful for the AI.

- **Test visual criteria (Day 2 Hr 2):** a bare table with sequence, work order, product, readiness (three flags), planned start, planned end, actual start, actual end and a reconcile result.
  - With the schedule seeded 101, 102, 103, 104, 105, every start reconciles as a normal start.
  - Jobs 102 and 104 show a changeover overrun of 14 s.
  - A job with readiness not entered shows "started without readiness" when the press starts it.
  - The reconcile outcomes in §4.1 each appear using the demo recipe.
- **AI hook:** "Which job sequence gives the shortest total changeover time?" and "Which changeovers ran over, and by how much?"

### 4.1 Rush override (confirmed by Walker, Oct 20)

**Principle:** a rush override is a person's decision. The MES records it, publishes it and reconciles it against the PLC. It never leaves a signal in the sim.

1. **Capture.** The front end has a "move job to front" action. It writes a schedule override record: work order, product code, previous sequence, new sequence, reason (customer expedite, material availability, other), entered by, entered at.
2. **Publish.** The MES publishes each override under `40Printing/Dallas/Press Room/Press 1/MES/ScheduleOverride`. Payload: work order, product code, from sequence, to sequence, reason, operator, timestamp.
3. **Reconcile.** At each Setup to Running transition, the MES compares the PLC `ProductCode` against the head of the schedule after overrides are applied. The four outcomes are in the table below.
4. **Cost.** The scheduled changeover time for the job that actually ran comes from its product master data, so the MES can report what the rush added in changeover and overrun.
5. **Day 2 demo with this sim.** The sim runs jobs in the fixed order 101, 102, 103, 104, 105. Seed the schedule in that order. To demonstrate a rush, enter an override that moves a later job to the front. The press keeps running its own order, and the MES shows the deviation. The teaching point is that the MES cannot command the press. It can only record and reconcile.

**Reconcile outcomes (confirmed by Walker, Oct 20).** "Matching" means the head of the schedule after overrides are applied.

| Outcome | When |
| --- | --- |
| Normal start | PLC product equals the head of the schedule and no override moved it. |
| Authorized override | PLC product equals the head of the schedule, and an override record moved that job there. |
| Override not followed | An override record exists, but the PLC runs a different job from the new head. This is what happens in the sim whenever an override disagrees with the fixed order 101 to 105. |
| Unrecorded deviation | PLC product differs from the head of the schedule and no override record explains it. Flag it for review. Do not hide it or reorder history. |

**Demo recipe.** The press order is fixed, so vary the schedule and not the press.

- Normal: schedule 101, 102, 103, 104, 105.
- Authorized override: the MES proposes 101, 102, 104, 103, 105. An operator overrides 103 ahead of 104, which matches the press.
- Override not followed: schedule 101 to 105, then override 105 to the front. The press still runs 101.
- Unrecorded deviation: schedule 101, 102, 104, 103, 105 with no override record. The press runs 103 when the head is 104.

## 5. Downtime Tracking

- **Purpose:** record every stop on Press 1 as an event with start, end, duration, class and product code, and keep planned and unplanned time apart.
- **Detection:** event detection from state and fault code, using the debounce rule in §2.

**Unplanned downtime classes (Walker)**

| Class | Source | Rule |
| --- | --- | --- |
| Web break | PLC | State Faulted (3), fault code 101. Most common. |
| Tunnel over-temp | PLC | State Faulted (3), fault code 102. |
| RTO inhibit | PLC | State Faulted (3), fault code 103. `PLC/RTOInhibit` is also true, so it can be cross-checked. |
| Changeover overrun | Derived in the MES | State Setup (2) for longer than the scheduled changeover time. The time beyond the schedule is unplanned. Not a PLC code. |
| Unclassified alarm | PLC | State Faulted (3) with any other fault code. Never dropped. **(confirmed by Walker, Oct 20)** |

**Planned downtime (Walker)**

- **Changeover:** Setup time up to the scheduled changeover time.
- **Clean plates and roll change:** entered by an operator in the front end and stored in the database. Each entry has a start, an end, a reason and the product code at the time. The press PLC does not show these stops.
- **MES UNS topic:** each planned stop is also published under `40Printing/Dallas/Press Room/Press 1/MES/PlannedStop` (path and payload confirmed by Walker, Oct 20). Payload fields: reason, start, end, operator. Written by the MES, not the sim.
- **Conflict rule (Walker):** a planned stop entered while the PLC shows Running is flagged as a conflict and kept for review. It is not blocked, and it is never hidden or silently merged.

**Event timing rules (confirmed by Walker, Oct 20)**

- Open an event after 2 consecutive samples in the same state and fault code. Backdate the start to the first of those samples.
- Close it on the first sample that differs. Duration is the difference of the sample timestamps. A fault phase of 10 s should measure 10 s, plus or minus one sample (2 s).
- A change of fault code inside Faulted closes one event and opens another.
- A Setup event splits at the scheduled changeover seconds. The first part is planned changeover. The rest is changeover overrun.
- **Data entities (confirmed by Walker, Oct 20):**
  - `downtime_event`: event_id, start_ts, end_ts, duration_s, source (plc, derived or operator), machine_state, fault_code, class, is_planned, product_code, work_order_id.
  - `planned_stop`: planned_stop_id, reason (clean plates or roll change), start_ts, end_ts, operator, product_code, conflict_flag, conflict_note.
- **Test visual criteria (Day 2 Hr 3):** a bare table of events (start, end, duration, class, planned flag, product code, work order) and a total by class.
  - Over one 17.4-minute loop: 15 alarm events, 9 web break, 4 tunnel over-temp, 2 RTO inhibit. Their total times are about 82 s, 48 s and 24 s.
  - Five Setup events totalling 146 s: 118 s planned changeover and two overruns of 14 s (before jobs 102 and 104).
  - A planned stop entered while the PLC shows Running appears with the conflict flag.
  - A Faulted state with a fault code other than 101, 102 or 103 appears as "Unclassified alarm".
- **AI hook:** "Which alarm cost the most run time, and on which job types?" Expected answer from this sim: web break, about 82 s per loop over 9 events. "How often does the RTO inhibit the press?" Expected: 2 per loop, on jobs 102 and 105.

## 6. OEE

- **Purpose:** report Availability, Performance, Quality and OEE for Press 1 live, per work order and per time window, using planned and unplanned time as Walker defined them.
- **Definitions:**
  - Planned production time: window time minus planned downtime (changeover up to schedule, operator-logged planned stops).
  - Running time: time in state 1.
  - **Availability** = Running time over planned production time. With no other states in the sim, planned production time is Running plus alarm time plus changeover overrun.
  - **Performance** = good meters over (Running minutes times the product's ideal speed in m/min). Cap the display at 100%.
  - **Quality** = good meters over (good plus reject meters).
  - **OEE** = Availability times Performance times Quality.
- **Planned vs. unplanned in Availability (Walker):** planned time (changeover up to schedule, operator-logged planned stops) is removed from planned production time and does not reduce Availability. Unplanned time (web break, tunnel over-temp, RTO inhibit, changeover overrun) reduces Availability.
- **Performance basis (confirmed by Walker, Oct 20).** Performance uses good meters only. On job 105 the reject counter steps 1 m per sample on top of the 5 m per sample good step, so good plus reject is 6 m per sample (180 m/min), while `LineSpeed` reads about 150. A good-plus-reject basis would put job 105 above 100% (VERA's arithmetic from Sim Spec §6 and §7: 438 m over 146 s of running against an ideal of about 389 m).
- **Ideal cycle time source:** MES master data per product code. Ideal speed in m/min, held in the product master (§7). The ideal speed is not in the sim.
- **Time basis (confirmed by Walker, Oct 20):** write one OEE interval row per minute per product code, then aggregate for any window: live (last 15 minutes), per work order run, per hour, since start.
- **Data entities (confirmed by Walker, Oct 20):** `oee_interval`: interval_start, product_code, work_order_id, running_s, planned_production_s, good_m, reject_m, ideal_m.
- **Expected values from this sim (VERA's arithmetic, Sim Spec §9, check against live deltas):**

| Job | Availability | Performance | Quality | OEE |
| --- | --- | --- | --- | --- |
| 101 (4-wide) | 83.3% | 96.0% | 97.1% | 77.7% |
| 102 (2-wide) | 77.3% | 83.3% | 95.4% | 61.5% |
| 103 (4-wide) | 83.3% | 90.0% | 96.2% | 72.1% |
| 104 (2-wide) | 77.3% | 95.5% | 96.7% | 71.4% |
| 105 (2-wide, drift) | 81.1% | 93.8% | 81.5% | 62.0% |
| **Loop** | **80.4%** | **92.1%** | **93.7%** | **69.4%** |

Availability is 82.9% if planned setup is not excluded. OEE is then about 71.5%. The 4-wide jobs score higher than the 2-wide jobs. The gaps come from changeover overrun (102, 104), Performance on 102 and the quality drift on 105. The About page sets an OEE target of 70%, so the loop lands just under it.

- **Test visual criteria (Day 2 Hr 3):** four tiles (A, P, Q, OEE) and a per-job table. After one full loop, the values match the table above within about 1 to 2 points.
- **AI hook:** "How does OEE compare between 2-wide and 4-wide jobs, and what drives the gap?"

## 7. Data Model Overview (PostgreSQL)

*Entity list and relationships. Sketch to be added.*

| Table | Purpose | Key columns |
| --- | --- | --- |
| product_master | Ideal speed, lanes, colors, substrate, scheduled changeover time | product_code |
| work_order | Orders and status | work_order_id, product_code |
| work_order_run | Attribution of a press run to a work order | run_id, work_order_id |
| schedule_entry | Sequence and planned times | work_order_id, sequence |
| schedule_override | Rush and other manual reorders | work_order_id, from and to sequence, reason, operator, time |
| job_readiness | Manual entry: plates, ink, proof | work_order_id |
| downtime_event | Detected from state and fault code, with class | start, end, class |
| planned_stop | Operator-entered clean plates and roll change | start, end, reason |
| oee_interval | Computed Availability, Performance, Quality inputs | interval_start, product_code |

Table list **(confirmed by Walker, Oct 20)**. Raw samples are not stored in PostgreSQL. Timebase holds the history.

**Product master seed (About §3, confirmed by Walker):**

| Product code | Family | Substrate | Lanes | Colors | Ideal speed | Scheduled changeover |
| --- | --- | --- | --- | --- | --- | --- |
| 101 | Snack bag film | OPP | 4 | 5 | 250 m/min | 20 s |
| 102 | Coffee pouch film | PET | 2 | 8 | 180 m/min | 30 s |
| 103 | Frozen food bag film | PE | 4 | 4 | 200 m/min | 24 s |
| 104 | Candy wrapper film | OPP | 2 | 6 | 220 m/min | 20 s |
| 105 | Pet food bag film | PE | 2 | 7 | 160 m/min | 30 s |

## 8. Integration & Architecture

- **Data flow (confirmed by Walker, Oct 20):** UNS Studio sim → CoreFlux (MQTT) → Maestrohub (unwrap and cast the envelope, route) → Ignition (MES logic, test visuals, Perspective) → PostgreSQL (MES records). Timebase ingests the tags for history. Timebase Atlas reads the model and the events for the AI agents.
- **Envelope:** the sim publishes the UNS Studio JSON envelope. Ignition unwraps `value`.
- **Historian role (Timebase) (confirmed by Walker, Oct 20):** raw tag history for trends and for the AI to query. The UNS Studio historian is off.
- **Knowledge graph role (Timebase Atlas) (confirmed by Walker, Oct 20):** Press 1, its stations, tags, work orders and downtime classes as nodes, so the AI can follow a downtime event to its work order and product.
- **MES namespace (published back to the UNS):** under `40Printing/Dallas/Press Room/Press 1/MES/`. Published by the MES, never by the sim.

| Topic under `.../Press 1/MES/` | Status |
| --- | --- |
| `ScheduleOverride` | Confirmed by Walker (§4.1) |
| `PlannedStop` | Confirmed by Walker, Oct 20 (path and payload as in §5) |
| `Downtime/CurrentClass` | Confirmed by Walker, Oct 20 |
| `OEE/Availability`, `OEE/Performance`, `OEE/Quality`, `OEE/OEE` | Confirmed by Walker, Oct 20 |
| `WorkOrder/Active` | Confirmed by Walker, Oct 20 |

- The first topic level is `40Printing`, with no dot. The original `4.0 Printing` broke Ignition, because Ignition does not allow `.` in tag names. Walker renamed it on Oct 20 (DEC-005). The company name in display text stays "4.0 Printing".

## 9. AI Analytics (Day 2 Hr 4)

- **Natural-language OEE and downtime queries.** Seed from About §6. The sim gives checkable answers:
  - Which alarm cost the most run time? Web break, about 82 s per loop, 9 events.
  - How often does the RTO inhibit the press? 2 per loop, on jobs 102 and 105.
  - Which changeovers ran over the scheduled time? Before jobs 102 and 104, by 14 s each.
  - Which job has the worst quality? Job 105, about 81%.
  - How does OEE compare between 2-wide and 4-wide jobs? 4-wide is higher (§6).
- **Anomaly flagging.** Tunnel temperature and web tension are the key variables. The sim gives the AI **detection, not prediction**: faults have no lead-in (Sim Spec §11 rule 6). What it can flag:
  - Tunnel zones above their normal band (above about 195 °F) during an over-temp alarm.
  - Tension falling to 0 during a web break.
  - Registration error and ink viscosity above band on job 105 (registration 0.30 to 0.60 mm against 0.02 to 0.12, viscosity 31 to 36 s against 24 to 28).
  - If a precursor demo is wanted, the sim needs ramp phases (Sim Spec §13).
- **Work order and scheduling assistance.** Suggest a job order with less changeover, flag at-risk work orders, and explain a deviation found in reconcile. The AI should ask before assuming anything not written in the docs.

## 10. Out of Scope

- Laminating, slitting, bagging, shipping and prepress
- Starved and blocked states
- Planned stops and schedule overrides in the sim (the MES enters them)
- Multi-line or multi-press scheduling
- Quality management, maintenance, material traceability *(confirmed by Walker, Oct 20)*

## 11. Acceptance Criteria

Each function is verified through its test visual. The values below come from the sim as built, so a full 17.4-minute loop is the test unit. Start the loop from a known point (sim restart before the test) or measure deltas over a whole loop.

- **Cross-cutting:** after one full loop the MES shows 15 alarm events (9 web break, 4 over-temp, 2 RTO inhibit), 2 changeover overruns of 14 s each, and meter totals that match the Sim Spec §9 reference values within a few meters.
- **Work orders:** each of the five jobs completes with the good and reject meters in §3. No negative meters after a restart.
- **Scheduling:** seeded in sim order, every start is a normal start. The four reconcile outcomes in §4.1 each appear using the demo recipe.
- **Downtime:** events, classes and totals as in §5. A planned stop entered during Running is flagged as a conflict.
- **OEE:** per-job and loop values within 1 to 2 points of the §6 table.
- **AI:** each query in §9 returns the expected answer, or says what data it is missing.

## 12. Open Questions

Closed Oct 20 (Walker approved): the four reconcile outcomes in §4.1, the proposed MES UNS topics and the `PlannedStop` path and payload in §8, the work order to run linkage rule in §3, the Performance basis in §6, the OEE time basis in §6, and the seed data approach in §3.

Also closed Oct 20 (Walker confirmed all): the work order status model, functional requirements and entities (§3); scheduling functional requirements, readiness rules and entities (§4); the Unclassified alarm rule, event timing rules and entities (§5); the `oee_interval` entity (§6); the table list (§7); the data flow and the Timebase and Timebase Atlas roles (§8); and quality management, maintenance and material traceability staying out of scope (§10).

Still open: none. Walker's word overrides anything here.
