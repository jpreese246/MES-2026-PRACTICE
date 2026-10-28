# About 4.0 Printing — Simulated Plant & Value Stream

*Status: v1.0, Oct 20, 2026. Walker's Hour 2 decisions are in, and this matches the sim as built. All items VERA proposed were confirmed by Walker on Oct 20. Walker is the printing SME, so his word overrides anything here. Read with `sim_spec_press1.md` and `mes_requirements.md`.*

This is the story document: who the company is, what the plant makes, and how material flows. The Sim Spec turns it into tags. The MES Requirements turn it into functions.

**How this document is used**

- The Sim Spec's namespace, line layout and scenarios must trace back to this page.
- The MES Requirements' work orders, scheduling and downtime model draw their vocabulary from the value stream below.
- The AI agents (Day 1 co-architect, Day 2 analytics) read this first for business context. Anything not written here, they should ask about rather than assume.
- **Fictional company.** Nothing here describes a real business. The repo README says so too.

## Decisions locked (Walker, Oct 20)

| Decision | Detail |
| --- | --- |
| Process | Flexographic printing, 8 colors, heat-tunnel (hot-air) drying |
| Key process variables | Tunnel temperature and web tension |
| Interlock | The RTO (regenerative thermal oxidizer) has an inhibit on running the press. The RTO inhibit is an alarm. |
| MES scope | The print process only. Nothing upstream or downstream is in the MES. |
| Company and sim | New fictional company, "4.0 Printing". New sim. |
| Alarms (unplanned, read from the PLC state and fault code) | Web break (101), tunnel over-temperature (102), RTO inhibit (103) |
| Derived unplanned reason | Changeover overrun: Setup time beyond the scheduled changeover time |
| Planned downtime | Changeover up to the scheduled time. Clean plates and roll change, which operators log in the MES front end. |
| Planned stop logging | MES front end and database. Also published to the UNS by the MES. Never simulated. |
| Planned stop that overlaps PLC Running | Flagged as a conflict, not blocked |
| Starved and blocked | Excluded |
| Fault mix | Weighted, web break is the most common |
| Fault cadence | About a 10-second fault every 60 seconds |
| Variable cycle time | Every job runs its own speed, lane count and length |
| Manual processes | Manual steps the MES cannot see or control, especially around scheduling (§5.1) |
| Units | Temperature in °F, output in meters |
| Product table, scheduled changeovers, overrun jobs, drift job | Confirmed as written in §3 and §5 |
| Reject rate on drift job 105 | About 20% of good meters is accepted as a deliberate drift job |
| Topic names | Human-readable, delegated to VERA (Sim Spec §2) |

## 1. Company Snapshot

| Item | Detail |
| --- | --- |
| Company name | 4.0 Printing |
| Industry / sector | Flexible packaging. Flexographic printing of film for food and beverage packaging. |
| Origin story | Started as a regional label printer in the 1990s and moved into flexible packaging film as customers asked for bag and pouch stock. *(fictional)* |
| Size | About 150 employees, one plant, roughly $40M in revenue. |
| Known for | Fast turnaround on short and medium runs, and tight color matching. |
| Customers (type, not names) | Food and beverage brand owners and bag converters: snack, coffee, frozen food, pet food. |
| Why they need an MES now | The schedule lives in a spreadsheet and on a whiteboard. Planners and press crews disagree about what runs next. Downtime is written on paper at end of shift. OEE is calculated by hand once a month. Rush jobs reshuffle the week. Nobody can say what a changeover really costs. |

## 2. Plant Snapshot

| Item | Detail |
| --- | --- |
| Plant name | Dallas Plant |
| Location | Dallas–Fort Worth, Texas |
| Plant role | Prints and converts flexible packaging film. Only the print process is in scope. |
| Lines in the plant | A press hall with several presses. The workshop MES covers Press 1 only. Other presses are not described or simulated. |
| **The line we are simulating** | **Press 1**: an 8-color flexographic press with a hot-air tunnel dryer |
| Operating pattern | 24 hours a day, 5 days a week, three shifts. Context only. Shift and crew data are never simulated. |
| Environment notes | Humidity-controlled press hall. The tunnel dryer is the main process interlock: too hot damages the film, too cool leaves wet ink. |
| Solvent exhaust and the RTO | Dryer exhaust goes to a regenerative thermal oxidizer. If the RTO inhibits, the press cannot run. |

## 3. Products

Press 1 prints film for different customers in 2-wide or 4-wide web layouts. Each job is one print run with its own substrate, lane count, colors and speed. Walker confirmed this table as the working set.

