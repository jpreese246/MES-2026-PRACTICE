# Sim Spec — 4.0 Printing, Press 1 (Raw Layer)

*Status: v1.0, Oct 20, 2026. This describes the sim as built and running (`fourzero_printing_press1`). Walker confirmed the decisions in §1. See `about_4_0_printing.md` for the plant story, `sim_build_guide.md` for how the definition was built, and `sim/fourzero_printing_press1.json` for the definition itself.*

**Hard rule:** raw process values + PLC status/state registers only. No MES data is ever simulated. OEE, work orders, schedules, downtime reasons, planned stops, scheduled changeover times, schedule overrides and shift/crew context are computed or entered downstream.

**Scope:** one machine, one sim. Press 1, an 8-color flexographic press with a hot-air tunnel dryer. The print process only.

## 1. Decisions (Walker, Oct 20)

| Topic | Decision |
| --- | --- |
| Process | Flexographic, 8 colors, heat-tunnel (hot-air) drying. Key variables are tunnel temperature and web tension. |
| Company and sim | New fictional company "4.0 Printing". New sim. |
| Alarms (read from state and fault code) | Web break (101), tunnel over-temp (102), RTO inhibit (103). The RTO is an alarm. |
| Planned downtime | Clean plates and roll change are planned. They are never in the sim. The MES front end logs them and the MES publishes them to the UNS. |
| Setup | Planned up to the scheduled changeover time. Setup beyond it is unplanned. The scheduled time is not in the sim. |
| Fault cadence | About a 10-second fault every 60 seconds. This is classroom time compression. |
| Fault mix | Weighted, web break is the most common. |
| Product code | Raw `ProductCode` and `WebLanes` registers, no order linkage. |
| Units | °F, meters |
| Starved and blocked | Excluded |
| Reject rate on job 105 | About 20% of good meters is accepted as a deliberate drift job. |
| Temperature bands, scheduled changeovers, overrun jobs (102, 104), drift job (105) | Confirmed correct by Walker as printing SME. |
| Topic names | Human-readable. Delegated to VERA. |

## 2. Namespace

Spaces work in UNS Studio topic levels. Tag names are PascalCase.

| Level | Topic level |
| --- | --- |
| Manufacturer / Enterprise | `40Printing` (display name "4.0 Printing"; renamed Oct 20, DEC-005) |
| Site | `Dallas` |
| Area | `Press Room` |
| Line (single production line) | `Press 1` |

Topic root: `40Printing/Dallas/Press Room/Press 1/...`. Sim sub-levels are `PLC`, `Unwind`, `Print Section`, `Tunnel Dryer` and `Rewind`.

**MES-published topics** live under `40Printing/Dallas/Press Room/Press 1/MES/...`. The MES publishes them, never this sim. See MES Requirements §8.

## 3. Process and Line Layout

See About 4.0 Printing §3–§4. One press prints film in 2-wide or 4-wide webs. The sim runs one block of phases per job across 5 job types, looped. Output is counted in meters.

| # | Station | Function | Topic sub-level |
| --- | --- | --- | --- |
| 1 | Unwind and splice | Mount roll, control web tension | `Unwind` |
| 2 | Print stations 1–8 | One color per unit, registration, ink | `Print Section` |
| 3 | Tunnel dryer | Hot-air ink drying. Exhaust to the RTO. | `Tunnel Dryer` |
| 4 | Chill and inspect | Not simulated in v1 | none |
| 5 | Rewind | Wind the printed roll | `Rewind` |

## 4. State and Fault Codes

| `PLC/MachineState` | Meaning |
| --- | --- |
| 1 | Running |
| 2 | Setup (changeover) |
| 3 | Faulted |

| `PLC/FaultCode` | Meaning | Class | Duration in sim |
| --- | --- | --- | --- |
| 0 | None (Running or Setup) | n/a | n/a |
| 101 | Web break | Unplanned alarm | 8 or 10 s |
| 102 | Tunnel over-temp | Unplanned alarm | 12 s |
| 103 | RTO inhibit (`PLC/RTOInhibit` also true) | Unplanned alarm | 12 s |

A Faulted state with any other code is "Unclassified alarm" in the MES. Changeover overrun is derived in the MES from Setup time against the scheduled changeover time. It is not a PLC code.

## 5. Tags (16)

