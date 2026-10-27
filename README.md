# AI Digital Growth

Build a commercially viable, evidence-driven digital growth and business-automation company. The system should identify real customer problems, prove them, sell bounded solutions, deliver reliably and measure client outcomes.

**Architecture direction:** global intelligence core with independently validated market adapters. Research and benchmark globally; validate demand, pricing, legal rules, conversion, delivery cost and retention separately in each market.

## Start here

- System overview: docs/architecture/system-overview.md
- Global/market adapters: docs/architecture/market-adapters.md
- Data-model gaps: docs/architecture/data-model-gap-register.md
- Implementation backlog: docs/implementation/implementation-backlog.md
- First executable slice and verification status: docs/implementation/first-slice.md
- Test/acceptance plan: docs/validation/verification-plan.md
- Grok/Helm workspace assessment: docs/reviews/2026-10-27-grok-workspace-assessment.md
- Decision and assumption templates: docs/templates/

## First executable slice

- Capacity/unit economics scenario calculator.
- Fail-closed outbound draft eligibility gate; no live sending.
- PostgreSQL schema for provenance, audit evidence, verification, source/purpose policy, suppression, content-hash approval, idempotency, costs and outcome snapshots.
- Unit tests, PostgreSQL integration tests and GitHub Actions CI.

## Run locally

- Install unit-test dependencies: python -m pip install -e '.[test]'
- Run examples: adg-economics examples/illustrative-baseline.json
- Run tests: pytest -q
- For DB tests, install python -m pip install -e '.[test,postgres]', set DATABASE_URL to a disposable PostgreSQL 16 database, run python scripts/apply_migrations.py, then pytest -q.

## Limits

No lead-source connector, public API/UI, website fetcher, email provider, live sending, authentication or production deployment has been implemented. Local DB integration is not verified until the GitHub Actions PostgreSQL job passes. Example funnel/pricing/time values are assumptions, not market observations or a forecast. Do not enable outbound before source terms, market/channel rules, legal clearance, capacity and evaluation requirements pass. Never copy platform-specific preview credentials from Helm into this repository.

**Rule:** untested means UNVERIFIED, not PASS.
