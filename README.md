# AI Digital Growth

**Purpose:** Build a commercially viable, evidence-driven digital growth and business-automation company, supported by an operating system that identifies real customer problems, proves them, sells bounded solutions, delivers reliably, and measures client outcomes.

**Strategic principle:** Global intelligence; market-specific validation and execution.

This repository is the working source of truth for architecture, implementation priorities, validation rules, and operating decisions. It begins as a documentation-first baseline; no application code or production workflow is claimed to exist yet.

## Current status (2026-10-27)

- The correct remote is [looloofy69-sketch/AI-Digital-Growth](https://github.com/looloofy69-sketch/AI-Digital-Growth).
- The repository was confirmed empty before this initialization.
- The strategy foundation and blueprint are preserved in the companion repository starter ZIP; the original DOCX/PDF files are not committed in this initial source-control baseline.
- Application code, database migrations, provider integrations, live campaigns, and automated test results remain **not implemented / unverified**.
- Commercial assumptions (market, segment, pricing, funnel, margins) remain hypotheses until validated with buyers and paid pilots.
- Market-specific legal/provider-policy review is required before enabling outbound workflows.

## Start here

1. docs/reviews/2026-10-27-repository-and-blueprint-review.md — corrections, gaps and first priorities.
2. docs/architecture/system-overview.md — system boundaries and core pipeline.
3. docs/architecture/market-adapters.md — global intelligence with independent market validation.
4. docs/architecture/data-model-gap-register.md — data integrity risks and required entities.
5. docs/implementation/implementation-backlog.md — implementation order and acceptance criteria.
6. docs/validation/verification-plan.md — failure-mode testing and autonomy gates.
7. docs/operations/initial-operating-gates.md — minimum controls for claims, outreach and delivery.
8. docs/decisions/ — explicit decisions and unresolved choices.

## Core flow

Discover → normalize/provenance → audit → independently verify → qualify/route → market/channel policy gate → human approval where required → send/deliver → measure outcomes → learn and improve.

The canonical data store must own lifecycle state, approvals, evidence references, cost records, suppression, and idempotency. Workflow orchestrators and vendors are replaceable execution adapters, not sources of truth.

## Scope discipline

Research and benchmark globally; validate demand, pricing, legality, conversion, delivery cost, and retention separately for each market and offer. Serving multiple markets is a strategic option, not a requirement to launch everywhere simultaneously.

## Initial non-goals

- Building a generalized multi-agent platform before paid demand is demonstrated.
- High-volume outbound before policy, provider, deliverability, suppression, and capacity gates are tested.
- Publishing AI content at scale without audience value, editorial verification, and measurement.
- Treating generated findings or generated code as verified merely because an LLM produced them.
