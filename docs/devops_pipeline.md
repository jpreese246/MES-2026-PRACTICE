# DevOps Pipeline

**Project:** MES Workshop 2026
**Scope:** An operational runbook — what CI runs, what each check guards, and the criteria for changing them. Values and principles live in `development_philosophy.md`; the human/agent loop lives in `development_workflow.md`.

---

## Local gates (run by the Dev before reporting done)

| Gate | Command | Guards |
|---|---|---|
| Compose config | `docker compose config -q` | `docker-compose.yml` is valid and every required `.env` variable is set |
| Stack health | `docker compose ps` | Every service is `running`, and `healthy` where it has a healthcheck |
| Spec checks | as named in the spec's Acceptance Criteria | The task's own behaviour |

No build, lint or test suite: this is a teaching build (`development_philosophy.md` principle 6).

## CI

**Status:** Not set up. Not planned for the workshop.

## Ratchets

None.

## Environments and deploy

One environment: the Docker stack on Walker's MacBook Pro, beside UNS Studio (on the host) and several unrelated stacks, which is why host ports are offset (`docs/architecture.md` §5). No test or production environment. Only the Dev runs `docker compose up` / `restart`; `docker compose down -v` needs the lead's say-so because it deletes all volume state.

## Automation boundaries

Any agent that drafts changes (docs drift, dependency bumps) **opens a pull request for human review and never commits to `main`.** Unverified auto-written docs are worse than missing docs.
