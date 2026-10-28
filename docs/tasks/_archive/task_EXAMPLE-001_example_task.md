# EXAMPLE-001 — Add a health-check endpoint to the ingest service

> **This is a format example shipped with `mes-dev-template`.** It shows what a PM-authored spec looks like and where the Dev writes its report. Replace it with your first real task, or move it under `docs/tasks/_archive/`. The project details below are illustrative.

**Status:** 📝 Specced — not yet run by the Dev
**Priority:** P2 · **Effort:** S (one Dev run)
**Depends on:** —
**Bug:** —

---

## Background

Nothing can tell whether the ingest service is up without reading its logs. `docker compose ps` shows the container running even when the service inside has lost its broker connection. After this task, `curl localhost:8000/health` returns the service's real state, and Compose uses it as the container healthcheck, so "running" means "working."

## What Already Exists (Do Not Rewrite)

- `services/ingest/app.py` — the service entrypoint and its MQTT client (`client`, created at module scope). Do not change how the client connects or subscribes.
- `docker-compose.yml` service `ingest` — keep its image, ports and env as they are; only add a `healthcheck`.

## What to Build

1. In `services/ingest/app.py`, add `GET /health` returning:
   - `200 {"status": "ok", "broker": "connected"}` when `client.is_connected()` is true
   - `503 {"status": "degraded", "broker": "disconnected"}` otherwise
   No other fields. No authentication (the port is bound to localhost).
2. In `docker-compose.yml`, add to `ingest`:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"]
     interval: 10s
     timeout: 3s
     retries: 3
   ```
3. In `docs/architecture.md` §2, add `/health` to the ingest row (Rule 11 — contract doc in the same commit).

## Acceptance Criteria

- [ ] `curl -s -o /dev/null -w '%{http_code}' localhost:8000/health` → `200` with the broker up
- [ ] Stopping the broker container makes the same call return `503` within 30 s
- [ ] `docker compose ps` shows `ingest` as `healthy` with the broker up
- [ ] `docker compose config -q` exits 0
- [ ] No changes to MQTT connect/subscribe logic
- [ ] `docs/architecture.md` lists the endpoint

## Files to Modify

| File | Change |
|---|---|
| `services/ingest/app.py` | Add `/health` handler |
| `docker-compose.yml` | Add `healthcheck` to `ingest` |
| `docs/architecture.md` | Add the endpoint to the components table |

## Dev Instructions

Read this spec in full before writing any code. Add a `GET /health` endpoint to `services/ingest/app.py` that reports the MQTT client's connection state (200/503, exact bodies above), wire it as the `ingest` container's Compose healthcheck, and list it in `docs/architecture.md`. Do not touch the MQTT connect/subscribe code or any other service. Run `docker compose config -q` and the curl checks in the Acceptance Criteria, and paste their output into the Dev Report. Do not commit unless the lead asks.

---

## Dev Report

*(Written by the Dev. The PM reads this, then verifies against the actual files.)*

**Status:** —
**Date:** —

**What was built:**
- —

**Files changed:**
| Path | Created / Modified / Deleted |
|---|---|
| — | — |

**Gate results** (commands and actual output, pasted):
```
—
```

**Deviations from spec:** —

**Open questions for the PM:** —

---

## PM Verification

*(Written by the PM after reading the changed files — Rule 7.)*

**Result:** —
**Findings:** —
