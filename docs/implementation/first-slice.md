# First executable slice — implementation log

**Date:** 2026-10-27  
**Goal:** Start the narrow implementation without premature live outreach or platform sprawl.

## Included

- Dependency-free Python package for monthly funnel, capacity and unit-economics scenarios.
- Fail-closed outbound-draft gate with exact market/recipient/channel/purpose/source matching, traceable legal/compliance clearance, evidence verification/freshness, suppression, and human approval.
- Reply-action distinction: explicit opt-out globally suppresses; objection pauses for review; ambiguous replies pause automation; a negative reply ends the current campaign.
- Bounded static website audit at src/ai_digital_growth/audit.py: one public HTTPS page per invocation, checked public-IP pinning, TLS hostname verification, redirect revalidation and body evidence hashes.
- PostgreSQL migration modeling provenance, audits, evidence and finding review, opportunities, market policy, scoped suppression, approvals tied to the exact content hash, idempotency and dispatch state, append-only event history, costs and outcomes.
- Transactional migration runner, example scenarios, unit tests, database integration tests and PostgreSQL 16 CI job.

## Local verification

- **PASS:** `PYTHONPATH=src pytest -q` — 39 passed; 1 PostgreSQL integration module skipped locally because psycopg is unavailable.
- **PASS:** compileall succeeded.
- **PASS:** audit tests cover URL restrictions, private/mixed DNS rejection, checked-IP connection pinning, TLS hostname, redirect revalidation/loops, response-size/compression limits, evidence hashes and CLI behavior. These tests use fake network primitives and contact no external websites.
- **PASS (previous commit):** GitHub Actions run 40438604100 on commit a0b8923413886d9a5926355ede9ab7c4c206bac1 provisioned PostgreSQL 16, applied the initial migration and reported 40 tests passed. A fresh CI run is required for the audit-enabled commit.
- **UNVERIFIED locally:** PostgreSQL integration tests are skipped because psycopg is absent in the local sandbox.
- **NOT RUN:** external sending, live website audit against a real website, legal review, production deployment, authentication, penetration tests or paid-market validation.

## Illustrative calculations

The blueprint funnel rates imply 3.024 expected wins per 1,000 contacts. At 1,650 contacts, expected wins are 4.9896. One 15-minute human review per contact costs 412.5 hours before research, sales, delivery and support. The example models 651.68 hours against 160 usable hours and negative contribution of EUR 11,552.96 under illustrative pricing/cost inputs. This identifies an overloaded scenario; it is not observed profitability. The 10% human-review scenario is sensitivity analysis, not evidence that remaining checks can safely be automated.

## Explicit limitations

1. Economics is a scenario calculator, not an observed forecast; taxes, payment timing, refunds, bad debt and price/volume interactions are not fully modeled.
2. The outbound gate and database are controls only. No provider adapter or send command exists.
3. Database checks cannot make an external provider call atomic with suppression. A production sender still needs a reviewed transactional outbox, concurrency handling and reconciliation protocol.
4. The migration is intended for a fresh test database; production rollback, grants, auth and deployment are incomplete.
5. The application must define a versioned keyed-hashing scheme and encryption/key management before storing real contact data.
6. The website audit is static and single-page. It does not inspect rendered JavaScript, performance field data, screenshots or a full site crawl; findings need independent human verification.

## Next gates

1. Get a green PostgreSQL CI run for the audit-enabled commit and repair any failures.
2. Review the fetcher against a wider SSRF/security matrix before public multi-tenant deployment.
3. Add server-side service persistence without live sending.
4. Replace illustrative economics inputs with measured prospecting and delivery costs from a paid pilot.
5. Add a provider adapter only after exact market/channel/source rules, approvals, suppression, idempotency and reconciliation are tested.
