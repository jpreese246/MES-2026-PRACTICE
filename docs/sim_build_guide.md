# UNS Studio Sim Build Guide: VERA's Working Rules

*Status: v1.0, Oct 20, 2026. The rules VERA follows when turning a Sim Spec into a `create_simulator` definition that works in UNS Studio. Written from the Format Guide, two SteelCo sim definitions, a probe sim, and one real build (`fourzero_printing_press1`). Sits alongside `sim_spec_press1.md`; the finished definition is `sim/fourzero_printing_press1.json`.*

**Source tags:** (D) = UNS Studio Simulator Format Guide and user docs. (J) = read from a real sim JSON. (O) = observed live in the namespace. (P) = measured by the probe sim. (B) = learned in the real build.

## 1. What this is based on

- **Read in full (D):** `reference/simulator-format-guide.md`, `user-docs/reference/simulators.md`, and the spec-to-simulator workflow in `attachment-workflows-reference.md`.
- **Read in full (J):** `steelco_rolling_mill` (3 phases, 6 stands) and `steelco_stand3_proposed_instrumentation` (2 phases, fault injection).
- **Not read:** the Racine JSON and `steelco_melt_shop`. Comments about them come from their tag output only.
- **Tooling limit:** the MCP `get_simulator` returns name, category and run state, not the definition. To read a definition, open it in Simulator Builder (Edit), read the file under UNS Studio's `config/simulators/` folder, or put the JSON on the canvas.
- **Historian:** `get_tag_history` returns "Tag historian not available" on this instance. Verify by polling `get_tag`, `search_tags` or the MQTT client, or turn the historian on.
- **Pasting JSON into a rich-text tool:** a rendered text block turns `*` into italics, so `0.7*BearingStressIndex` shows as `0.7 BearingStressIndex`. Keep sim JSON in fenced code blocks, and copy the definition from the file, never out of a rendered block.

## 2. Hard constraints of the engine (D)

1. **One JSON file, no code.** Metadata, then `phases`, then `groups`, then `topics`, each with one `generator`.
2. **Payload is fixed.** Every message is the engine's envelope: `value`, `timestamp`, `datatype`, `status` (always "Good"), and `units` if defined. There is no plain-value or Sparkplug option. Ignition and the MES unwrap `value`.
3. **No conditional logic.** `formula` is arithmetic only: `+ - * /`, parentheses, numbers, topic names. No IF, no comparisons, no functions, no self-reference. **State cannot drive other values at runtime.**
4. **Scenarios are made of phases.** `cycle_mode: "sequential"` loops forever. **A phase with no `duration_seconds` lasts exactly one cycle.** Set `duration_seconds` to hold a phase. State is authored as a phase, not computed. The other modes are `random` (draws a phase each time, can repeat) and `fixed` (phase 0 only).
5. **One interval per phase.** All topics in a phase publish together every `interval_seconds` (integer seconds).
6. **Generators:** `random_float`, `random_int`, `random_choice`, `static`, `counter`, `sine_wave`, `random_walk`, `dependent`, `formula`, `timestamp`, `object`. `counter` and `random_walk` are stateful. `sine_wave` is measured from sim start, not phase start.
7. **Formula references:** a bare name is a topic in the same group, listed earlier. `{Full/Topic/Path}` reaches any topic in the same phase. Cross-group formulas evaluate last. A failed formula publishes `null` with status "Bad".
8. **Naming:** sim `name` must match `^[a-z0-9_]+$`, be unique, and not match a bundled sim. A rejected definition writes nothing.
9. **Update restarts a running sim.** `update_simulator` stops, rewrites and restarts. Expect a data gap and a counter reset (observed on a restart, §3 row 6). Do not edit live during class.
10. **A broker must be connected to start.**
11. **Always create through `create_simulator`.** Hand-placed files skip validation.

## 3. Behaviors measured by the probe and the real sim (P, O)

Probe `probe_counter_test` (since deleted) ran four 20-second phases at a 2-second interval and was read by polling `get_tag` and the MQTT client. Row 6 was observed on the real sim.

