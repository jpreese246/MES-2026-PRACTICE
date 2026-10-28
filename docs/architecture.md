# Architecture

**Project:** MES Workshop 2026
**Status:** Draft
**Last updated:** 2026-10-20 (INFRA-001 close-out)

---

## Purpose

How the system is structured: components, boundaries, data flow, and the rules that keep it that way. *Why* a structural choice was made lives in `docs/decision-log.md`; *what* the product does lives in `docs/goals.md` and the task specs.

## 1. System Overview

A single-line MES for 4.0 Printing Press 1. UNS Studio runs the raw-layer sim `fourzero_printing_press1` on Walker's MacBook Pro, the same machine that runs Docker and this repo, and publishes 16 tags over MQTT. The MES stack runs in Docker on that machine: CoreFlux is the broker, Maestrohub unwraps and casts the envelope and routes it, Ignition runs the MES logic and visuals, and PostgreSQL holds the MES records. Timebase keeps raw tag history, and Timebase Atlas models the plant for the AI agents. Ignition publishes MES results back to the UNS under `…/Press 1/MES/`. The data flow is in `docs/mes_requirements.md` §8, confirmed by Walker on Oct 20.

**Broker cut-over (done 2026-10-20, DEC-004).** The sim publishes to this stack's CoreFlux (host `127.0.0.1:1886`). The old `coreflux-mqtt` container (host 1884, project `notus-dev`) is no longer in the path.

**Day 1 interim path (DEC-002).** Until Maestrohub is added, Ignition's MQTT Engine (server `MES Coreflux`, custom namespace `All`, subscription `#`, `jsonPayload: false`) subscribes to CoreFlux directly. Each topic becomes one String tag holding the raw envelope under `[MQTT Engine]40Printing/Dallas/Press Room/Press 1/…`. The `press1` project library unwraps and casts it (VIS-001). The topic root is `40Printing` (DEC-005). Stale `[MQTT Engine]4.0 Printing/…` tags may remain; never read them.

```
UNS Studio sim ─MQTT─► CoreFlux ─► Maestrohub ─► Ignition ─► PostgreSQL
(host, not Docker)     (broker)    (unwrap, cast, (MES logic,  (MES records)
                          │         route)        visuals)
                          └─► Timebase (raw history) ─► Timebase Atlas (model for AI)

Ignition ─publishes─► CoreFlux under 40Printing/Dallas/Press Room/Press 1/MES/…
```

## 2. Components

| Component | Responsibility | Tech / version | Lives in |
|---|---|---|---|
| UNS Studio sim | Raw-layer signals for Press 1 (16 tags). Never changed by this project. | UNS Studio | Walker's MacBook Pro, outside Docker; definition copy at `docs/sim/fourzero_printing_press1.json` |
| CoreFlux | MQTT broker for raw and MES-published topics. Refuses empty client IDs. | `coreflux/coreflux-mqtt-broker:2.2.0` | `docker-compose.yml` service `coreflux` |
| Maestrohub | Unwrap and cast the envelope, route | Maestrohub; version set in the dev-stack deploy task | `docker-compose.yml`, service set in the dev-stack deploy task |
| Ignition | MES logic, test visuals, Perspective, publishing to `…/MES/`. Cirrus Link MQTT Engine and Transmission modules mounted from `resources/modules/`. Project `mes-2026` (repo `ignition/projects/mes-2026/`, bind-mounted): `press1` library, `press1Tick` 2 s gateway timer, SCADA page `/press1` (VIS-001). | `inductiveautomation/ignition:8.3.10`, Standard edition | `docker-compose.yml` service `ignition` |
| PostgreSQL | MES records (`docs/mes_requirements.md` §7) | `postgres:16` (16.15 at INFRA-001) | `docker-compose.yml` service `db` |
| Timebase | Raw tag history for trends and AI queries | Timebase; version set in the dev-stack deploy task | `docker-compose.yml`, service set in the dev-stack deploy task |
| Timebase Atlas | Knowledge graph: Press 1, stations, tags, work orders, downtime classes | Timebase Atlas; version set in the dev-stack deploy task | `docker-compose.yml`, service set in the dev-stack deploy task |

