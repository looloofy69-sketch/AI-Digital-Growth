# Implementation backlog

Priorities refer to prerequisites, not a promise of a fixed delivery schedule.

## P0 — Required before enabling real outbound automation

### P0.1 Reconcile capacity and unit economics

Define the full time/cost model: sourcing, qualification, automated checks, human review, sales, delivery, QA, support, admin, rework, tools, payment friction, taxes/fees where applicable, and founder time. Explicitly model the fraction of candidates receiving each review path.

**Acceptance:** low/base/high scenarios fit available capacity; all material costs are represented; assumptions are separated from observed pilot results.

### P0.2 Choose and sell a bounded paid pilot

Compare candidate market/segment/offer combinations using reachable demand, evidence strength, willingness to pay, delivery cost, competitive alternatives and policy overhead. Run buyer discovery and test willingness to pay before building a broad platform.

**Acceptance:** a defined buyer cohort, offer scope, price hypothesis, success metric, sampling plan, stop/continue rule and real buyer evidence are recorded.

### P0.3 Define a valid canonical schema

Resolve the data-model gap register; create versioned migrations and synthetic seed fixtures; constrain identity, enums/ranges, relationships, transitions and append-only history.

**Acceptance:** migrations apply from an empty database; upgrade/rollback tests run in a disposable environment; invalid states and orphan records are rejected.

### P0.4 Implement policy, suppression and send boundary

Use one canonical suppression authority at the final submission boundary. Implement durable approvals, idempotency, bounded retries, provider event reconciliation, rate/budget limits, audit records and a kill switch. Model timeout-after-possible-acceptance as outcome_unknown until reconciled.

**Acceptance:** concurrency, duplicate retry, opt-out race, re-import, provider-timeout and global-stop tests pass without duplicate submission or suppression bypass.

### P0.5 Isolate website-audit fetching

Block private, loopback, link-local and reserved address ranges; re-check after DNS resolution and every redirect; constrain protocols/ports, response size, time, redirects and content types. Keep credentials/secrets unavailable to untrusted-content processors.

**Acceptance:** adversarial URL suite covers IPv4/IPv6, DNS variation, redirects, oversized responses and private destinations; prohibited fetches are blocked.

### P0.6 Define claim and model evaluation

Version audit rules, prompts, models and policies. Create representative labeled fixtures, blinded review where appropriate, false-positive/negative measures, calibration and rollback thresholds.

**Acceptance:** reproducible evaluation report and rollback path exist before autonomy promotion.

## P1 — Required for dependable paid delivery

- Project/SOW/milestone/acceptance/change-request model.
- Reusable delivery kits with CI, preview, smoke tests, independent QA and rollback.
- Baseline/outcome measurement contract.
- Client onboarding, asset ownership, handover, backup and support boundaries.
- Observability for job errors, vendor failures, spend, latency, rework and incidents.

## P2 — Defer until demand or bottleneck evidence

- Public Free Site Check at scale.
- Multi-market outbound scale-up.
- Broad automated SEO publishing beyond draft/review.
- Automated service-opportunity mining and benchmark reports.
- Partner automation and additional verticals.

Every implementation issue must specify objective, evidence, non-goals, dependencies, design, acceptance tests, security/compliance impact, cost/capacity impact, rollback, owner, status and known limitations.