| # | Question | Result | Rule for us |
| --- | --- | --- | --- |
| 1 | Does `counter` with `step: 0` hold its value? | **Yes.** `Count` stayed at 151 through the phase and kept publishing. | Use `step: 0` for counters in Setup and Faulted phases. |
| 2 | What happens when a phase omits a topic? | **It stops publishing.** Its timestamp froze while others kept updating, and a subscriber sees the old value, not zero. | Never omit a topic. Publish it with `step: 0` or `static`. |
| 3 | Does a counter resume when its phase is re-entered? | **Yes.** 151 became 152 in phase 4. | Counters are cumulative across the loop. |
| 4 | Does `random_walk` resume or restart at `start`? | **Not proven.** No jump was seen. | The design does not depend on it. |
| 5 | Does `formula` honor `decimals: 0`? | **Yes.** `Derived` read 70 for `Count` 139 and 76 for `Count` 151, half-up rounding. | Formula decimals can be trusted. |
| 6 | Do counters reset after Stop and Start? | **Yes (observed Oct 20, real sim).** Walker restarted `fourzero_printing_press1` at about 11:43 CDT. At about 11:58 CDT, with 917 s of runtime and the sim in job 105 Run 1, good meters read 1,995 and rejects 81. That equals one pass through the loop from zero. Without a reset the counters would be in the thousands. The loop starts over as well. | Do not stop, start or update the sim during class. Treat a counter drop to 0 as a restart downstream. |

## 4. What the SteelCo definitions teach us (J, O)

**Patterns worth copying**

- **Every phase republishes every topic.** Stopped equipment is the same topic with `static 0`.
- **Equipment, then PLC node, then signal.** Raw controller data sits under a `PLC` node.
- **Plain generators for process values.** `random_walk` with start, step, min, max and decimals, with a band per phase.
- **Correlated signals through `formula` plus `noise`.** The Stand3 sim sets `HydraulicPressure` from `BearingStressIndex`, and a formula can read an earlier formula in the same group.
- **Fault injection as a long phase.** Stand3 runs Normal for 300 s then Fault for 60 s, looped. Healthy assets repeat their baseline so only one asset moves.
- **PLC housekeeping tags (Racine, O):** `Connected`, stack light bools, `CycleCount`.

**Patterns to avoid**

- **The `object` wrapper on numeric tags.** Rolling Mill wraps most tags as `{value, timestamp, quality}` with a fake timestamp starting at 1700000000000 (November 2023). The engine wraps it again, so a consumer sees `value.value`. Use plain generators only.
- **Phases without `duration_seconds`.** `MillStatus` flaps every few seconds. Give every phase an explicit duration.
- **MES-layer and shift tags in a plant sim:** `ShiftNumber`, `*ThisShift`, `MillYield`, `OEE/*`, `DowntimeReasonCode`, `Orders/*`, `Scheduling/*`. They break the raw-only rule.
- **Fractional counter steps.** SteelCo's step 6.8 reads 367.20000000000033 live, so `counter` ignores `decimals`. Use integer steps and round downstream.
- **Counters publish as floats** (`54.0`). Cast downstream.
- **Spaces in topic levels are fine.** Earlier drafts told us to avoid them. SteelCo uses spaces, and a dot and spaces both worked in the real build.

## 5. Naming rules

- Topic root: `Enterprise/Site/Area/Line/<Station>/<Signal>`. Human-readable levels are fine, spaces included. Tag names are PascalCase with no spaces.
- PLC state and counters go under a `PLC` node so raw registers are separable from process values.
- Units go in `units` only. Never put status text there.
- Sim `name`: lowercase, digits, underscores. `topic_prefixes` is informational and lists the line root.
- `description` is one paragraph and says plainly that the sim is raw layer only.
- Phase names can carry the fault description. They make the definition readable but do not appear in the published data.

## 6. How to model a line with these generators

