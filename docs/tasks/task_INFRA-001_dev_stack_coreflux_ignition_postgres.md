# INFRA-001 — Dev stack: CoreFlux, Ignition and PostgreSQL in docker-compose

**Status:** ✅ Complete — 2026-10-20, runtime-checked by Walker (Dev, 2026-10-20)
**Priority:** P0 · **Effort:** S (one Dev run)
**Depends on:** —
**Bug:** —

---

## Background

Walker's Day 1 plan (2026-10-20): stand up Ignition and CoreFlux first. Walker then points the UNS Studio sim at the new CoreFlux (INFRA-004, Walker-run), and the day closes with Press 1 process visuals in Perspective (VIS-001).

`docker-compose.yml` is still the `mes-dev-template` skeleton: placeholder `broker` and `app` services, a `db` service with no version, and a real `ignition` service. After this task, `docker compose up -d` brings up three healthy services — CoreFlux (MQTT broker), Ignition 8.3.10 and PostgreSQL 16 — on host ports that do not collide with anything else on Walker's Mac. PostgreSQL is included now because the skeleton already has it and it costs nothing; connecting Ignition to it is INFRA-002.

**Host port survey (PM, 2026-10-20, `lsof -iTCP -sTCP:LISTEN` and `docker ps`).** Walker's Mac already runs other stacks. Taken: `1883` (**UNS Studio itself listens here**), `1884`/`8083`/`5003` (the existing CoreFlux container `coreflux-mqtt`, project `notus-dev` — the one the sim publishes to today), `1885` (HighByte), `5432` (native Postgres and `postgres-test`), `5433` (`ignmes-postgres`), `8088`/`8043` (`ignmes-ignition`), `8000`, `8080`–`8083`, `8090`. Free and chosen below: `1886`, `8084`, `5004`, `5434`, `8089`.

## What Already Exists (Do Not Rewrite)

- `docker-compose.yml` service `ignition` (lines 47–72): image `inductiveautomation/ignition:8.3.10`, env, the two Cirrus Link `.modl` mounts, port `${IGNITION_HTTP_PORT:-8089}:8088`. **Keep it exactly as is**, except the one `depends_on` addition below.
- `resources/modules/MQTT-Engine-signed.modl`, `MQTT-Transmission-signed.modl` — present; mounted by the `ignition` service.
- `.gitignore` already ignores `.env`.
- **Other stacks on this machine — do not touch them:** `coreflux-mqtt`, `ignmes-*`, `postgres-test`, `highbyte`, `timebase-*`, `portainer`, and the rest of `docker ps`. Never stop, restart or remove a container that is not in this compose project.
- **UNS Studio and the sim `fourzero_printing_press1`** — on the host, publishing to `coreflux-mqtt` on host port 1884. Not touched by this task.

Cached images (no pull needed): `coreflux/coreflux-mqtt-broker:2.2.0`, `inductiveautomation/ignition:8.3.10`, `postgres:16`, `eclipse-mosquitto:2`.

## What to Build

### 1. `docker-compose.yml`

- Header comment: replace `{{PROJECT_NAME}}` with `MES Workshop 2026`; drop the "Replace the placeholder services…" sentence. Keep the pinning, secrets and `down -v` warnings.
- `name: mes-workshop-2026`
- **Delete** the `broker` and `app` services.
- **Add** service `coreflux`:
  ```yaml
  coreflux:
    image: coreflux/coreflux-mqtt-broker:2.2.0   # same version as the broker the sim uses today
    restart: unless-stopped
    environment:
      COREFLUX_SECRET_KEY: ${COREFLUX_SECRET_KEY:?set COREFLUX_SECRET_KEY in .env}
    ports:
      - "127.0.0.1:${COREFLUX_MQTT_PORT:-1886}:1883"   # MQTT. 1883 is UNS Studio, 1884 the old broker
      - "127.0.0.1:${COREFLUX_WEB_PORT:-8084}:8080"    # web UI
      - "127.0.0.1:${COREFLUX_API_PORT:-5004}:5000"    # websockets / backend API
    volumes:
      - coreflux-data:/etc/coreflux
    # Healthcheck comes from the image (pgrep CorefluxMQTTBroker).
  ```
