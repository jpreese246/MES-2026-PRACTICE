# Bug Log

**Project:** MES Workshop 2026
**Maintained by:** the PM
**Format:** Reverse chronological. A bug is logged when found, updated when investigated or specced, and marked Fixed with a root-cause note only after the fix is verified (Rule 7). Read this before touching a previously-buggy area.

---

## Entry template

```
## BUG-NNN — {short headline} ({P0–P3}, {Open | Specced | Fixed})

**Found:** YYYY-MM-DD by {who}, {where — build, environment}
**Spec:** `docs/tasks/task_BUG-NNN_<slug>.md` (once specced)

**Symptom:** what was observed, exactly.
**Root cause:** what was actually wrong — from logs, grep, or a query, not inference.
**Fix:** what changed (filled in at close-out).
**Trap to remember:** the pattern that will cause this again, if there is one.
```

---

## BUG-001 — Ignition MQTT Engine connects and drops every ~3 s against CoreFlux (P1, Fixed — workaround)

**Found:** 2026-10-20 by Walker, Ignition 8.3.10 gateway log (MQTT Engine server "MES Coreflux", client ID `ignition-client`, `tcp://coreflux:1883`)
**Spec:** none — external broker defect; workaround is an Ignition gateway setting (Walker, GUI)

**Symptom:** `TahuClient` ERROR `Failed subscribe on [#, spBv1.0/#, spBv1.0/STATE/IamHost] granted QoS [0, 0, 1] != [1, 0, 0]`, then reconnect, repeating every ~3 s.
**Root cause:** CoreFlux 2.2.0 returns the SUBACK granted-QoS list in the wrong order when one SUBSCRIBE carries topics with mixed QoS. PM reproduced with paho 1.6.1 against `127.0.0.1:1886` (2026-10-20): requested `[0,0,1]` → granted `[1,0,0]`; requested `[1,0,0]` → `[1,0,0]`; `[0,0]` → `[0,0]`; `[1,1,1]` → `[1,1,1]`. MQTT Engine checks granted against requested in order, treats the mismatch as a failed subscribe, and disconnects. The QoS 1 entry is the Sparkplug primary-host STATE topic (`spBv1.0/STATE/IamHost`).
**Fix:** Workaround by Walker in the gateway UI, 2026-10-20 ~13:59: MQTT Engine server `MES Coreflux` now has `enablePrimaryHostSubscriptions: false`, so it no longer subscribes to `spBv1.0/STATE/…` at QoS 1. PM verified from the gateway config file and the log: last reconnect 13:59:01, none in the following 10+ minutes. The broker defect itself is unfixed (not reported to CoreFlux yet).
**Trap to remember:** Any client that subscribes to several topics with mixed QoS in one SUBSCRIBE will see this against CoreFlux 2.2.0 — check Maestrohub and Timebase (INFRA-003) for the same pattern. Keep subscription QoS uniform per client.

