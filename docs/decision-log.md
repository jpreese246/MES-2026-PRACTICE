# Decision Log

**Project:** MES Workshop 2026
**Maintained by:** the PM
**Format:** Reverse chronological. Superseded decisions are ~~struck through~~ with a pointer to the decision that replaced them — never deleted.

---

## How to use this log

Every significant architectural, tooling, process or product decision is recorded with: the decision, the options considered, the rationale, who made the call, and the cost of reversing it. **🔴 High reversal cost** decisions warrant extra deliberation before changing.

## Entry template

```
### DEC-NNN — {decision headline}

**Date:** YYYY-MM-DD
**Status:** Proposed | ✅ Accepted — {who}, YYYY-MM-DD | ~~Superseded by DEC-MMM~~
**Reversal cost:** 🟢 Low | 🟡 Moderate | 🔴 High
**Affects:** files, components, docs

**Context:** what forced the decision, verified by reading (not recalled).
**Options:**
1. {option} — pros / cons
2. {option} — pros / cons
**Decision:** what was chosen.
**Rationale:** why.
**Consequences:** what this commits us to, and what it rules out.
```

---

## Log

### DEC-006 — Repo moved to `iiot-university`, private

**Date:** 2026-10-21
**Status:** ✅ Accepted — Walker, 2026-10-21
**Reversal cost:** 🟢 Low
**Affects:** git remote `origin`, `docs/claude_project_instructions.md`

**Context:** The repo was created as `40solutions/mes-workshop-2026`. Walker: "its supposed to be private in iiot-university not 40solutions".
**Decision:** Transferred it with GitHub's repo transfer (history kept, still private) to `iiot-university/mes-workshop-2026`. Local `origin` repointed.
**Consequences:** The old URL redirects. New clones use https://github.com/iiot-university/mes-workshop-2026.

### DEC-005 — Topic root renamed `4.0 Printing` → `40Printing`

**Date:** 2026-10-20
**Status:** ✅ Accepted — Walker, 2026-10-20
**Reversal cost:** 🔴 High (every consumer path, and another sim reimport resets the counters)
**Affects:** the sim definition, every topic path in `docs/`, MQTT Engine namespace, all future Ignition/Maestrohub/Timebase paths

**Context:** The project rules allowed renaming the first level only with Walker's approval and only if a consumer misbehaved with it. The dot broke Ignition (Ignition does not allow `.` in tag names). The documented fallback `4.0Printing` keeps the dot, so it would not have helped.
**Decision:** Root is `40Printing`. Walker had VERA rename it and reimported the sim at ~13:45 CDT (this reset the counters and restarted the loop, before students connected). Display text still says "4.0 Printing" — it is the company name.
**Consequences:** PM verified all 16 topics live under `40Printing/Dallas/Press Room/Press 1/` on `coreflux:1883` (~14:10 CDT). Stale `4.0 Printing/…` copies remain in UNS Studio's namespace, Notus and probably the MQTT Engine tag provider; never read them. Repo docs and `docs/sim/fourzero_printing_press1.json` need syncing (PM; sim JSON only as a byte-for-byte copy from UNS Studio). Spaces in lower levels are unchanged.

### DEC-004 — Sim repointed to this stack's CoreFlux (INFRA-004)

**Date:** 2026-10-20
**Status:** ✅ Accepted — Walker, 2026-10-20
**Reversal cost:** 🟡 Moderate (another repoint risks a sim restart and counter reset)
**Affects:** UNS Studio broker connection, `docs/architecture.md` §1, §5

**Context:** The sim published to `coreflux-mqtt` (project `notus-dev`, host 1884), outside this stack. INFRA-001 deployed CoreFlux 2.2.0 on host `127.0.0.1:1886`.
**Decision:** Walker repointed the UNS Studio sim to `127.0.0.1:1886`. Walker: "sim is pointed at 1886, no restart".
**Rationale:** The MES stack owns its broker; one cut-over before students pull data.
**Consequences:** The old broker is out of the path. PM verified all 16 topics under `4.0 Printing/Dallas/Press Room/Press 1/` arriving on `coreflux:1883` (2026-10-20). Do not repoint again during class.

### DEC-003 — Dev stack host ports bind to localhost only; students use their own broker

**Date:** 2026-10-20
**Status:** ✅ Accepted — Walker, 2026-10-20
**Reversal cost:** 🟢 Low
**Affects:** `docker-compose.yml` port bindings, `docs/development_philosophy.md` §Security

**Context:** INFRA-001 binds every host port to `127.0.0.1`. The PM asked whether students would connect to Walker's broker or gateway from their own machines.
**Options:**
1. Keep `127.0.0.1` — nothing on Walker's Mac is exposed to the room.
2. Bind `0.0.0.0` so students can reach Walker's CoreFlux/Ignition — needs auth thought.
**Decision:** Option 1. Students connect to their own broker, or Walker republishes to a public broker for them.
**Rationale:** Walker, 2026-10-20: "students will connect to their own broker (or I will publish to a public broker for them)".
**Consequences:** No LAN exposure of this stack. If Walker publishes to a public broker, that is a separate bridge/republish task, specced when he asks.

### DEC-002 — Day 1: Ignition MQTT Engine subscribes to CoreFlux directly

**Date:** 2026-10-20
**Status:** ✅ Accepted — Walker, 2026-10-20
**Reversal cost:** 🟢 Low
**Affects:** UNS-002, VIS-001; deferred: INFRA-003 (Maestrohub), UNS-001; `docs/architecture.md` §1

**Context:** The approved data flow (`docs/mes_requirements.md` §8) routes sim → CoreFlux → Maestrohub → Ignition. Maestrohub is not in this stack yet, and the Day 1 goal is process visuals in Perspective.
**Options:**
1. Build Maestrohub ingest first (INFRA-003, UNS-001), then Ignition.
2. Ignition's MQTT Engine subscribes to the sim topics on CoreFlux directly; visuals bind to MQTT Engine tags.
**Decision:** Option 2, for testing. Walker, 2026-10-20: "ignition will sub to coreflux and visuals will publish from mqtt engine just for testing".
**Rationale:** Fastest path to live tags for today's visuals.
**Consequences:** UNS-002 configures MQTT Engine against `coreflux:1883`. Envelope unwrap and casting happen in Ignition for now; the Maestrohub path (INFRA-003, UNS-001) is deferred, not dropped — revisit before the Core Four build.

### DEC-001 — Two-session PM/Dev workflow, files as the only channel

**Date:** 2026-10-20
**Status:** ✅ Accepted — inherited from `mes-dev-template`
**Reversal cost:** 🟡 Moderate
**Affects:** `.claude/skills/pm/SKILL.md`, `.claude/skills/dev/SKILL.md`, all of `docs/`

**Decision:** One Claude Code session runs `/pm` (specs, docs, verification; no production code); a second runs `/dev` (implements one spec). They never share a chat; the Dev reports through the spec's `Dev Report` and `agent_handoff.md`. No root `CLAUDE.md` — the operating manual is `docs/claude_project_instructions.md`.

**Rationale:** Separating author from verifier stops an agent grading its own work. Files survive `/clear` and session restarts; chat does not.
