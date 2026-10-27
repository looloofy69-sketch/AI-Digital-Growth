# Repository and blueprint review

**Review date:** 2026-10-27  
**Target repository:** https://github.com/looloofy69-sketch/AI-Digital-Growth  
**Sources:** v1.1 strategy DOCX/PDF and v2.1 blueprint DOCX in the companion starter package; GitHub repository metadata and API responses.

## Repository findings

- The target repository was empty at review time: no files, no commits and no branches.
- The connected GitHub integration reports read and push permissions for this target.
- This is a strategy/architecture review only. No pre-existing app code, database migration, deployed workflow, email provider, live campaign, client outcome or test suite was available to inspect.
- The earlier URL Loofy147/AI-Digital-Growth was a different repository and must not be treated as the source of truth for this project.

## What the blueprint gets right

- Evidence-to-revenue framing: prove a digital problem, scope a fix, deliver, and measure outcomes.
- Separation between deterministic measurement, LLM assistance and human approval.
- Emphasis on source provenance, evidence freshness, claim verification, cost floors, delivery QA and safety gates.
- Replaceable vendors and a canonical system of record.
- Recognition that global research and multi-market selling need market-specific validation.

## P0 issues before external automation

1. **Capacity model:** the blueprint uses an example of about 1 client per 330 contacts and about 1,650 contacts for five monthly wins. If every one of those contacts requires a 0.25-hour human-reviewed mini-check, that is 412.5 review hours/month before sales, delivery, support and administration. This is conditional arithmetic, not proof that every contact receives manual review. The fraction of contacts on each review path and its measured time must be specified.
2. **Attribution:** the immutable first-touch plus append-only touch-history policy needs a canonical touch-event model.
3. **Suppression key/scope:** the proposed key and scope semantics do not align. Define global vs scoped blocks and prove no scoped rule can weaken a global block.
4. **Reply taxonomy:** the prompt that treats objections as opt-outs conflicts with a taxonomy that separates objection and opt-out. Explicit opt-outs must suppress; ambiguous or policy-sensitive replies need conservative handling/escalation.
5. **Autonomy:** shadow-mode promotion rules conflict with a Free Site Check described as L3 after launch. Launch cannot by itself justify autonomy.
6. **Illustrative DDL:** generic entity IDs, UUID arrays without foreign keys, unconstrained statuses/ranges and incomplete delivery/outcome records weaken integrity.
7. **Provider ambiguity:** a timeout after provider acceptance must become an outcome_unknown state and be reconciled before retrying.
8. **Compliance:** legal review is an open dependency. Do not enable real outreach for a market/channel/recipient combination until the exact policy has been reviewed and tested.

## Commercial and planning issues

- Funnel rates, pricing, sector scores, care-plan attach rates and stage gates are hypotheses until observed in actual cohorts.
- The 12-week plan bundles too many major loops. Validate one bounded paid workflow before scaling the public audit, outbound, SEO publishing, partner and service-discovery systems.
- Outcome measurement needs a contract: baseline, definition, source/access basis, window, confounders and client acknowledgement.
- International data may improve benchmarking, but external benchmarks do not prove local willingness to pay. Keep market cohorts and P&L separate.

## Recommended sequence

1. Reconcile capacity and fully loaded unit economics.
2. Select a bounded offer using buyer access and observed willingness to pay, not subjective scores alone.
3. Define schema, policy and evaluation invariants.
4. Implement one end-to-end workflow with human approval.
5. Validate paid delivery, margin, rework and outcomes.
6. Automate measured bottlenecks; defer wider platform breadth.

## Confidence and limits

- **High confidence:** the remote was empty and the current connection has push permission; direct API observations.
- **High confidence:** the capacity arithmetic is correct if all 1,650 mini-checks receive a quarter-hour review; the denominator is not established.
- **High confidence:** the cited reply taxonomy, suppression, autonomy and data-model problems are visible in the reviewed blueprint.
- **Unverified:** market demand, actual pricing, vendor account capability, legal sufficiency, deployed software, production safety and real client outcomes.
