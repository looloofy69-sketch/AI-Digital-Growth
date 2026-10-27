# First executable slice — implementation log

**Date:** 2026-10-27  
**Goal:** Start the narrow implementation without premature live outreach or platform sprawl.

## Included

- Dependency-free Python package for monthly funnel, capacity and unit-economics scenarios.
- Fail-closed outbound-draft gate with exact market/recipient/channel/purpose/source matching, traceable legal/compliance clearance, evidence verification/freshness, suppression, and human approval.
- Reply-action distinction: explicit opt-out globally suppresses; objection pauses for review; ambiguous replies pause automation; a negative reply ends the current campaign.
- PostgreSQL migration modeling provenance, audits, evidence and finding review, opportunities, market policy, scoped suppression, approvals tied to the exact content hash, idempotency and dispatch state, append-only event history, costs and outcomes.
- Transactional migration runner, example scenarios, unit tests, database integration tests and PostgreSQL 16 CI job.

## Local verification (before repository sync)

- PASS: 30 Python unit/static/CLI tests passed.
- PASS: compileall succeeded.
- PASS: editable package installed in the available environment and CLI emitted valid JSON.
- PASS: GitHub Actions on commit 38c6433562f98d41b15a75ef047cc955e4931d92 ran PostgreSQL 16, applied migration 0001, and reported 35 tests passed.
- UNVERIFIED locally: PostgreSQL integration tests were skipped because PostgreSQL and psycopg were unavailable in the sandbox.
- NOT RUN: live scraping, email provider integration, production deployment, authentication, legal review, penetration testing or paid-market validation.

## Illustrative calculations

The blueprint funnel rates imply 3.024 expected wins per 1,000 contacts. At 1,650 contacts, expected wins are 4.9896. One 15-minute human review per contact costs 412.5 hours before research, sales, delivery and support. The example models 651.68 hours against 160 usable hours, and a negative contribution of EUR 11,552.96 using illustrative revenue/labor/cost values. This exposes an overloaded scenario; it is not a real-world profitability claim.

The 10% human review scenario is a sensitivity test, not evidence that remaining checks can safely be automated.

## Explicit limitations

1. The economics model is not an observed forecast; taxes, payment timing, refunds, bad debt and price/volume interactions are not fully modeled.
2. The outbound gate has no provider adapter or send command. Dry-run eligibility is not external-send authorization.
3. DB triggers recheck important invariants, but a production sender still needs transactional outbox design and per-subject synchronization at the final submission boundary. An external provider call is not atomic with a database transaction.
4. The migration is for a fresh test database. Production migration/rollback review, database grants, auth and deployment are incomplete.
5. Contact address hashes must use a documented keyed-hashing scheme; ciphertext and key management belong in the application/secret manager.

## Next gates

1. Get a green PostgreSQL CI run and repair every migration/test failure.
2. Implement a bounded website-audit worker with SSRF controls, deterministic measurements and reproducible evidence.
3. Add service persistence without live sending.
4. Replace illustrative economics inputs with measured prospecting and delivery time/cost data from a paid pilot.
5. Add outbound only after the legal/provider/source/capacity/evaluation gates have passed.