## 3. Data Flow and Contracts

| Contract | Authority |
|---|---|
| Raw UNS namespace, 16 tags, state and fault codes, envelope, consumer rules | `docs/sim_spec_press1.md` §2, §4, §5, §11 |
| MES-published topics under `…/Press 1/MES/` and their payloads | `docs/mes_requirements.md` §8, §4.1 (`ScheduleOverride`), §5 (`PlannedStop`) |
| PostgreSQL tables and product master seed | `docs/mes_requirements.md` §7, entities in §3–§6 |
| Work order seed data | `docs/mes_requirements.md` §3 |

## 4. Module Boundaries and Rules

- The MES never publishes to sim topics. MES output goes only under `…/Press 1/MES/`.
- The envelope is unwrapped and every value cast once, at ingest.
- Meters are consumed as deltas; a drop to 0 is a sim restart.
- No raw samples in PostgreSQL. Timebase holds history.
- Ideal speed and scheduled changeover live only in `product_master`.

## 5. Local Infrastructure

`docker-compose.yml` (project `mes-workshop-2026`, INFRA-001) runs CoreFlux, PostgreSQL and Ignition. Maestrohub, Timebase and Timebase Atlas are added by INFRA-003. UNS Studio runs on the host, not in compose. Credentials live in `.env` (git-ignored); names only in `.env.example`.

Walker's Mac runs other stacks, so host ports are offset and every one binds to `127.0.0.1` only (DEC-003):

| Service | Host | In-network | Notes |
|---|---|---|---|
| `coreflux` MQTT | `127.0.0.1:1886` | `coreflux:1883` | The sim publishes here. Host 1883 is UNS Studio itself; 1884 is the old broker. |
| `coreflux` web UI | http://localhost:8084 | `coreflux:8080` | |
| `coreflux` API / websockets | `127.0.0.1:5004` | `coreflux:5000` | |
| `db` | `127.0.0.1:5434` | `db:5432` | DB `mes`, user `mes` |
| `ignition` | http://localhost:8089 | `ignition:8088` | Admin user `admin` |

**Ignition project in git.** `ignition/projects/mes-2026/` is bind-mounted at `/usr/local/bin/ignition/data/projects/mes-2026`. Designer saves land in the repo. Files edited on disk need the gateway's Projects → "Scan File System" button (8.3 does not watch the folder).

**SCADA trend buffer (VIS-001).** Raw Press 1 samples (2 s, 60 min cap), events and jobs live in `system.util.getGlobals()['press1.v2']`, on the gateway only. There is no historian, database or Timebase behind it. It is lost on a gateway restart, and nothing is sampled while the Mac sleeps.

Inside a container, `localhost` is that container: Ignition reaches the broker at `coreflux:1883`, never `localhost:1886`.

## 6. Startup / Shutdown

`docker compose up -d` / `docker compose stop` from the repo root. Ignition waits for `db` to be healthy. Never `docker compose down -v` without the lead's say-so (it deletes all volume state). Stopping CoreFlux interrupts the sim's publishing but does not restart the sim. UNS Studio is never stopped or restarted as part of stack startup or shutdown.

## 7. Known Limits

- One press only. No other lines, presses or upstream and downstream steps.
- No control of the press.
- Detection, not prediction: faults have no lead-in in the sim (`docs/sim_spec_press1.md` §11 rule 6).
- Classroom time compression: stops every 60 s, changeovers in seconds.
- Spaces in topic levels (`Press Room`, `Press 1`, `Print Section`, `Tunnel Dryer`) work in Ignition MQTT Engine (VIS-001). They are untested in Maestrohub and Timebase. The dot was removed from the root (DEC-005).
- A sim restart resets the counters and the loop.