Tag path is the topic under `40Printing/Dallas/Press Room/Press 1`. All values arrive in the UNS Studio envelope (§11). Every cell below was checked against the definition JSON.

| Tag path | Units | Running | Setup | Web break 101 | Over-temp 102 | RTO inhibit 103 |
| --- | --- | --- | --- | --- | --- | --- |
| `PLC/Connected` | none | true | true | true | true | true |
| `PLC/MachineState` | none | 1 | 2 | 3 | 3 | 3 |
| `PLC/FaultCode` | none | 0 | 0 | 101 | 102 | 103 |
| `PLC/ProductCode` | none | job code | new job code | held | held | held |
| `PLC/WebLanes` | none | 2 or 4 | new job lanes | held | held | held |
| `PLC/GoodMeters` | m | steps (§6) | holds | holds | holds | holds |
| `PLC/RejectMeters` | m | 0, or 1 per sample on job 105 | holds | 2 per sample | holds | holds |
| `PLC/RTOInhibit` | none | false | false | false | false | true |
| `Unwind/WebTension` | lbf | random walk 20–30 | 0 | 0 | 0 | 0 |
| `Rewind/WebTension` | lbf | random walk 18–28 | 0 | 0 | 0 | 0 |
| `Print Section/LineSpeed` | m/min | random walk around job speed (§6) | 0 | 0 | 0 | 0 |
| `Print Section/RegistrationError` | mm | random walk 0.02–0.12 (job 105: 0.30–0.60) | 0 | 0 | 0 | 0 |
| `Print Section/InkViscosity` | s (Zahn cup) | random walk 24–28 (job 105: 31–36) | random walk 24–28 (all jobs, including 105) | job's Run band (job 105: 31–36) | job's Run band (job 105: 31–36) | job's Run band (job 105: 31–36) |
| `Tunnel Dryer/Zone1Temp` | °F | random walk 160–180 | 160–180 | 160–180 | 215–235 | 160–180 |
| `Tunnel Dryer/Zone2Temp` | °F | random walk 175–195 | 175–195 | 175–195 | 215–235 | 175–195 |
| `Tunnel Dryer/Zone3Temp` | °F | random walk 170–190 | 170–190 | 170–190 | 215–235 | 170–190 |

*Notes from the definition read-back:*

- *Registration error is 0 in every Setup and fault phase.*
- *Ink viscosity and the three zone temperatures keep walking in every phase, stopped or not. Only the tension, speed and registration tags drop to 0 when the press is not running.*
- *Over-temp moves all three zones to 215–235 on the first sample of the fault phase. There is no ramp before it and no ramp after it.*
- *RTO inhibit does not change the zone temperatures. Only `PLC/RTOInhibit`, the state and the fault code show it.*

"Holds" for counters means `step: 0`. The counter keeps publishing at its last value. "Held" for registers means the value set in Setup carries through the job.

## 6. Jobs

Speed is set by the integer counter step per 2-second sample. Meters per sample times 30 gives m/min. Steps are integer because `counter` ignores `decimals`, so sim speed is slightly below the About §3 ideal. The MES holds the ideal speed and computes Performance. The MES multiplies meters by lanes for lane-meters.

| Order | Product code | Lanes | Good step (m per sample) | Sim speed | Ideal speed (About §3) | Performance |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 101 | 4 | 8 | 240 m/min | 250 | 96% |
| 2 | 102 | 2 | 5 | 150 m/min | 180 | 83% |
| 3 | 103 | 4 | 6 | 180 m/min | 200 | 90% |
| 4 | 104 | 2 | 7 | 210 m/min | 220 | 95% |
| 5 | 105 (drift) | 2 | 5 | 150 m/min | 160 | 94% |

## 7. Loop as Built

Publish interval is 2 seconds. The sim has 35 phases: for each job, one Setup phase then 3 Run and Fault cycles. One loop takes 1,046 seconds (17.4 minutes). All durations are even because of the 2-second interval.

