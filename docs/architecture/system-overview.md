# System overview

## Outcome

Build a repeatable commercial workflow that turns verified digital problems into paid work and measurable client outcomes. The software serves the business; platform complexity is not itself a success metric.

## End-to-end pipeline

1. **Discover:** collect candidate organizations from permitted sources, preserving source, retrieval time, terms, and uncertainty.
2. **Normalize:** resolve organization/domain/contact identity without silently merging ambiguous records.
3. **Audit:** run deterministic diagnostics with bounded network access, timeouts, size limits, and reproducible parameters.
4. **Store evidence:** retain raw outputs, hashes, timestamps, tool/rule versions, and links from each finding to its evidence.
5. **Verify independently:** use a separate run/tool or blind reviewer where practical. Reject, downgrade, or qualify non-reproducible claims.
6. **Qualify and route:** apply hard exclusions first; then use transparent scoring to route a verified problem to an offer.
7. **Apply policy:** evaluate market, recipient, source, purpose, and channel rules before any external communication.
8. **Approve and act:** persist approval and idempotency state before an outbound or consequential action; re-check suppression at the final boundary.
9. **Deliver:** manage scope, milestones, acceptance tests, costs, QA, handover, and rollback.
10. **Measure and learn:** retain baseline, metric definition, source, period, confounders, and client result; update assumptions only from evidence.

## System boundaries

- **Canonical application store:** owns identities, lifecycle, approvals, evidence references, policies, suppression, job state, and costs.
- **Workers:** execute bounded tasks and may be retried; they must be idempotent or explicitly model ambiguous outcomes.
- **LLMs:** classify, summarize, draft, and assist reasoning. They do not establish a fact solely by asserting it.
- **Deterministic tools:** produce measurements that still require validation for applicability and freshness.
- **Vendors/orchestrators:** replaceable adapters, never the only place critical state exists.
- **Human control:** required for external claims, commercial commitments, production release, and other gated decisions until evidence supports a narrower authorization.

## First production slice

Build only the smallest end-to-end slice needed to sell and deliver one paid offer: lead/source record, evidence-backed audit, independent verification, a human-reviewed proposal, project scope and acceptance, cost capture, and a client outcome baseline. Do not begin with a generalized multi-agent platform.

## Required cross-cutting properties

Security isolation; provenance; immutable audit history; explicit state transitions; idempotency; bounded retries; cost and rate limits; observability; export/deletion lifecycle; versioned prompts/rules/models; reproducible tests; rollback; and per-market metrics.
