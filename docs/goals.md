# Goals (North Star)

**Project:** MES Workshop 2026
**Status:** ✅ Ratified by Walker, 2026-10-20

> Agents read this when a decision turns on priorities rather than on a settled spec. If this file is still a draft, **ask the lead rather than inventing priorities** (Rule 10).

---

## Mission

Teach workshop students to architect and build a single-line MES — Work Orders, Scheduling, Downtime Tracking and OEE — on a simulated flexographic press (4.0 Printing, Press 1), with AI working on both ends of the build.

## Success looks like

From `docs/mes_requirements.md` §11. A full 17.4-minute sim loop is the test unit.

- Over one loop the MES shows 15 alarm events (9 web break, 4 tunnel over-temp, 2 RTO inhibit), 2 changeover overruns of 14 s each, and meter totals within a few meters of `docs/sim_spec_press1.md` §9.
- Each of the five jobs completes its work order with the good and reject meters in `docs/mes_requirements.md` §3. No negative meters after a sim restart.
- Seeded in sim order, every start reconciles as a normal start, and the four reconcile outcomes each appear using the demo recipe (§4.1).
- A planned stop entered while the PLC shows Running is flagged as a conflict.
- OEE per job and per loop lands within 1 to 2 points of the §6 table (loop about 69.4%).
- Each Day 2 Hour 4 AI query in §9 returns the expected answer, or says what data it is missing.

## Priorities (ranked)

1. Live sim data ingested correctly (envelope unwrapped, values cast, meter deltas). Everything else depends on it.
2. The Core Four, in order — Work Orders, Scheduling, Downtime, OEE — each meeting its test-visual criteria by Day 2 Hours 2–3.
3. AI queries ready for Day 2 Hour 4.
4. Real visuals, built in one pass in Hour 4.

## Non-goals

- Controlling the press. The MES records and reconciles; the sim ignores it.
- Changing the sim. It is fixed for the class, and a restart resets its counters.
- Production hardening, security or scale. This is a teaching build.
- Anything in `docs/mes_requirements.md` §10: laminating, slitting, bagging, shipping, prepress, starved and blocked states, multi-line or multi-press scheduling.

## Audience / users

Workshop students building the MES in class, with Walker teaching live.

## Standing constraints that flow from the goals

- Fictional company, synthetic data only.
- Dev speed over security and QA.
- The sim is fixed; the MES adapts to it.
- Class days are Oct 20 and 22, 2026; Day 2 Hours 2–3 are test-visual build time and Hour 4 is the AI hook.
