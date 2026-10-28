# Development Philosophy

**Project:** MES Workshop 2026
**Scope:** *How we build* — values, coding standards, logging, security, and the Definition of Done. Operational CI detail lives in `devops_pipeline.md`; process lives in `development_workflow.md`.

---

## Principles

1. **Evidence over confidence.** A claim about the system is backed by a file path, a command and its output, or a query result. "It should work" is not a status.
2. **The files are the record.** If it isn't in the repo, it didn't happen. Chat is not memory.
3. **Spec before code; decide before delegate.** Architecture is decided by the PM and the lead, then written down. The Dev implements; it doesn't improvise structure.
4. **Smallest change that satisfies the spec.** No drive-by refactors, no scope widening.
5. **Docs that lie are worse than no docs.** A contract or user doc moves with the code in the same commit, or the commit isn't done.
6. **Teaching build, not production.** Build for an honest live walkthrough in class, not for scale. Dev speed beats security hardening and QA. Synthetic data only.

## Coding Standards

- No formatter or linter is configured. The build is configuration (`docker-compose.yml`), Ignition gateway and Perspective resources, SQL, and Maestrohub flows.
- Pin every container image to an explicit version tag; never `:latest`.
- Match the surrounding code's naming, structure and comment density.
- No silent failures: an error is logged and surfaced, never swallowed.
- Sim data rules are binding (`docs/sim_spec_press1.md` §11): unwrap the envelope, cast every value on ingest, use deltas on `GoodMeters` and `RejectMeters` and treat a drop to 0 as a sim restart.
- The MES publishes only under `40Printing/Dallas/Press Room/Press 1/MES/`; never to sim topics.

## Logging

- Container logs via `docker compose logs <service>`. Ignition gateway logs in the gateway web UI (Status → Logs). No central log store.
- **Never log secrets, tokens, or credentials.**

## Security

- No secrets in tracked files — `.env` (git-ignored) with a committed `.env.example` of names only.
- Host ports bind to `127.0.0.1` only. Containers talk to each other by service name on the compose network.
- Default credentials are acceptable for this teaching build, but they live in `.env`, never in tracked files.

## Testing

- No automated test suite. Verification is by command output (`docker compose ps`, MQTT round-trips, SQL queries) and by the lead runtime-testing against a live sim loop.
- A bug fix comes with a test that fails before the fix and passes after, where practical.

## Definition of Done

A task is done when **all** of these are true:

- [ ] Every Acceptance Criterion in the spec is met, checked against the code (Rule 7)
- [ ] Gates pass: `docker compose config -q`, plus every check the spec's Acceptance Criteria name
- [ ] Contract / user docs updated in the same commit, or "None." recorded (Rule 11)
- [ ] The Dev Report and the handoff's Dev status are filled in (Rule 6)
- [ ] The lead has runtime-tested against a fresh build (Rule 12)
- [ ] Atomic close-out landed (Rule 14)
