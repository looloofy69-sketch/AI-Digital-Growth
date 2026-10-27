from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not configured")
NOW = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture
def conn():
    connection = psycopg.connect(DATABASE_URL)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def make_approved_draft(conn):
    org_id, contact_id, source_id, relation_id = (uuid.uuid4() for _ in range(4))
    run_id, evidence_id, finding_id, opportunity_id = (uuid.uuid4() for _ in range(4))
    policy_id, draft_id, approval_id, touch_id = (uuid.uuid4() for _ in range(4))
    address_hash = hashlib.sha256(str(contact_id).encode("utf-8")).digest()
    body = "Reviewed test message"
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    conn.execute("INSERT INTO organizations(id,canonical_domain,display_name) VALUES (%s,%s,%s)",
                 (org_id,f"test-{org_id}.example.invalid","integration-test"))
    conn.execute("INSERT INTO contact_points(id,channel,address_hash,address_ciphertext) VALUES (%s,%s,%s,%s)",
                 (contact_id,"email",address_hash,b"encrypted-test-value"))
    conn.execute("INSERT INTO source_records(id,market_code,source_type,source_uri,accessed_at,permitted_purposes,source_confidence) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (source_id,"TEST","manual","https://example.invalid/source",NOW,["website_audit_outreach"],5))
    conn.execute("INSERT INTO organization_contacts(id,organization_id,contact_point_id,role_label,source_record_id) VALUES (%s,%s,%s,%s,%s)",
                 (relation_id,org_id,contact_id,"owner",source_id))
    conn.execute("INSERT INTO touch_events(id,organization_id,organization_contact_id,source_record_id,channel,touch_type,occurred_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (touch_id,org_id,relation_id,source_id,"website","discovered",NOW))
    conn.execute("INSERT INTO audit_runs(id,organization_id,source_record_id,target_url,status,tool_version,rule_version,input_fingerprint,started_at,completed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (run_id,org_id,source_id,"https://example.invalid","completed","test-tool","test-rules","a"*64,NOW-timedelta(minutes=2),NOW))
    conn.execute("INSERT INTO evidence_artifacts(id,audit_run_id,evidence_type,source_url,captured_at,content_sha256) VALUES (%s,%s,%s,%s,%s,%s)",
                 (evidence_id,run_id,"http_metadata","https://example.invalid",NOW,"b"*64))
    conn.execute("INSERT INTO findings(id,audit_run_id,rule_id,title,description,severity,state,confidence,freshness_window_days) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (finding_id,run_id,"test-rule","Test finding","Evidence-backed test claim","low","proposed",99,7))
    conn.execute("INSERT INTO finding_evidence(finding_id,audit_run_id,evidence_artifact_id) VALUES (%s,%s,%s)",
                 (finding_id,run_id,evidence_id))
    conn.execute("INSERT INTO finding_reviews(id,finding_id,review_result,reviewer_type,reviewer_id,verifier_version,rationale,reviewed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                 (uuid.uuid4(),finding_id,"verified","human","test-reviewer","v1","Evidence matches claim",NOW))
    conn.execute("UPDATE findings SET state='verified' WHERE id=%s",(finding_id,))
    conn.execute("INSERT INTO opportunities(id,organization_id,score,score_version,stage,first_touch_event_id,proposed_offer) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (opportunity_id,org_id,80,"score-v1","qualified",touch_id,"website_repair_sprint"))
    conn.execute("INSERT INTO market_policy_decisions(id,market_code,recipient_type,channel,purpose,source_record_id,decision,policy_version,legal_review_reference,reviewed_by,reviewed_at,valid_from,valid_until,rationale) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (policy_id,"TEST","business_contact","email","website_audit_outreach",source_id,"allow","policy-v1","clearance-test-ref","reviewer",NOW,NOW-timedelta(days=1),NOW+timedelta(days=1),"test-only clearance"))
    conn.execute("INSERT INTO outbound_drafts(id,opportunity_id,organization_contact_id,source_record_id,policy_decision_id,market_code,recipient_type,channel,purpose,subject,body,status,content_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (draft_id,opportunity_id,relation_id,source_id,policy_id,"TEST","business_contact","email","website_audit_outreach","Test subject",body,"draft",content_hash))
    conn.execute("INSERT INTO outbound_draft_claims(draft_id,finding_id,finding_version) VALUES (%s,%s,%s)",(draft_id,finding_id,1))
    conn.execute("INSERT INTO outbound_approval_events(id,draft_id,decision,actor_id,rationale,draft_content_hash,occurred_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (approval_id,draft_id,"approved","approver","exact-content approval",content_hash,NOW))
    conn.execute("UPDATE outbound_drafts SET status='approved' WHERE id=%s",(draft_id,))
    return contact_id, address_hash, draft_id


def test_migration_created_required_tables(conn):
    found = {x[0] for x in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname=current_schema()").fetchall()}
    assert {"organizations","source_records","audit_runs","evidence_artifacts","findings","finding_evidence",
            "finding_reviews","market_policy_decisions","suppression_rules","outbound_drafts",
            "outbound_approval_events","dispatch_attempts","dispatch_events"} <= found


def test_check_constraint_rejects_out_of_range_score(conn):
    org = uuid.uuid4()
    conn.execute("INSERT INTO organizations(id,display_name) VALUES (%s,%s)",(org,"test"))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO opportunities(id,organization_id,score,score_version) VALUES (%s,%s,%s,%s)",
                     (uuid.uuid4(),org,101,"test"))


def test_evidence_is_append_only(conn):
    org, run, evidence = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    conn.execute("INSERT INTO organizations(id,display_name) VALUES (%s,%s)",(org,"test"))
    conn.execute("INSERT INTO audit_runs(id,organization_id,target_url,status,tool_version,rule_version,input_fingerprint) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (run,org,"https://example.invalid","completed","test","test","a"*64))
    conn.execute("INSERT INTO evidence_artifacts(id,audit_run_id,evidence_type,source_url,captured_at,content_sha256) VALUES (%s,%s,%s,%s,now(),%s)",
                 (evidence,run,"metadata","https://example.invalid","b"*64))
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("UPDATE evidence_artifacts SET evidence_type='changed' WHERE id=%s",(evidence,))


def test_allow_policy_requires_source_permission_and_clearance(conn):
    source = uuid.uuid4()
    conn.execute("INSERT INTO source_records(id,market_code,source_type,accessed_at,permitted_purposes,source_confidence) VALUES (%s,%s,%s,%s,%s,%s)",
                 (source,"TEST","manual",NOW,[],5))
    with pytest.raises(psycopg.errors.RaiseException, match="does not explicitly permit purpose"):
        conn.execute("INSERT INTO market_policy_decisions(id,market_code,recipient_type,channel,purpose,source_record_id,decision,policy_version,legal_review_reference,reviewed_by,reviewed_at,valid_from,rationale) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (uuid.uuid4(),"TEST","business_contact","email","website_audit_outreach",source,"allow","v1","clearance","reviewer",NOW,NOW,"test"))


def test_dispatch_gate_and_late_optout_reconciliation(conn):
    contact, addr_hash, draft = make_approved_draft(conn)
    attempt = uuid.uuid4()
    conn.execute("INSERT INTO dispatch_attempts(id,draft_id,idempotency_key,status) VALUES (%s,%s,%s,%s)",
                 (attempt,draft,f"idem-{attempt}","queued"))
    conn.execute("UPDATE dispatch_attempts SET status='claimed',attempt_count=1 WHERE id=%s",(attempt,))
    conn.execute("UPDATE dispatch_attempts SET status='submitting' WHERE id=%s",(attempt,))
    conn.execute("INSERT INTO suppression_rules(id,subject_type,subject_hash,channel,scope_type,scope_key,status,reason,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (uuid.uuid4(),"contact_point",addr_hash,"all","global","*","active","late opt-out","test"))
    # Provider acceptance must still be recorded truthfully if suppression arrives after submission.
    conn.execute("UPDATE dispatch_attempts SET status='accepted',provider_name='test-provider',provider_message_id=%s WHERE id=%s",
                 (f"message-{attempt}",attempt))


def test_active_suppression_blocks_new_dispatch(conn):
    _, addr_hash, draft = make_approved_draft(conn)
    conn.execute("INSERT INTO suppression_rules(id,subject_type,subject_hash,channel,scope_type,scope_key,status,reason,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (uuid.uuid4(),"contact_point",addr_hash,"all","global","*","active","test opt-out","test"))
    with pytest.raises(psycopg.errors.RaiseException, match="suppression"):
        conn.execute("INSERT INTO dispatch_attempts(id,draft_id,idempotency_key,status) VALUES (%s,%s,%s,%s)",
                     (uuid.uuid4(),draft,f"blocked-{uuid.uuid4()}","queued"))


def test_rejected_latest_review_invalidates_a_previously_verified_finding(conn):
    _, _, draft = make_approved_draft(conn)
    finding = conn.execute("SELECT finding_id FROM outbound_draft_claims WHERE draft_id=%s",(draft,)).fetchone()[0]
    conn.execute("INSERT INTO finding_reviews(id,finding_id,review_result,reviewer_type,reviewer_id,verifier_version,rationale,reviewed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                 (uuid.uuid4(),finding,"rejected","human","second-reviewer","v2","Second review contradicted the claim",NOW+timedelta(seconds=5)))
    state = conn.execute("SELECT state FROM findings WHERE id=%s",(finding,)).fetchone()[0]
    assert state == "rejected"
    with pytest.raises(psycopg.errors.RaiseException, match="unverified"):
        conn.execute("INSERT INTO dispatch_attempts(id,draft_id,idempotency_key,status) VALUES (%s,%s,%s,%s)",
                     (uuid.uuid4(),draft,f"invalidated-{uuid.uuid4()}","queued"))


def test_suppression_rules_cannot_be_deleted(conn):
    _, address_hash, _ = make_approved_draft(conn)
    rule = uuid.uuid4()
    conn.execute("INSERT INTO suppression_rules(id,subject_type,subject_hash,channel,scope_type,scope_key,status,reason,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                 (rule,"contact_point",address_hash,"all","global","*","active","explicit opt-out","reply-handler"))
    created = conn.execute("SELECT count(*) FROM suppression_events WHERE suppression_rule_id=%s AND event_type='created'",(rule,)).fetchone()[0]
    assert created == 1
    with pytest.raises(psycopg.errors.RaiseException, match="cannot be deleted"):
        conn.execute("DELETE FROM suppression_rules WHERE id=%s",(rule,))


def test_dispatch_transition_machine_rejects_illegal_jump(conn):
    _, _, draft = make_approved_draft(conn)
    attempt = uuid.uuid4()
    conn.execute("INSERT INTO dispatch_attempts(id,draft_id,idempotency_key,status) VALUES (%s,%s,%s,%s)",
                 (attempt,draft,f"bad-transition-{attempt}","queued"))
    with pytest.raises(psycopg.errors.RaiseException, match="invalid dispatch state transition"):
        conn.execute("UPDATE dispatch_attempts SET status='submitting' WHERE id=%s",(attempt,))


def test_finding_cannot_be_verified_without_review(conn):
    org, run, ev, finding = (uuid.uuid4() for _ in range(4))
    conn.execute("INSERT INTO organizations(id,display_name) VALUES (%s,%s)",(org,"test"))
    conn.execute("INSERT INTO audit_runs(id,organization_id,target_url,status,tool_version,rule_version,input_fingerprint) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (run,org,"https://example.invalid","completed","test","test","c"*64))
    conn.execute("INSERT INTO evidence_artifacts(id,audit_run_id,evidence_type,source_url,captured_at,content_sha256) VALUES (%s,%s,%s,%s,now(),%s)",
                 (ev,run,"test","https://example.invalid","d"*64))
    conn.execute("INSERT INTO findings(id,audit_run_id,rule_id,title,description,severity,state,freshness_window_days) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                 (finding,run,"r","Test","Desc","low","proposed",7))
    conn.execute("INSERT INTO finding_evidence(finding_id,audit_run_id,evidence_artifact_id) VALUES (%s,%s,%s)",(finding,run,ev))
    with pytest.raises(psycopg.errors.RaiseException, match="affirmative review"):
        conn.execute("UPDATE findings SET state='verified' WHERE id=%s",(finding,))
