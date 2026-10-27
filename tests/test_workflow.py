from datetime import datetime, timedelta, timezone

import pytest

from ai_digital_growth.workflow import (
    EvidenceClaim, FindingState, GateStatus, OutboundDraftContext, PolicyDecision, PolicyResult,
    ReplyAction, ReplyClass, action_for_reply, evaluate_outbound_draft,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def policy(**overrides):
    values = dict(
        market="FR", recipient_type="business_contact", channel="email",
        purpose="website_audit_outreach", source_id="source-123", result=PolicyResult.ALLOW,
        policy_version="market-rules-1", reviewer="reviewer-1",
        legal_review_reference="clearance-record-1",
        valid_from=NOW - timedelta(days=1), valid_until=NOW + timedelta(days=1),
    )
    values.update(overrides)
    return PolicyDecision(**values)


def claim(**overrides):
    values = dict(
        finding_id="finding-123", state=FindingState.VERIFIED, evidence_count=1,
        captured_at=NOW - timedelta(hours=3), maximum_age_days=7,
    )
    values.update(overrides)
    return EvidenceClaim(**values)


def context(**overrides):
    values = dict(
        market="FR", recipient_type="business_contact", channel="email",
        purpose="website_audit_outreach", source_id="source-123", claims=[claim()],
        policy=policy(), suppressed=False, human_approved=False,
    )
    values.update(overrides)
    return OutboundDraftContext(**values)


def test_valid_draft_needs_human_approval_and_then_only_dry_run():
    assert evaluate_outbound_draft(context(), now=NOW).status is GateStatus.NEEDS_HUMAN_APPROVAL
    x = evaluate_outbound_draft(context(
        human_approved=True, approval_actor="operator-1", approval_at=NOW-timedelta(minutes=1)
    ), now=NOW)
    assert x.status is GateStatus.ELIGIBLE_FOR_DRY_RUN
    assert "not external dispatch" in x.reasons[0]


def test_suppression_overrides_everything():
    x = evaluate_outbound_draft(context(suppressed=True, human_approved=True), now=NOW)
    assert x.status is GateStatus.BLOCKED
    assert "suppression" in x.reasons[0].lower()


def test_missing_or_non_allow_policy_blocks():
    assert evaluate_outbound_draft(context(policy=None), now=NOW).status is GateStatus.BLOCKED
    assert evaluate_outbound_draft(context(policy=policy(result=PolicyResult.REVIEW)), now=NOW).status is GateStatus.BLOCKED
    assert evaluate_outbound_draft(context(policy=policy(result=PolicyResult.BLOCK)), now=NOW).status is GateStatus.BLOCKED
    assert evaluate_outbound_draft(context(policy=policy(legal_review_reference=None)), now=NOW).status is GateStatus.BLOCKED


@pytest.mark.parametrize("field,value", [
    ("market","DZ"), ("recipient_type","consumer"), ("channel","sms"),
    ("purpose","consumer_marketing"), ("source_id","different-source"),
])
def test_policy_requires_exact_context_match(field, value):
    assert evaluate_outbound_draft(context(policy=policy(**{field:value})), now=NOW).status is GateStatus.BLOCKED


def test_expired_or_naive_policy_blocks():
    assert evaluate_outbound_draft(context(policy=policy(valid_until=NOW-timedelta(seconds=1))), now=NOW).status is GateStatus.BLOCKED
    assert evaluate_outbound_draft(context(policy=policy(valid_from=datetime(2026,10,27))), now=NOW).status is GateStatus.BLOCKED


def test_unverified_missing_and_stale_evidence_blocks():
    for item in [
        claim(state=FindingState.PROPOSED), claim(evidence_count=0),
        claim(captured_at=NOW-timedelta(days=8)), claim(captured_at=NOW+timedelta(minutes=1)),
        claim(captured_at=datetime(2026,10,27)),
    ]:
        assert evaluate_outbound_draft(context(claims=[item]), now=NOW).status is GateStatus.BLOCKED


def test_no_claims_and_missing_approval_metadata_block():
    assert evaluate_outbound_draft(context(claims=[]), now=NOW).status is GateStatus.BLOCKED
    assert evaluate_outbound_draft(context(human_approved=True, approval_at=NOW), now=NOW).status is GateStatus.BLOCKED
    assert evaluate_outbound_draft(context(human_approved=True, approval_actor="op", approval_at=NOW+timedelta(seconds=1)), now=NOW).status is GateStatus.BLOCKED


def test_reply_objection_is_not_reclassified_as_opt_out():
    assert action_for_reply(ReplyClass.EXPLICIT_OPT_OUT) is ReplyAction.GLOBAL_SUPPRESS
    assert action_for_reply(ReplyClass.OBJECTION) is ReplyAction.PAUSE_AND_REVIEW
    assert action_for_reply(ReplyClass.AMBIGUOUS) is ReplyAction.PAUSE_AND_CLARIFY
    assert action_for_reply(ReplyClass.NOT_INTERESTED) is ReplyAction.END_CURRENT_CAMPAIGN
    assert action_for_reply(ReplyClass.INTERESTED) is ReplyAction.ROUTE_TO_HUMAN
