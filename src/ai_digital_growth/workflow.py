"""Fail-closed eligibility rules. This module has no network or sending capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence


class PolicyResult(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


class FindingState(str, Enum):
    VERIFIED = "verified"
    PROPOSED = "proposed"
    REJECTED = "rejected"
    STALE = "stale"


class GateStatus(str, Enum):
    BLOCKED = "blocked"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"
    ELIGIBLE_FOR_DRY_RUN = "eligible_for_dry_run"


class ReplyClass(str, Enum):
    EXPLICIT_OPT_OUT = "explicit_opt_out"
    OBJECTION = "objection"
    NOT_INTERESTED = "not_interested"
    INTERESTED = "interested"
    AMBIGUOUS = "ambiguous"


class ReplyAction(str, Enum):
    GLOBAL_SUPPRESS = "global_suppress"
    PAUSE_AND_REVIEW = "pause_and_review"
    END_CURRENT_CAMPAIGN = "end_current_campaign"
    ROUTE_TO_HUMAN = "route_to_human"
    PAUSE_AND_CLARIFY = "pause_and_clarify"


@dataclass(frozen=True)
class PolicyDecision:
    market: str
    recipient_type: str
    channel: str
    purpose: str
    source_id: str
    result: PolicyResult
    policy_version: str
    reviewer: str
    legal_review_reference: str | None
    valid_from: datetime
    valid_until: datetime | None = None

    def is_current(self, now: datetime) -> bool:
        if not isinstance(self.valid_from, datetime) or self.valid_from.tzinfo is None:
            return False
        if now.tzinfo is None:
            return False
        if self.valid_until is not None and (
            not isinstance(self.valid_until, datetime) or self.valid_until.tzinfo is None
        ):
            return False
        return self.valid_from <= now and (self.valid_until is None or now < self.valid_until)


@dataclass(frozen=True)
class EvidenceClaim:
    finding_id: str
    state: FindingState
    evidence_count: int
    captured_at: datetime
    maximum_age_days: int


@dataclass(frozen=True)
class OutboundDraftContext:
    market: str
    recipient_type: str
    channel: str
    purpose: str
    source_id: str
    claims: Sequence[EvidenceClaim]
    policy: PolicyDecision | None
    suppressed: bool
    human_approved: bool
    approval_actor: str | None = None
    approval_at: datetime | None = None


@dataclass(frozen=True)
class GateResult:
    status: GateStatus
    reasons: tuple[str, ...]


def _age_days(now: datetime, captured_at: datetime) -> float | None:
    if not isinstance(captured_at, datetime) or now.tzinfo is None or captured_at.tzinfo is None:
        return None
    return (now - captured_at).total_seconds() / 86400


def evaluate_outbound_draft(context: OutboundDraftContext, now: datetime | None = None) -> GateResult:
    """Evaluate the draft for human approval/dry-run only; never dispatches externally."""
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        return GateResult(GateStatus.BLOCKED, ("Evaluation clock must be timezone-aware.",))
    if context.suppressed:
        return GateResult(GateStatus.BLOCKED, ("Applicable suppression is active; it overrides all other eligibility.",))

    blockers: list[str] = []
    for name in ("market", "recipient_type", "channel", "purpose", "source_id"):
        value = getattr(context, name, None)
        if not isinstance(value, str) or not value.strip():
            blockers.append(f"Required context field {name} is missing.")

    policy = context.policy
    if policy is None:
        blockers.append("No exact market/channel/source policy decision exists.")
    else:
        matches = (
            policy.market == context.market
            and policy.recipient_type == context.recipient_type
            and policy.channel == context.channel
            and policy.purpose == context.purpose
            and policy.source_id == context.source_id
        )
        if not matches:
            blockers.append("Policy does not exactly match market, recipient, channel, purpose and source.")
        if policy.result is not PolicyResult.ALLOW:
            blockers.append(f"Policy result is {policy.result.value}, not allow.")
        if not isinstance(policy.policy_version, str) or not policy.policy_version.strip():
            blockers.append("Policy version is required.")
        if not isinstance(policy.reviewer, str) or not policy.reviewer.strip():
            blockers.append("Accountable policy reviewer is required.")
        if policy.result is PolicyResult.ALLOW and not (
            isinstance(policy.legal_review_reference, str) and policy.legal_review_reference.strip()
        ):
            blockers.append("Allow decision needs a traceable legal/compliance clearance reference.")
        if not policy.is_current(now):
            blockers.append("Policy decision is not currently valid or has invalid timezone data.")

    if not context.claims:
        blockers.append("At least one evidence-backed claim is required.")
    for claim in context.claims:
        if not isinstance(claim.finding_id, str) or not claim.finding_id.strip():
            blockers.append("Finding ID is missing.")
        if claim.state is not FindingState.VERIFIED:
            blockers.append(f"Finding {claim.finding_id or '<missing-id>'} is not independently verified.")
        if claim.evidence_count < 1:
            blockers.append(f"Finding {claim.finding_id or '<missing-id>'} has no linked evidence.")
        if claim.maximum_age_days < 0:
            blockers.append(f"Finding {claim.finding_id or '<missing-id>'} has invalid freshness policy.")
        age = _age_days(now, claim.captured_at)
        if age is None:
            blockers.append(f"Finding {claim.finding_id or '<missing-id>'} has invalid timezone data.")
        elif age < 0:
            blockers.append(f"Finding {claim.finding_id or '<missing-id>'} is future-dated.")
        elif age > claim.maximum_age_days:
            blockers.append(f"Finding {claim.finding_id or '<missing-id>'} is stale ({age:.1f} days old).")

    if blockers:
        return GateResult(GateStatus.BLOCKED, tuple(blockers))
    if not context.human_approved:
        return GateResult(GateStatus.NEEDS_HUMAN_APPROVAL, ("Checks passed; durable human approval is required before dry-run.",))
    if not isinstance(context.approval_actor, str) or not context.approval_actor.strip():
        return GateResult(GateStatus.BLOCKED, ("Approval actor is missing.",))
    if not isinstance(context.approval_at, datetime) or context.approval_at.tzinfo is None:
        return GateResult(GateStatus.BLOCKED, ("Approval timestamp must be timezone-aware.",))
    if context.approval_at > now:
        return GateResult(GateStatus.BLOCKED, ("Approval timestamp is in the future.",))
    return GateResult(
        GateStatus.ELIGIBLE_FOR_DRY_RUN,
        ("Policy, suppression and evidence checks passed; dry-run only, not external dispatch.",),
    )


def action_for_reply(reply: ReplyClass) -> ReplyAction:
    """Keep explicit opt-out separate from objection; ambiguous cases stop automation."""
    return {
        ReplyClass.EXPLICIT_OPT_OUT: ReplyAction.GLOBAL_SUPPRESS,
        ReplyClass.OBJECTION: ReplyAction.PAUSE_AND_REVIEW,
        ReplyClass.NOT_INTERESTED: ReplyAction.END_CURRENT_CAMPAIGN,
        ReplyClass.INTERESTED: ReplyAction.ROUTE_TO_HUMAN,
        ReplyClass.AMBIGUOUS: ReplyAction.PAUSE_AND_CLARIFY,
    }[reply]