| Product code | Product family | Substrate | Lanes | Colors | Ideal speed | Scheduled changeover (sim time) | Changeover impact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 101 | Snack bag film | OPP | 4-wide | 5 | 250 m/min | 20 s | Low after another OPP job. High after dark coverage. |
| 102 | Coffee pouch film | PET | 2-wide | 8 | 180 m/min | 30 s | High. Full color set, tight registration. |
| 103 | Frozen food bag film | PE | 4-wide | 4 | 200 m/min | 24 s | Medium. Substrate change from OPP or PET. |
| 104 | Candy wrapper film | OPP | 2-wide | 6 | 220 m/min | 20 s | Low after 101, medium after others. |
| 105 | Pet food bag film | PE | 2-wide | 7 | 160 m/min | 30 s | High. Heavy ink coverage, slower speed. |

- **SKUs the line runs:** 5 job types.
- **Scheduled changeover time:** the planned allowance for getting from one job to the next. Setup up to it is planned. Setup beyond it is unplanned. Times are compressed for the classroom. Real changeovers take tens of minutes.
- **Unit of measure:** linear meters of printed web. The press counts meters. The MES multiplies by lanes for lane-meters.
- **Good versus reject:** good meters are web printed within registration and color spec. Rejects are web wasted at startup, after a web break, or out of registration or color. The PLC counts both.
- **Product identity in the PLC:** the operator sets a job code at setup, and a separate lane register shows 2 or 4. Neither carries any order information. This is the settled policy (raw registers, no order linkage).

## 4. The Value Stream

One line, in flow order, from substrate in to printed roll out. Steps marked "not simulated" matter to the story but publish no data.

### 4.1 Summary

A roll of film substrate is mounted on the Press 1 unwind and spliced into the web. The web runs under controlled tension through eight flexo print stations, each laying down one color. It then passes through a hot-air tunnel dryer that sets the ink, with exhaust to the RTO, over chill rolls past an in-line inspection point, and onto the rewind as a printed roll. Plates, cylinders and ink are prepared by hand before the job starts, and the customer proof is approved by a person. Printed rolls are staged and moved by hand to laminating and slitting, which are outside the workshop MES. Each job has its own speed, lane count and length, so the press never runs at a single rate for long.

### 4.2 Process steps

| # | Step / station | What happens | Material in | Material out | Equipment / PLC | Rate | Buffer after step |
| --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | Prepress and proof approval *(not simulated)* | Artwork is approved by the customer and plates are made | Artwork, proof | Approved plates | Manual | n/a | Plate rack |
| U2 | Plate, cylinder and anilox prep *(not simulated)* | Plates are mounted and print units are made ready | Plates, sleeves | Ready print units | Manual | n/a | Staged at press |
| U3 | Ink mixing and viscosity prep *(not simulated)* | Ink is mixed and viscosity set for the job | Ink, solvent | Ink at spec | Manual | n/a | Ink kitchen |
| U4 | Substrate staging *(not simulated)* | Film rolls are staged at the press | Film rolls | Roll at unwind | Manual | n/a | Staging rack |
| 1 | Unwind and splice | The roll is mounted and spliced, and web tension is controlled | Film roll | Web under tension | Press 1 PLC | Job speed (§3) | None (continuous web) |
| 2 | Print stations 1–8 | Each unit lays down one color and holds registration | Web | Printed web, ink wet | Press 1 PLC | Job speed | None |
| 3 | Tunnel dryer | Hot air dries the ink. Tunnel temperature is a critical variable. Exhaust goes to the RTO, which can inhibit the press. | Wet printed web | Dry printed web | Press 1 PLC (tunnel zones, RTO inhibit) | Job speed | None |
| 4 | Chill and inspect *(not simulated in v1)* | Chill rolls cool the web. In-line check for registration and defects. | Dry printed web | Cooled web | Press 1 hardware, no tags in the sim | Job speed | None |
| 5 | Rewind | The finished printed roll is wound at controlled tension | Cooled web | Printed roll | Press 1 PLC | Job speed | Printed roll staging |
| D1 | Roll staging and handoff *(not simulated)* | Printed rolls are staged and moved by hand | Printed roll | Roll at next step | Manual | n/a | Staging area |
| D2 | Laminating *(not simulated)* | Printed film is laminated | Printed roll | Laminated roll | Not in scope | n/a | n/a |
| D3 | Slitting, pack and ship *(not simulated)* | Rolls are slit, packed and shipped | Laminated roll | Finished goods | Not in scope | n/a | n/a |

### 4.3 Flow sketch