| Job | Setup | Run 1 | Fault 1 | Run 2 | Fault 2 | Run 3 | Fault 3 | Job total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 101 (4-wide) | 18 | 50 | 101 for 10 | 52 | 101 for 8 | 48 | 102 for 12 | 198 |
| 102 (2-wide) | 44 | 50 | 101 for 10 | 48 | 103 for 12 | 52 | 101 for 8 | 224 |
| 103 (4-wide) | 22 | 48 | 102 for 12 | 50 | 101 for 10 | 52 | 101 for 8 | 202 |
| 104 (2-wide) | 34 | 50 | 101 for 10 | 48 | 102 for 12 | 52 | 101 for 8 | 214 |
| 105 (2-wide, drift) | 28 | 48 | 102 for 12 | 50 | 101 for 10 | 48 | 103 for 12 | 208 |

**Faults per loop:** 15. Web break 9 (60%), over-temp 4 (27%), RTO inhibit 2 (13%). Over-temps happen on jobs 101, 103, 104 and 105. RTO inhibits happen on jobs 102 and 105.

**Setup and overrun.** Setup is state 2 with fault code 0. The product code and lane registers change at the start of the Setup phase.

| Before job | Sim setup | Scheduled (MES master data) | Result |
| --- | --- | --- | --- |
| 101 | 18 s | 20 s | Planned |
| 102 | 44 s | 30 s | Overrun, 14 s unplanned |
| 103 | 22 s | 24 s | Planned |
| 104 | 34 s | 20 s | Overrun, 14 s unplanned |
| 105 | 28 s | 30 s | Planned |

## 8. Counters

- `GoodMeters` steps only in Run phases and holds everywhere else.
- `RejectMeters` is its own counter, not a formula off `GoodMeters`. It steps 2 per sample in a web break, 1 per sample in job 105 Run phases, and holds otherwise. A multiplier on a cumulative count would jump at every job change.
- Both are cumulative across jobs and loops. A counter keeps its value when its phase is left and re-entered (probe, Build Guide §3).
- **Both reset to 0 when the sim is stopped and started, and the loop starts over. Observed Oct 20.** Walker restarted the sim at about 11:43 CDT. At about 11:58 CDT the sim had 917 s of runtime, was in job 105 Run 1, and read 1,995 good meters and 81 reject meters. That equals jobs 101–104 (1,950 good, 72 rejects) plus 9 samples of job 105 (45 good, 9 rejects). Without a reset the counters would be in the thousands. Nobody should restart the sim during class, because it throws away the counts and the MES would see a drop to 0.
- **Reject rate (accepted):** job 105 rejects about 20% of good meters (1 against 5 per sample). This is a deliberate drift job. Integer counters at a 2-second interval cannot go lower.

## 9. Reference Values per Loop

For Day 2 hand-checking. These figures were re-derived from the definition JSON (phase durations times counter steps) and match the loop table. Totals can still be off by a sample or two at phase boundaries, so check against live deltas before using them as test targets.

| Quantity | Value per loop |
| --- | --- |
| Run time | 746 s |
| Fault time | 154 s (web break 82 s, over-temp 48 s, RTO 24 s) |
| Setup time | 146 s (118 s planned, 28 s overrun) |
| Good meters | about 2,315 (job 101: 600, 102: 375, 103: 450, 104: 525, 105: 365) |
| Reject meters | about 155 (82 from web breaks, 73 from job 105 drift) |
| Availability, Running vs Running plus Faulted | 82.9% |
| Availability, planned setup excluded and overrun counted as unplanned | about 80.4% (746 of 928 s) |
| Loop quality, good over good plus reject | about 93.7% (scrap about 6.3%, above the 4% target in About §6) |
| Quality by job | about 97% (101), 95% (102), 96% (103), 97% (104), 81% (105) |

## 10. Explicitly Out of Scope for the Sim

- No work order, schedule or order-number data
- No OEE, availability, performance or quality values
- No downtime reason codes beyond the raw state and fault codes (101, 102, 103)
- No scheduled changeover times or overrun flags (derived in the MES)
- No planned stops (clean plates, roll change, breaks, shutdown)
- No schedule overrides or rush jobs (the sim loops its job order and does not react to the MES)
- No shift, crew or operator data
- No prepress, ink room, laminating, slitting or shipping signals
- Not in v1: micro-stops, slow running, starved and blocked states

## 11. Consumer Rules (what Ignition and the MES must handle)

