# ADR-0001: Global intelligence core with market adapters

- **Status:** Accepted as architecture direction; commercial markets remain unvalidated.
- **Date:** 2026-10-27

## Context

The business can use international sources and benchmarks for research while operating from Algeria and potentially selling across multiple geographies. A single country-first architecture would unnecessarily constrain research; a single global policy would incorrectly assume that pricing, buyer behavior and legal rules transfer between markets.

## Decision

Share core audit methods, evidence formats, evaluation, CRM lifecycle, delivery quality and cost definitions. Isolate market-specific source permissions, language, pricing, contracts/tax assumptions, acquisition eligibility, channel rules, payment methods and observed economics in versioned adapters.

## Consequences

- Research and tooling can be reused across markets.
- Commercial metrics and P&L remain segmented by market, offer and acquisition channel.
- Policy is a hard gate before outbound action; a market cannot inherit permission from another market.
- Localization and adapter maintenance add implementation cost.
- Global benchmarks help form hypotheses but do not substitute for paid-market validation.

## Revisit when

Comparable evidence shows that a field should be global or market-specific; a policy change occurs; or adapter maintenance outweighs its value.