`[Substrate roll] -> [Unwind + splice] -> [Print stations 1-8] -> [Tunnel dryer] -> [Chill + inspect] -> [Rewind] -> [Printed roll staging] -> (laminate, slit, ship: not simulated)`

Tunnel dryer exhaust goes to the RTO. The RTO can inhibit the press. Manual inputs to the press before each job: plates and cylinders, ink, proof approval, substrate roll. Replace this sketch with a diagram when time allows.

### 4.4 Line characteristics

| Characteristic | Answer |
| --- | --- |
| Pace-setting step | The tunnel dryer. It limits maximum press speed for a given job and substrate. |
| Where WIP builds up when something stops | Printed rolls pile up in staging ahead of laminating. Upstream, prepared plates and ink wait at the press. |
| Which step stopping stops the line | Any step. Press 1 is one continuous web. |
| Buffered steps | None inside the press. Upstream prep and downstream laminating are buffered by staging. |
| Where quality is checked | In-line inspection at step 4 for registration and defects, plus a manual end-of-roll sample check. Neither publishes a signal in v1. |
| Where product identity is set | At setup, by the operator, in the press HMI. This sets the product code and lane count registers. |
| Line-level ideal rate | **Not one number.** Ideal rate is set per product (§3), in m/min. The MES holds these as master data for the OEE ideal cycle time. |

## 5. How the Line Misbehaves

These are plant facts the Sim Spec reproduces. They are not MES data.

**Cadence (Walker):** about a 10-second stop every 60 seconds. As built, runs last 48 to 52 seconds and stops last 8 to 12 seconds. This is deliberate classroom time compression. Real stops last minutes and happen every few hours. Students will ask. It is a teaching choice, not a plant claim.

**Fault mix as built:** 15 faults per 17.4-minute loop. Web break 9 (60%), tunnel over-temp 4 (27%), RTO inhibit 2 (13%). Web break is the most common. Over-temps happen on jobs 101, 103, 104 and 105. RTO inhibits happen on jobs 102 and 105.

| Event type | Physical cause | In the sim | Duration | What the PLC shows (raw only) |
| --- | --- | --- | --- | --- |
| Alarm: **web break** (most common) | Tension spike, weak film or a failed splice | 9 per loop | 8 or 10 s | Faulted (3), fault code 101, speed 0, tension 0, meters hold, reject meters step |
| Alarm: **tunnel over-temp** | Heater control trip or high zone temperature | 4 per loop | 12 s | Faulted (3), fault code 102, zone temperatures above the normal band, speed 0 |
| Alarm: **RTO inhibit** | The oxidizer inhibits the press | 2 per loop | 12 s | Faulted (3), fault code 103, `RTOInhibit` true, speed 0 |
| Changeover (planned) | New plates, ink and web setup | Every job | Up to the scheduled time | Setup (2), fault code 0, product code and lane registers change, speed 0 |
| Changeover overrun (unplanned) | Setup takes longer than scheduled | Before jobs 102 and 104 | 14 s over each | Setup (2) still showing after the scheduled time. The allowance is not in the sim. |
| Quality drift | Registration or color drifts | Job 105 | Whole job | Registration error and ink viscosity above normal. Reject meters rise on every Run sample. |
| Planned stops: clean plates, roll change | Routine plate cleaning, roll out or rewind full | **Not in the sim** | n/a | Nothing. The press keeps showing Running. Operators log them in the MES. |
| Micro-stop, slow running, starved, blocked | n/a | **Not in v1** | n/a | n/a |

The sim publishes only the PLC state, fault code and raw process values. The three alarms are read straight from the state and fault code, with no operator entry. Changeover overrun needs one more fact the sim does not carry, the scheduled changeover time, which comes from the MES.

**Timing notes for the MES (Day 2):** the sim publishes every 2 seconds, so a stop yields 4 to 6 samples. A 2-sample (4 s) debounce catches every stop. Availability (Running against Running plus Faulted) is 82.9%. With planned setup excluded and overrun counted as unplanned it is about 80.4%. Quality is about 96% on jobs 101 to 104 (web break rejects only), about 81% on job 105, and about 93.7% over a loop. Calibrate OEE targets to these (Sim Spec §9).

### 5.1 Manual processes the MES cannot see

Walker's requirement: a plant with real manual steps that are hard to work around. In a raw-only sim these steps leave no signal. That gap is the teaching point.