| Need | Pattern | Caveat |
| --- | --- | --- |
| Machine state | One phase per state, with a `static` numeric code and an explicit `duration_seconds`. Loop with `sequential`. | The sequence is fixed. Variety comes from phase order and durations. |
| Fault code | `static` code inside each fault phase. One phase per fault. | Avoid `random_choice` for codes. It flaps on every publish. |
| Process values | `random_walk` with a band per phase. `formula` plus `noise` for correlated values. | Stopped phases repeat the topic with `static 0`. |
| Production counter | `counter`, integer step. Speed is the step per sample over the interval. | In stopped phases use `step: 0` (probe #1). Never omit it (probe #2). |
| Reject counter | **A separate `counter`.** | Do not use a formula off the good counter. A multiplier on a cumulative count jumps at every job change. |
| Product code and lane register | `static`, changed at the Setup phase boundary. | Raw register only, no order linkage. |
| Variable cycle time | One block of phases per job, each with its own step. | Counter integer steps only, so sim speed is a rounded fraction of ideal. |
| Planned and shutdown stops | A Stopped phase, with speeds `static 0`. | No clock awareness. It is a phase, not a schedule. |

**Design consequence:** every phase repeats every topic. The printing sim has 35 phases and 16 topics, so 560 entries. Generate the JSON from the spec tables and never edit it by hand. The spec stays the single source of truth.

## 7. Build procedure (MCP)

1. Finalize the Sim Spec (namespace, tags, jobs, loop table).
2. Probe anything unproven (§3 is done for counters).
3. Generate the full definition JSON from the spec tables.
4. Call `create_simulator` with the JSON string. Read any validator message and fix only the field it names. No blind retries.
5. `list_simulators`: confirm the sim is loaded and not marked invalid.
6. Confirm a broker is connected, then `start_simulator`.
7. Verify (§8), then hand off for wiring.
8. After launch, use `update_simulator` only when needed (it restarts the sim and resets the counters). Never `delete_simulator` without Walker's confirmation. It is permanent.
9. Deleting a sim removes its definition but not the tags it already published. Those stay cached in the namespace until they are cleared in the UNS Browser or UNS Studio restarts. Build throwaway probes under their own root (for example `Probe/...`) so they are easy to find and clear.

## 8. Post-build verification checklist

Poll the MQTT client or `get_tag`, since history is unavailable.

- Sim listed, not invalid, runtime advancing
- `search_tags` on the line root returns every topic in the Sim Spec
- No value is `null` or status "Bad"
- Each value sits one level inside the envelope, with no nested `value.value`
- Machine state cycles through every code in the spec, and each state dwells for its `duration_seconds`
- Each fault code appears at least once with the spec duration
- Good counter is monotonic over a full loop, and holds during stops
- Reject counter never exceeds the good counter's step logic and never decreases
- Raw-only audit: no topic named or behaving like OEE, availability, work order, schedule, downtime reason, shift, crew, operator or "ThisShift"
- Ignition can read `value` from the envelope (Hour 4 gate)

**Indirect checks that work without watching every phase:** compare the counters against the loop table. In the printing sim, good meters read 975 and rejects 36 at the start of job 103 Setup, which equals the arithmetic for jobs 101 and 102. After the restart, they read 1,995 and 81 nine samples into job 105 Run 1, which matches too. A counter that matches the table means the phases ran in the right order.

**The runtime counter** (`runtimeSeconds` from `list_simulators`) ran about 19 to 33 seconds ahead of the loop position in the printing sim. Use it to see that the sim is alive, not to time phases.

## 9. Lessons from the real build (B)

- A 35-phase, 16-topic definition (560 topic entries) passed `create_simulator` on the first call. Generating from the spec tables works.
- Spaces and a dot in topic levels work in UNS Studio. All 16 tags were found by `search_tags` and the MQTT client shows the paths unchanged. Ignition, Maestrohub and Timebase are untested.
- **Datatype changes between phases for the same tag.** `static 0` publishes as integer and `random_walk` and `counter` publish as float. Whether `static 0.0` publishes as float is untested. Until it is, consumers must cast.
- **Cycles per job were a build choice.** 5 cycles per job would have meant about 55 phases. 3 cycles gave 35 and a 17.4-minute loop, long enough to show every fault type and short enough for class.
- **Fault duration follows fault type,** not position in the cycle. Keep it that way when regenerating.
- **Datasets that look wrong can be right.** Rejects stay flat during over-temp and RTO faults on purpose. Only web breaks scrap web.
- **A deleted sim leaves its tags behind.** The probe's four tags stayed in the namespace after the sim was deleted, and the MCP tools cannot remove them.
- **A restart resets the counters and the loop.** Observed after Walker restarted the sim (§3 row 6). A restart in class would look like a drop to 0 downstream.

## 10. Skeleton (pattern only)

Placeholders in angle brackets come from the Sim Spec. Plain generators, explicit durations, and counters held with `step: 0` in the faulted phase (probe #1). Do not omit topics (probe #2).

```json
{
  "name": "<winner>_line_raw",
  "pretty_name": "<Line name> (Raw Layer)",
  "category": "Manufacturing",
  "description": "Raw process values and PLC state/counter registers for a single production line. No MES data is simulated.",
  "update_frequency": "2 seconds",
  "cycle_mode": "sequential",
  "topic_prefixes": ["<Enterprise>/<Site>/<Area>/<Line>"],
  "phases": [
    {
      "name": "Running",
      "interval_seconds": 2,
      "duration_seconds": 50,
      "groups": [
        {
          "topic_prefix": "<Enterprise>/<Site>/<Area>/<Line>/PLC",
          "topics": [
            { "topic": "MachineState", "generator": { "type": "static", "value": 1 } },
            { "topic": "FaultCode", "generator": { "type": "static", "value": 0 } },
            { "topic": "GoodMeters", "units": "m", "generator": { "type": "counter", "start": 0, "step": 5 } },
            { "topic": "RejectMeters", "units": "m", "generator": { "type": "counter", "start": 0, "step": 0 } }
          ]
        },
        {
          "topic_prefix": "<Enterprise>/<Site>/<Area>/<Line>/<Station>",
          "topics": [
            { "topic": "Speed", "units": "m/min", "generator": { "type": "random_walk", "start": 150.0, "step": 2.0, "min": 145.0, "max": 155.0, "decimals": 1 } }
          ]
        }
      ]
    },
    {
      "name": "Faulted - <Fault 101>",
      "interval_seconds": 2,
      "duration_seconds": 10,
      "groups": [
        {
          "topic_prefix": "<Enterprise>/<Site>/<Area>/<Line>/PLC",
          "topics": [
            { "topic": "MachineState", "generator": { "type": "static", "value": 3 } },
            { "topic": "FaultCode", "generator": { "type": "static", "value": 101 } },
            { "topic": "GoodMeters", "units": "m", "generator": { "type": "counter", "start": 0, "step": 0 } },
            { "topic": "RejectMeters", "units": "m", "generator": { "type": "counter", "start": 0, "step": 2 } }
          ]
        },
        {
          "topic_prefix": "<Enterprise>/<Site>/<Area>/<Line>/<Station>",
          "topics": [
            { "topic": "Speed", "units": "m/min", "generator": { "type": "static", "value": 0 } }
          ]
        }
      ]
    }
  ]
}
```

## 11. Open items

- `random_walk` continuity across phases is unproven.
- **A dot in a topic level breaks Ignition**, because Ignition does not allow `.` in tag names. The print sim's root was renamed from `4.0 Printing` to `40Printing` (DEC-005). Do not put dots in topic levels. Spaces work in Ignition MQTT Engine.
- Whether `static 0.0` publishes as float is untested.
- **Probe cleanup.** The probe sim `probe_counter_test` was deleted on Oct 20 with Walker's approval. Its four cached tags are still in the namespace (`Probe/CounterTest/Count`, `Derived`, `Phase`, `Walk`). The MCP tools cannot remove them. Clear them in the UNS Browser before students connect, or tell students to ignore `Probe/`. Do not restart UNS Studio to clear them, because that resets the print sim's counters.
- The historian is off, so history-based verification is unavailable.

*Closed Oct 20: counter reset on Stop and Start (observed, §3 row 6).*