1. **Envelope.** Every message is the UNS Studio JSON envelope: `value`, `timestamp`, `datatype`, `status`, `units`. Ignition unwraps `value`.
2. **Datatypes change between phases.** `static 0` publishes as integer. Random walks and counters publish as float. This affects `LineSpeed`, `RegistrationError`, both `WebTension` tags and both meter counters. Cast everything on ingest. Meters arrive as floats such as `54.0`.
3. **Meters are cumulative.** Use deltas. A drop to 0 means the sim restarted (observed, §8). It is not negative production.
4. **Stop detection.** A stop lasts 4 to 6 samples. A debounce of 2 consecutive samples (4 s) catches every one. Use sample timestamps for duration, not sample counts.
5. **Topic root `40Printing`.** The original `4.0 Printing` broke Ignition, because Ignition does not allow `.` in tag names. Walker renamed it and reimported the sim at about 13:45 CDT on Oct 20, which reset the counters (DEC-005). Spaces in the lower levels work in Ignition MQTT Engine and are untested in Maestrohub and Timebase.
6. **Faults have no lead-in.** Tension goes straight to 0 on a web break, and zone temperatures jump straight to 215–235 on an over-temp. There is no tension spike before a break and no temperature climb before a trip. An analytics agent can detect and classify these events, but it cannot find a precursor in the data.

## 12. Verification Status

- **Passed `create_simulator` validation** on the first call. 16 topics, 35 phases, 560 topic entries.
- **Definition read back (Oct 20, about 11:45 CDT).** The sim JSON was compared with this spec. Phase count, 16 topics per phase, every duration, product code, lane count, counter step, fault code, `RTOInhibit` value and temperature or viscosity band match §5–§7. The §9 totals re-derive from it.
- **Root renamed to `40Printing` (Oct 20, about 13:45 CDT, DEC-005).** All 16 topics verified live on the stack's CoreFlux under the new root at about 14:10 CDT. The repo copy of the definition predates the rename (§13 item 1).
- **Definition file in this repo (Oct 20, 12:17 CDT).** `sim/fourzero_printing_press1.json` is a byte-for-byte copy (matching SHA-256) of the file in UNS Studio's `config/simulators/` folder. It parses as 35 phases, 16 topics per phase and a 1,046 s loop, matching §7. That check covers structure and timing only. The per-cell comparison above was done on the earlier read, before Walker's restart.
- **All 16 topics** found by `search_tags` and shown in the Sim UNS MQTT client.
- **Checked live at about 11:29 CDT (sim runtime about 550 s, in job 103):** product code 103, lanes 4, Running state, speed 185 m/min against the designed 180, zones and tensions in band. Good meters read 975 at the start of job 103 Setup, which equals jobs 101 and 102 (600 m plus 375 m). Rejects read 36, which equals 18 m from each of the first two jobs. Counters matched the as-built arithmetic, and the sim had not restarted at that point.
- **Checked live at about 11:58 CDT, after Walker's restart (runtime 917 s, in job 105 Run 1):** product code 105, good meters 1,995, reject meters 81. Both match the loop arithmetic from a fresh start, so the counters did reset on restart (§8).
- **Not yet observed live:** fault phases directly (the reject totals are indirect evidence that web breaks step 2 per sample, and that 102 and 103 do not), and the full 17.4-minute loop end to end. Walker will test these during the build. The check list is in Build Guide §8.

## 13. Open Items

1. **Repo copy of the definition is stale.** `sim/fourzero_printing_press1.json` still has the `4.0 Printing` root. It needs a byte-for-byte copy of the renamed file from UNS Studio's `config/simulators/` (VERA/Walker). Never hand-edit it. Maestrohub and Timebase handling of the spaces is untested.
2. **Probe cleanup.** The probe sim `probe_counter_test` was deleted on Oct 20 with Walker's approval. Its four cached tags are still in the namespace: `Probe/CounterTest/Count`, `Derived`, `Phase` and `Walk`. The MCP tools cannot remove tags. Clear them in the UNS Browser if it has a tag delete, or tell students to ignore `Probe/`. Clear them before students connect. Do not restart UNS Studio to clear them, because that resets the print sim's counters.
3. **Precursors for the AI (decision for Walker, before Day 2).** Faults have no lead-in (§11 rule 6). If Day 2 Hour 4 should show the AI finding a tension or temperature signature before a stop, the definition needs ramp phases ahead of some faults. That is an `update_simulator` call, which restarts the sim and resets counters. Do it before students pull data, or leave the sim as is.
4. Fault phases not yet watched live (Walker will test while building).

*Closed Oct 20: counter reset on restart (observed, §8).*