| Manual step | Who | Why the MES cannot see it | Effect on the schedule | What the PLC shows (raw only) |
| --- | --- | --- | --- | --- |
| Plate, cylinder and anilox readiness | Pressroom crew | No signal. A person decides the print units are ready. | Gates every job start. The MES can schedule a job whose plates are not ready. | Setup running past the scheduled time, which the MES classifies as changeover overrun |
| Ink mixing and viscosity prep | Ink room | No signal | Delays makeready | Same as above |
| Proof approval | Customer, QA | A human judgment | A job can be held after it is scheduled | Nothing |
| Lane setup (2-wide or 4-wide) | Press operator | Chosen at setup to suit the job | Changes output per meter, so it changes OEE performance | Lane register changes after setup |
| Rush override | Scheduler, plant manager | A human bumps a job to the front. The MES records it, and publishes it to the UNS. | The MES sequence is wrong the moment it happens | A product code that does not match the schedule's next job |
| Printed roll staging and handoff | Material handler | No tracking | Downstream starvation is invisible | Nothing |
| Planned stop logging (clean plates, roll change) | Press operator | The PLC shows no stop. A person enters start, end and reason in the MES. | Removes time from planned production time | Nothing |

The MES has a manual capture surface for readiness entry, schedule override and planned stop entry. It stays correct when a human acts outside the system. A planned stop entered while the PLC shows Running is flagged as a conflict, and a job that runs out of schedule order without an override record is flagged as an unrecorded deviation (MES Requirements §4.1).

## 6. Business Context the MES Will Care About

Plain-language narrative only. None of this is simulated. All values confirmed by Walker, Oct 20.

- **Orders:** Make-to-order. The plant runs about 20 to 60 jobs a week. A job is typically 2 to 8 hours of press time. Quoted lead time is one to two weeks. Rush orders arrive a few times a week.
- **Scheduling:** Sequence is driven by due date and by changeover cost. Changeover cost depends on color count, ink coverage, substrate and a 2-wide or 4-wide lane change. Each scheduled job carries a scheduled changeover time. Schedulers group similar jobs and run light colors before dark. Plate readiness gates the start of a job. A human can override the sequence at any time.
- **Downtime:** Unplanned downtime is web breaks, tunnel over-temperature trips, RTO inhibits and changeover overrun. Changeover within the scheduled time, clean plates and roll changes are planned and reported separately.
- **Performance:** OEE target of 70%, scrap target under 4% of meters, and on-time delivery above 95%. Today these are measured by hand, monthly. Note that the sim's loop scrap is about 6.3% (job 105 drifts on purpose), so the AI has a real quality problem to find.
- **Questions leadership asks that nobody can answer today** (these become the Day 2 AI queries):
  - Which job types lose the most time to web breaks?
  - Which alarm costs the most run time, and on which job types?
  - How often does the RTO inhibit the press, and on which jobs?
  - Which changeovers run over the scheduled time, and by how much?
  - Why does OEE drop on 4-wide jobs?
  - What did the last rush job really cost in changeover and missed due dates?
  - Which job sequence gives the shortest total changeover time this week?
  - How many meters do we scrap per web break?

## 7. Trace to the Specs

| This document | Feeds | Section |
| --- | --- | --- |
| §1–§2 Company, plant, line name | Namespace (Manufacturer / Site / Area / Line) | Sim Spec §2 |
| §3 Products | Product code and lane registers, Scheduling and Work Order entities, OEE ideal rate and scheduled changeover master data | Sim Spec §6, MES §3, §4, §6 |
| §4.2 Process steps | Line layout, raw process values, PLC registers, RTO inhibit | Sim Spec §3, §5 |
| §5 Misbehavior, cadence, fault mix | Loop, fault phases, reject drift, setup | Sim Spec §4, §7, §8 |
| §5 Alarms and changeover overrun | Downtime classification | MES §5 |
| §5.1 Manual processes | Manual capture surface, planned stop table, schedule override, MES-published UNS topics | MES §3–5, §7, §8 |
| §6 Business context | Work orders, scheduling, downtime and OEE requirements | MES §3–6 |
| §6 Leadership questions | AI analytics queries | MES §9 |

## 8. Not Described Here (On Purpose)

- No simulated MES data: no work orders, schedules, OEE, downtime reasons, scheduled changeover times, planned stops, schedule overrides, shifts or crews.
- No real company, customer or supplier names.
- No other plants, presses or downstream lines. Single press only.
- No signals for prepress, ink room, laminating, slitting or shipping. Chill and inspect (§4.2 step 4) also has no signals in v1.

## 9. Open Items

None. The company snapshot, plant details, line characteristics, §6 business numbers, the dryer as pace-setting step (§4.4) and the end-of-roll sample check were confirmed by Walker on Oct 20.
