# Verification plan

## Rule

Untested means **UNVERIFIED**, not PASS. Every pass claim records test command/method, version/commit, environment, sample and result.

## Required verification dimensions

| Dimension | Tests/evidence | Blocker examples |
|---|---|---|
| Commercial | paid pilot, buyer feedback, conversion denominators, cost and labor logs | no willingness-to-pay evidence; unbounded scope |
| Audit correctness | labeled representative sample, repeat runs, blinded verification, false-positive/negative review | unsupported or non-reproducible external claim |
| Data integrity | migration/rollback, duplicate ingestion, identity, foreign keys, ranges and transition tests | orphan evidence or invalid lifecycle state |
| Suppression/send | opt-out race, re-import, concurrency, timeout after provider acceptance, idempotent retries | duplicate send or suppression bypass |
| Security | SSRF, DNS/redirect variants, untrusted content, secret isolation and authorization | prohibited network access or secret exposure |
| Privacy/compliance | policy unit tests, source provenance, retention/deletion tests and approved market/channel matrix | enabled workflow with no approved rule |
| Reliability | bounded retry, dead-letter/replay, provider outage, backpressure, kill switch | retries amplify failure or spend is uncontrolled |
| Delivery | CI, preview, responsive/accessibility checks, dependency/security scans, smoke/rollback | no accepted scope or recovery path |
| Content/SEO | source/citation review, originality/value, indexability and duplicate checks | unsupported claim or scaled thin content |
| Economics | attribution, direct hours, rework, support, payment delay and margin by offer/market | material costs omitted |

## Autonomy promotion

Do not promote a stage based on aggregate accuracy alone. Require representative coverage, task-appropriate precision/recall or error measures, zero critical failures over a defined test window where appropriate, reviewer disagreement/calibration, drift monitoring, explicit rollback and accountable-owner approval. A security or legal gate cannot be offset by a high average score.

## First acceptance suite

1. Fresh database install and migration/rollback.
2. Invalid enum/range and orphan-reference rejection.
3. Duplicate import preserves canonical identity.
4. Evidence round-trip retains tool/model/policy version.
5. Verification mismatch blocks external claim.
6. Stale evidence triggers recheck before use.
7. Opt-out blocks queued/future sends and survives re-import.
8. An objection is not silently relabeled opt-out; ambiguous cases are escalated.
9. Concurrent idempotent dispatch produces no duplicate submission.
10. Provider accepts then client times out; retry reconciles without duplicate.
11. SSRF fixtures cover redirects, DNS changes, IPv6, private addresses and oversized responses.
12. Kill switch stops pending and new sends.
13. Market lacking an approved policy is blocked regardless of score.
14. Project cannot be accepted unless checks pass or an explicit waiver is recorded.
15. Outcome report includes baseline, metric, period, source/access basis and limitations.
16. A later rejected/retest-required finding review invalidates a previously verified claim.
17. Suppression rules cannot be deleted or rewritten; revocation is attributed and logged.
18. Dispatch state transitions reject illegal jumps and accepted outcomes are terminal facts.
19. A finding review cannot be backdated or future-dated.
20. Changing draft target/context/content invalidates approval and requires a new canonical hash.
16. A later rejected/retest-required finding review invalidates a previously verified claim.
17. Suppression rules cannot be deleted or rewritten; revocation is attributed and logged.
18. Dispatch state transitions reject illegal jumps and accepted outcomes are terminal facts.

## Reporting template

- **PASS:** exact test, commit/version, environment, sample, result and artifact.
- **FAIL:** expected vs actual, reproduction, severity and repair.
- **UNVERIFIED:** what was not run and exact dependency required.
- **ACCEPTED LIMITATION:** rationale, residual risk, mitigation and review trigger.
