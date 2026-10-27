# Decision log

## Accepted directions

| ID | Decision | Status | Evidence/assumption | Review trigger |
|---|---|---|---|---|
| D-001 | Global intelligence core with market-specific adapters | Accepted direction | Enables method reuse without conflating market behavior or legal rules | Adapter cost or cross-market comparability changes |
| D-002 | Validate one bounded paid workflow before broad platform build | Accepted sequencing principle | Limits investment before willingness to pay and delivery cost are known | Paid pilot evidence or repeated buyer contradiction |
| D-003 | Evidence-linked claims and independent verification | Required design principle | Avoids unsupported external claims | Evaluation shows a safer/reliable alternative |
| D-004 | Canonical state store owns suppression, approvals and idempotency | Required design principle | Vendor/workflow retries must not bypass critical control | Architecture/security review |

## Unresolved

- First market(s), segment(s) and first paid offer.
- Candidate sources and acquisition channels per market.
- Pricing and cost floors based on actual delivery effort.
- CRM and workflow orchestrator selection.
- Database/runtime/deployment technology.
- Autonomy thresholds supported by evaluation data.
- Market-specific legal review and contracting requirements.

## Change protocol

When a decision changes, record old and new state, rationale, supporting evidence, confidence, cost/risk impact, affected documents/interfaces/tests, owner and review trigger. Do not silently overwrite earlier assumptions.