- `db` service: image `postgres:16`; host port `"127.0.0.1:${POSTGRES_PORT:-5434}:5432"` with a trailing comment `# 5432/5433 are taken by other stacks`. Everything else in `db` unchanged.
- `ignition` service: add only
  ```yaml
  depends_on:
    coreflux:
      condition: service_started
    db:
      condition: service_healthy
  ```
- `volumes:` → `coreflux-data`, `db-data`, `ignition-data` (rename `broker-data` to `coreflux-data`; nothing uses it yet).
- Do **not** add `container_name` (it would collide with the other stacks' names). Compose's default network `mes-workshop-2026_default` is the network; services reach each other by service name (`coreflux:1883`, `db:5432`).

### 2. `.env.example` (names only, never values)

Add `COREFLUX_SECRET_KEY=`, `COREFLUX_MQTT_PORT=1886`, `COREFLUX_WEB_PORT=8084`, `COREFLUX_API_PORT=5004`, `POSTGRES_PORT=5434`. Keep the existing lines.

### 3. `.env` (git-ignored, local only)

Create it if missing. Values: `POSTGRES_DB=mes`, `POSTGRES_USER=mes`, `POSTGRES_PASSWORD=` a generated value, `IGNITION_ADMIN_USERNAME=admin`, `IGNITION_ADMIN_PASSWORD=` a generated value, `COREFLUX_SECRET_KEY=` output of `openssl rand -base64 32`, ports as in `.env.example`. **Never paste any of these values into the spec, the handoff or any tracked file.** Report only that `.env` holds them.

### 4. Bring it up

`docker compose up -d` from the repo root. Wait for Ignition's first start (can take 1–3 minutes).

### 5. Not in scope

- No Ignition configuration: no MQTT Engine server settings, no database connection, no tags, no projects. (INFRA-002, UNS-002.) MQTT Engine may log connection errors to its default `localhost:1883` server — expected; record it, do not fix it.
- No CoreFlux configuration beyond what the image does by default (no users, ACLs, bridges or LoT actions). If anonymous MQTT is refused, see AC 5.
- No Maestrohub, Timebase or Timebase Atlas (INFRA-003).
- No change to UNS Studio or the sim (INFRA-004 is Walker's).

## Acceptance Criteria

1. [ ] `docker compose config -q` exits 0.
2. [ ] `grep -n '{{' docker-compose.yml` returns nothing.
3. [ ] `docker compose ps` shows `coreflux`, `db` and `ignition` up; `db` and `ignition` `healthy`, and `coreflux` `healthy` once its image healthcheck has run.
4. [ ] `curl -s http://localhost:8089/StatusPing` returns `{"state":"RUNNING"}` (paste the actual output). If the gateway sits at a commissioning or EULA screen that needs a browser, record exactly what it shows in the Dev Report — it becomes a Walker GUI step.
5. [ ] **Host-side MQTT round trip on 127.0.0.1:1886** (the path UNS Studio will use): a host Python script with paho-mqtt 1.6.1 (already installed) subscribes to `INFRA-001/Test`, publishes `{"value": 1}` to it, and receives it within 5 s. Try anonymous first. If the broker refuses anonymous connections, try CoreFlux's documented default credentials; if one works, record in the Dev Report **which** account worked (username only) and that UNS Studio will need it — do not put a password in a tracked file. Put the script in `/tmp` or your scratchpad, not the repo.
6. [ ] **In-network round trip** on `coreflux:1883`: `docker run --rm --network mes-workshop-2026_default eclipse-mosquitto:2 sh -c 'mosquitto_sub -h coreflux -t INFRA-001/Test -C 1 -W 10 & sleep 1; mosquitto_pub -h coreflux -t INFRA-001/Test -m ok; wait'` prints `ok` (add `-u/-P` only if AC 5 needed credentials).
7. [ ] Ignition can reach the broker and the database: `docker compose exec ignition bash -c 'echo > /dev/tcp/coreflux/1883 && echo mqtt-ok; echo > /dev/tcp/db/5432 && echo db-ok'` prints both.
8. [ ] `docker compose exec db psql -U mes -d mes -c 'select version();'` returns PostgreSQL 16.x.
9. [ ] The CoreFlux web UI answers: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8084/` returns 200 or a 3xx.
10. [ ] No other stack was touched: `docker ps --format '{{.Names}} {{.Status}}'` for `coreflux-mqtt`, `ignmes-ignition`, `ignmes-postgres`, `postgres-test` shows the same uptime as before your run (they were "Up 6 hours" at ~13:00 CDT).
11. [ ] `git status` shows only `docker-compose.yml`, `.env.example`, this spec and `docs/agent_handoff.md` changed. `.env` is not listed.

## Files to Modify

| File | Change |
|---|---|
| `docker-compose.yml` | Replace skeleton with `coreflux`, `db`, `ignition` as above |
| `.env.example` | Add the five new variable names |
| `.env` | Create/fill locally (git-ignored, never committed) |
| `docs/tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md` | Status line and Dev Report only |
| `docs/agent_handoff.md` | `Dev status` block only |

Contract docs (Rule 11): `docs/architecture.md` §2 and §5 (versions, ports) are PM-owned and are updated by the PM at close-out. The Dev does not edit them.

## Dev Instructions

Read this spec in full before touching anything. Replace the template skeleton in `docker-compose.yml` with three pinned services — `coreflux` (CoreFlux 2.2.0, host MQTT port 1886), `db` (PostgreSQL 16, host port 5434) and the existing `ignition` service (8.3.10, host port 8089, unchanged apart from `depends_on`) — add the new names to `.env.example`, fill `.env` locally, bring the stack up, and prove each Acceptance Criterion with pasted command output.

Hard constraints:
- **Never stop, start, restart or reconfigure the UNS Studio sim or UNS Studio itself.** A restart resets the sim's counters. Nothing in this task touches them.
- **Never stop, restart, remove or reconfigure any container outside the `mes-workshop-2026` compose project** — in particular `coreflux-mqtt`, which the live sim publishes to. Never run `docker compose down -v`, `docker system prune` or `docker volume prune`.
- Never publish to any `4.0 Printing/...` topic, on either broker. Test traffic goes only to `INFRA-001/Test` on the new broker.
- No secrets in tracked files, the spec or the handoff. Generated passwords and the CoreFlux key live only in `.env`.
- Pin images exactly as specified; no `:latest`. No `container_name`.
- No Ignition or CoreFlux configuration beyond what is specified (section 5).
- Stage path-scoped (`docker-compose.yml`, `.env.example`, this spec, `docs/agent_handoff.md`); never `git add -A` or `git add .`. Commit locally with `INFRA-001: Stand up CoreFlux, Ignition and PostgreSQL`. Do not push.

---

## Dev Report

*(Written by the Dev. The PM reads this, then verifies against the actual files.)*

**Status:** ✅ Done — ready for PM verification
**Date:** 2026-10-20

**What was built:**
- `docker-compose.yml` — header de-templated (`MES Workshop 2026`, "Replace the placeholder…" sentence dropped; pinning, secrets and `down -v` warnings kept). `name: mes-workshop-2026`. `broker` and `app` deleted. `coreflux` added exactly as specced (CoreFlux 2.2.0; 127.0.0.1 host ports 1886 MQTT / 8084 web / 5004 API; `coreflux-data:/etc/coreflux`; secret key required from `.env`). `db` pinned to `postgres:16`, host port `127.0.0.1:${POSTGRES_PORT:-5434}:5432`. `ignition` unchanged except the `depends_on` block (coreflux `service_started`, db `service_healthy`). Volumes: `coreflux-data`, `db-data`, `ignition-data`. No `container_name`.
- `.env.example` — appended `COREFLUX_SECRET_KEY=`, `COREFLUX_MQTT_PORT=1886`, `COREFLUX_WEB_PORT=8084`, `COREFLUX_API_PORT=5004`, `POSTGRES_PORT=5434`. Existing lines kept.
- `.env` — created locally (mode 600, git-ignored). Holds `POSTGRES_DB=mes`, `POSTGRES_USER=mes`, a generated `POSTGRES_PASSWORD`, `IGNITION_ADMIN_USERNAME=admin`, a generated `IGNITION_ADMIN_PASSWORD`, `COREFLUX_SECRET_KEY` from `openssl rand -base64 32`, and the five ports. Values are only in `.env`.
- Stack brought up with `docker compose up -d`; all three services healthy, zero restarts.

**Files changed:**
| Path | Created / Modified / Deleted |
|---|---|
| `docker-compose.yml` | Modified |
| `.env.example` | Modified |
| `.env` | Created (git-ignored, not committed) |
| `docs/tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md` | Modified (Status line, Dev Report) |
| `docs/agent_handoff.md` | Modified (Dev status block) |

**Gate results** (commands and actual output, pasted):
```
# AC 1
$ docker compose config -q; echo "config exit=$?"
config exit=0

# AC 2
$ grep -n '{{' docker-compose.yml; echo "grep exit=$?"
grep exit=1            # no matches

# AC 3
$ docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
SERVICE    IMAGE                                 STATUS                    PORTS
coreflux   coreflux/coreflux-mqtt-broker:2.2.0   Up 36 seconds (healthy)   127.0.0.1:1886->1883/tcp, 127.0.0.1:5004->5000/tcp, 127.0.0.1:8084->8080/tcp
db         postgres:16                           Up 36 seconds (healthy)   127.0.0.1:5434->5432/tcp
ignition   inductiveautomation/ignition:8.3.10   Up 25 seconds (healthy)   127.0.0.1:8089->8088/tcp
$ docker inspect … RestartCount
coreflux restarts=0 started=2026-10-20T18:09:09.798293762Z
db restarts=0 started=2026-10-20T18:09:09.799200221Z
ignition restarts=0 started=2026-10-20T18:09:20.446795212Z

# AC 4
$ curl -s http://localhost:8089/StatusPing
{"state":"RUNNING"}
(No commissioning/EULA screen: EULA accepted by env, quickstart disabled.)

# AC 5 — host paho-mqtt 1.6.1 → 127.0.0.1:1886, ANONYMOUS, client_id "infra001-roundtrip"
$ python3 -I <scratchpad>/mqtt_rt.py
received INFRA-001/Test {"value": 1}
paho  connect rc = 0 | round trip OK in 0.92s

# AC 6 — spec command as written FAILS (see Deviations):
$ docker run --rm --network mes-workshop-2026_default eclipse-mosquitto:2 sh -c 'mosquitto_sub -h coreflux -t INFRA-001/Test -C 1 -W 10 & sleep 1; mosquitto_pub -h coreflux -t INFRA-001/Test -m ok; wait'
Connection error: Connection Refused: identifier rejected
Connection error: Connection Refused: identifier rejected
Error: The connection was refused
# diagnosis (mosquitto_pub -d): empty client ID → CONNACK 2 (v3.1.1) / CONNACK 133 "Client Identifier not valid" (v5); with -i infra001-pub → CONNACK 0
# with explicit client IDs, anonymous:
$ docker run --rm --network mes-workshop-2026_default eclipse-mosquitto:2 sh -c 'mosquitto_sub -h coreflux -i infra001-sub -t INFRA-001/Test -C 1 -W 10 & sleep 1; mosquitto_pub -h coreflux -i infra001-pub -t INFRA-001/Test -m ok; wait'
ok

# AC 7
$ docker compose exec ignition bash -c 'echo > /dev/tcp/coreflux/1883 && echo mqtt-ok; echo > /dev/tcp/db/5432 && echo db-ok'
mqtt-ok
db-ok

# AC 8
$ docker compose exec db psql -U mes -d mes -c 'select version();'
 PostgreSQL 16.15 (Debian 16.15-1.pgdg13+2) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
(1 row)

# AC 9
$ curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8084/
200

# AC 10 — other stacks untouched (StartedAt unchanged, 0 restarts; status now reads "Up 7 hours" at ~13:10 CDT)
$ docker inspect -f '{{.Name}} started={{.State.StartedAt}} restarts={{.RestartCount}}' coreflux-mqtt ignmes-ignition ignmes-postgres postgres-test
/coreflux-mqtt started=2026-10-20T11:39:11.210122Z restarts=0
/ignmes-ignition started=2026-10-20T11:39:11.210155375Z restarts=0
/ignmes-postgres started=2026-10-20T11:39:11.193911542Z restarts=0
/postgres-test started=2026-10-20T11:39:11.191729542Z restarts=0

# AC 11 (before staging; handoff edited afterwards)
$ git status --short
 M .env.example
 M docker-compose.yml
 M docs/tasks/task_INFRA-001_dev_stack_coreflux_ignition_postgres.md
```

Expected noise, recorded not fixed (§5): MQTT Engine cycles every ~3 s against its unconfigured default server —
`W [o.e.t.m.TahuClient] ME-4eb672d2-accb-4851: … MQTT Server Name = Chariot SCADA :: MQTT Server URL = tcp://localhost:1883 … Caused by: java.net.ConnectException: Connection refused`.

**Deviations from spec:** AC 6's command was run with explicit client IDs (`-i infra001-sub`, `-i infra001-pub`). CoreFlux 2.2.0 rejects an empty MQTT client ID, and mosquitto 2's CLI sends an empty one by default. No credentials were needed anywhere — anonymous MQTT is accepted on both 1886 (host) and `coreflux:1883` (in-network). Nothing else differs.

**Open questions for the PM:**
- **Empty client IDs are refused by the new broker.** Any client that connects with an empty/server-assigned client ID will get "identifier rejected". paho (host), Ignition MQTT Engine (`ME-…`) and most UNS tools set one, but INFRA-004 (UNS Studio repoint) and INFRA-003 (Maestrohub/Timebase) should confirm theirs is non-empty. Worth a line in `architecture.md` / traps?
- MQTT Engine will keep logging connect failures to `tcp://localhost:1883` until UNS-002/INFRA-002 points it at `coreflux:1883` (note: inside the container, `localhost:1883` is the Ignition container itself, not UNS Studio).
- Ignition admin username is `admin`; the password is only in `.env` — Walker reads it there for the http://localhost:8089 check.

---

## PM Verification

*(Written by the PM after reading the changed files — Rule 7.)*

**Result:** ✅ Pass — 2026-10-20. Walker confirmed the sim publishes to the new broker without a restart; PM confirmed all 16 sim topics arriving on `coreflux:1883`.
**Findings:**
- Read `git show 87af5b0` and the working tree. Changed: `docker-compose.yml`, `.env.example`, this spec, `docs/agent_handoff.md` (Dev status; the commit-hash line is an uncommitted follow-up edit). No other files. No scope creep.
- `docker-compose.yml` matches §1 line for line: `coreflux` 2.2.0 with `${COREFLUX_SECRET_KEY:?…}` and 127.0.0.1 ports 1886/8084/5004; `db` `postgres:16` on 5434; `ignition` unchanged apart from `depends_on`; `broker`/`app` gone; volumes renamed; no `container_name`; no `{{`.
- Re-ran independently: `docker compose config -q` → ok; `docker compose ps` → all three `healthy`; `StatusPing` → `{"state":"RUNNING"}`; CoreFlux web → 200; in-network round trip with client IDs → `pm-ok`; `coreflux-mqtt` StartedAt unchanged (`11:39:11Z`, 0 restarts).
- `.env` is git-ignored and untracked; the three generated secrets do not appear in any tracked file (`git grep -F`).
- AC 6 deviation (explicit `-i` client IDs) accepted: CoreFlux 2.2.0 refuses an empty client ID. That is broker behaviour, not a defect in the task. Added to the handoff traps for INFRA-004 and INFRA-003.
- MQTT Engine connect errors to its default `localhost:1883` are expected per §5; UNS-002 points it at `coreflux:1883`.
