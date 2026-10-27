# Data model gap register

This document is a design review of the strategy/blueprint's illustrative schema, not a claim that a database exists or has been deployed.

## High-priority integrity gaps

| ID | Finding | Risk | Required repair and test |
|---|---|---|---|
| DM-01 | Suppression rows include a scope dimension but the proposed key is only (channel, address_hash). | Scope semantics cannot be represented consistently; a narrower record could accidentally weaken a global block. | Decide whether suppression is global-only or model subject plus many scoped policies. Test that scoped rules never override global suppression. |
| DM-02 | Generic entity/entity_id state events do not enforce a foreign key to the target entity. | Orphaned or mistyped event history. | Use typed event tables or enforceable aggregate/event design. Test invalid references. |
| DM-03 | An array of UUID claim IDs has no foreign-key enforcement. | Activity can cite nonexistent evidence/findings. | Use a normalized join table with a foreign key. Test rejection of missing IDs. |
| DM-04 | Contact uniqueness on channel/address may conflate contact identity with organization relationship. | Shared addresses and legitimate multi-organization relationships become ambiguous. | Separate identity and organization-contact relationships where required; test duplicate ingestion and shared addresses. |
| DM-05 | Status, severity, score and probability values lack complete domains/range constraints. | Invalid states and misleading reporting. | Use enums/reference tables/check constraints and transition guards; test invalid inputs. |
| DM-06 | The sample source model does not fully implement immutable first touch plus append-only touch history. | Attribution becomes incomplete or contradictory. | Add append-only touch events with source/campaign/actor/time/evidence and a stable first-touch event reference. |
| DM-07 | Project delivery, commercial terms, costs and outcome snapshots are not fully modeled. | Revenue, scope, labor, acceptance, support and results cannot be reconciled. | Define project/SOW/milestone/acceptance/change request, cost event, invoice/payment reference and outcome snapshot records. |
| DM-08 | Consent/objection/suppression and deletion lifecycles are underspecified. | Cannot demonstrate why a channel action was permitted or whether deletion completed across systems. | Record source, purpose, policy version, decision, evidence, retention/deletion request and completion; minimize unnecessary data. |
| DM-09 | Provider timeout after provider acceptance is not represented explicitly. | A retry may create a duplicate external send. | Model queued/claimed/submitting/accepted/failed/outcome_unknown plus provider IDs and reconciliation. Test timeout-after-acceptance and concurrent retries. |
| DM-10 | Prompt, model, policy and evaluation versions are not consistently first-class. | Results and autonomy promotions cannot be reproduced after updates. | Record immutable evaluation runs and version identifiers; test rollback to a known-good version. |

## Conceptual minimum for a first production slice

Organization; contact identity; organization-contact relationship; source record; append-only touch event; audit run; evidence artifact; finding and independent verification; opportunity and score snapshot; offer; policy decision; approval; suppression subject/event; campaign/message draft/send attempt/provider event/reply; proposal; project/scope/milestone/acceptance/change request; cost event; outcome snapshot; job run; audit event/incident; and model/prompt/policy/evaluation versions.

This does not mandate one table per noun. A simpler schema is acceptable if it enforces the required constraints and histories.

## Invariants

1. Suppression always overrides qualification, score, campaign eligibility or prior approval.
2. Evidence is immutable; corrected interpretations create a new finding/version.
3. State changes record actor, reason, timestamp, version and correlation ID.
4. Outbound actions, money and deletion workflows have idempotency and explicit status transitions.
5. Re-importing a contact cannot reactivate a suppressed address.
6. Retention/deletion covers derived data, caches and relevant vendors, not only primary records.
7. An outcome always includes metric definition, baseline, time window, source/access basis and limitations.
8. No LLM-generated label is allowed to bypass deterministic state and policy checks.
