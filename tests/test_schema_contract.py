from pathlib import Path

SQL = Path(__file__).parents[1].joinpath("db/migrations/0001_initial_core.sql").read_text(encoding="utf-8")


def test_schema_has_core_workflow_records():
    for table in (
        "organizations", "contact_points", "source_records", "touch_events", "audit_runs",
        "evidence_artifacts", "findings", "finding_evidence", "finding_reviews", "opportunities",
        "market_policy_decisions", "suppression_rules", "outbound_drafts", "outbound_draft_claims",
        "outbound_approval_events", "dispatch_attempts", "dispatch_events", "cost_events",
        "outcome_snapshots", "audit_events",
    ):
        assert f"CREATE TABLE {table} (" in SQL


def test_schema_has_explicit_failure_mode_guards():
    for marker in (
        "enforce_policy_allow_basis", "enforce_verified_finding_basis",
        "enforce_draft_approval_basis", "enforce_dispatch_gate",
        "reject_append_only_mutation", "outcome_unknown",
        "source record % does not explicitly permit purpose",
        "active suppression blocks dispatch",
    ):
        assert marker in SQL
