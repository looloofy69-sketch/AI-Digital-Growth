-- AI Digital Growth migration 0001. Application-generated UUIDs; fresh PostgreSQL database only.
CREATE TABLE organizations (
 id UUID PRIMARY KEY, canonical_domain TEXT UNIQUE, display_name TEXT NOT NULL,
 home_market_code TEXT, suppression_hash BYTEA, domain_hash BYTEA,
 lifecycle_status TEXT NOT NULL DEFAULT 'discovered'
   CHECK (lifecycle_status IN ('discovered','validated','qualified','customer','inactive','excluded')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (canonical_domain IS NULL OR canonical_domain = lower(canonical_domain)),
 CHECK (suppression_hash IS NULL OR octet_length(suppression_hash) >= 32),
 CHECK (domain_hash IS NULL OR octet_length(domain_hash) >= 32)
);

CREATE TABLE contact_points (
 id UUID PRIMARY KEY, channel TEXT NOT NULL CHECK (channel IN ('email','phone','webform','other')),
 address_hash BYTEA NOT NULL, address_ciphertext BYTEA, verified_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(channel,address_hash),
 CHECK (octet_length(address_hash) >= 32),
 CHECK (address_ciphertext IS NULL OR octet_length(address_ciphertext) > 0)
);

CREATE TABLE source_records (
 id UUID PRIMARY KEY, market_code TEXT NOT NULL,
 source_type TEXT NOT NULL CHECK (source_type IN ('directory','website','referral','inbound','manual','other')),
 source_uri TEXT, accessed_at TIMESTAMPTZ NOT NULL, terms_snapshot_uri TEXT,
 permitted_purposes TEXT[] NOT NULL DEFAULT '{}',
 source_confidence SMALLINT NOT NULL CHECK (source_confidence BETWEEN 1 AND 5),
 evidence_metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (source_uri IS NULL OR length(trim(source_uri)) > 0)
);

CREATE TABLE organization_contacts (
 id UUID PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
 contact_point_id UUID NOT NULL REFERENCES contact_points(id) ON DELETE RESTRICT,
 role_label TEXT, source_record_id UUID REFERENCES source_records(id) ON DELETE RESTRICT,
 relationship_verified_at TIMESTAMPTZ, active BOOLEAN NOT NULL DEFAULT true,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX organization_contacts_unique_role_idx
 ON organization_contacts(organization_id,contact_point_id,COALESCE(role_label,''));

CREATE TABLE touch_events (
 id UUID PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
 organization_contact_id UUID REFERENCES organization_contacts(id) ON DELETE RESTRICT,
 source_record_id UUID REFERENCES source_records(id) ON DELETE RESTRICT,
 channel TEXT NOT NULL CHECK (channel IN ('website','referral','email','phone','social','event','inbound','other')),
 touch_type TEXT NOT NULL CHECK (touch_type IN ('discovered','visited','audit','inbound','outbound_draft','reply','meeting','proposal','won','lost','other')),
 occurred_at TIMESTAMPTZ NOT NULL, attribution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
 correlation_id UUID, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX touch_events_org_time_idx ON touch_events(organization_id,occurred_at);

CREATE TABLE audit_runs (
 id UUID PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
 source_record_id UUID REFERENCES source_records(id) ON DELETE RESTRICT, target_url TEXT NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
 tool_version TEXT NOT NULL, rule_version TEXT NOT NULL, input_fingerprint CHAR(64) NOT NULL,
 started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, error_code TEXT, error_summary TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
 CHECK (completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at))
);
CREATE INDEX audit_runs_org_created_idx ON audit_runs(organization_id,created_at DESC);

CREATE TABLE evidence_artifacts (
 id UUID PRIMARY KEY, audit_run_id UUID NOT NULL REFERENCES audit_runs(id) ON DELETE RESTRICT,
 evidence_type TEXT NOT NULL, source_url TEXT NOT NULL, captured_at TIMESTAMPTZ NOT NULL,
 content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
 storage_uri TEXT, media_type TEXT, evidence_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(audit_run_id,content_sha256),
 UNIQUE(id,audit_run_id)
);

CREATE TABLE findings (
 id UUID PRIMARY KEY, audit_run_id UUID NOT NULL REFERENCES audit_runs(id) ON DELETE RESTRICT,
 rule_id TEXT NOT NULL, finding_version INTEGER NOT NULL DEFAULT 1 CHECK (finding_version > 0),
 supersedes_finding_id UUID REFERENCES findings(id) ON DELETE RESTRICT,
 title TEXT NOT NULL, description TEXT NOT NULL,
 severity TEXT NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
 state TEXT NOT NULL DEFAULT 'proposed' CHECK (state IN ('proposed','verified','rejected','stale')),
 confidence NUMERIC(5,2) CHECK (confidence BETWEEN 0 AND 100),
 freshness_window_days INTEGER NOT NULL CHECK (freshness_window_days > 0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(audit_run_id,rule_id,finding_version), UNIQUE(id,finding_version), UNIQUE(id,audit_run_id)
);

CREATE TABLE finding_evidence (
 finding_id UUID NOT NULL, audit_run_id UUID NOT NULL, evidence_artifact_id UUID NOT NULL,
 relevance_note TEXT, PRIMARY KEY(finding_id,evidence_artifact_id),
 FOREIGN KEY(finding_id,audit_run_id) REFERENCES findings(id,audit_run_id) ON DELETE RESTRICT,
 FOREIGN KEY(evidence_artifact_id,audit_run_id) REFERENCES evidence_artifacts(id,audit_run_id) ON DELETE RESTRICT
);

CREATE TABLE finding_reviews (
 id UUID PRIMARY KEY, finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE RESTRICT,
 review_result TEXT NOT NULL CHECK (review_result IN ('verified','rejected','retest_required')),
 reviewer_type TEXT NOT NULL CHECK (reviewer_type IN ('human','independent_tool')),
 reviewer_id TEXT NOT NULL, verifier_version TEXT NOT NULL, rationale TEXT NOT NULL,
 reviewed_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX finding_reviews_latest_idx ON finding_reviews(finding_id,reviewed_at DESC,id DESC);

CREATE FUNCTION apply_finding_review_result() RETURNS trigger LANGUAGE plpgsql AS $
BEGIN
 IF NEW.review_result='rejected' THEN
   UPDATE findings SET state='rejected' WHERE id=NEW.finding_id AND state<>'rejected';
 ELSIF NEW.review_result='retest_required' THEN
   UPDATE findings SET state='stale' WHERE id=NEW.finding_id AND state IN ('verified','proposed');
 END IF;
 RETURN NEW;
END; $;
CREATE TRIGGER apply_finding_review_result AFTER INSERT ON finding_reviews
 FOR EACH ROW EXECUTE FUNCTION apply_finding_review_result();

CREATE TABLE opportunities (
 id UUID PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
 score NUMERIC(5,2) CHECK (score BETWEEN 0 AND 100), score_version TEXT NOT NULL,
 stage TEXT NOT NULL DEFAULT 'discovered'
   CHECK (stage IN ('discovered','audited','qualified','approved','contacted','interested','proposal','won','lost','delivering','retained','excluded')),
 proposed_offer TEXT, first_touch_event_id UUID REFERENCES touch_events(id) ON DELETE RESTRICT,
 next_action TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX opportunities_stage_score_idx ON opportunities(stage,score DESC NULLS LAST);

CREATE TABLE opportunity_findings (
 opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
 finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE RESTRICT,
 linked_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(opportunity_id,finding_id)
);

CREATE TABLE market_policy_decisions (
 id UUID PRIMARY KEY, market_code TEXT NOT NULL,
 recipient_type TEXT NOT NULL CHECK (recipient_type IN ('business_contact','consumer','public_entity','healthcare_related','other')),
 channel TEXT NOT NULL CHECK (channel IN ('email','phone','sms','social','webform','other')),
 purpose TEXT NOT NULL, source_record_id UUID NOT NULL REFERENCES source_records(id) ON DELETE RESTRICT,
 decision TEXT NOT NULL CHECK (decision IN ('allow','block','review')), policy_version TEXT NOT NULL,
 legal_review_reference TEXT, reviewed_by TEXT NOT NULL, reviewed_at TIMESTAMPTZ NOT NULL,
 valid_from TIMESTAMPTZ NOT NULL, valid_until TIMESTAMPTZ, rationale TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (valid_until IS NULL OR valid_until > valid_from),
 CHECK (length(trim(policy_version)) > 0), CHECK (length(trim(reviewed_by)) > 0)
);
CREATE INDEX market_policy_lookup_idx ON market_policy_decisions
 (market_code,recipient_type,channel,purpose,source_record_id,valid_from DESC);

CREATE TABLE suppression_rules (
 id UUID PRIMARY KEY, subject_type TEXT NOT NULL CHECK (subject_type IN ('contact_point','organization','domain')),
 subject_hash BYTEA NOT NULL, channel TEXT NOT NULL CHECK (channel IN ('email','phone','sms','social','all')),
 scope_type TEXT NOT NULL CHECK (scope_type IN ('global','market','purpose','campaign')),
 scope_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
 reason TEXT NOT NULL, created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 revoked_by TEXT, revoked_at TIMESTAMPTZ, revocation_reason TEXT,
 CHECK (octet_length(subject_hash) >= 32),
 CHECK ((scope_type='global' AND scope_key='*') OR (scope_type<>'global' AND scope_key<>'*')),
 CHECK ((status='active' AND revoked_at IS NULL AND revoked_by IS NULL AND revocation_reason IS NULL)
     OR (status='revoked' AND revoked_at IS NOT NULL AND revoked_by IS NOT NULL AND length(trim(revocation_reason))>0))
);
CREATE UNIQUE INDEX suppression_active_rule_unique ON suppression_rules(subject_type,subject_hash,channel,scope_type,scope_key) WHERE status='active';
CREATE INDEX suppression_subject_lookup_idx ON suppression_rules(subject_type,subject_hash,channel) WHERE status='active';

CREATE TABLE suppression_events (
 id UUID PRIMARY KEY, suppression_rule_id UUID NOT NULL REFERENCES suppression_rules(id) ON DELETE RESTRICT,
 event_type TEXT NOT NULL CHECK (event_type IN ('created','revoked','matched','reimport_blocked')),
 actor TEXT NOT NULL, source_event_id TEXT, reason TEXT NOT NULL,
 occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE FUNCTION enforce_suppression_rule_lifecycle() RETURNS trigger LANGUAGE plpgsql AS $
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'suppression rules cannot be deleted; revoke with an attributable event';
 END IF;
 IF OLD.status<>'active' OR NEW.status<>'revoked' THEN
   RAISE EXCEPTION 'suppression rules may only transition once from active to revoked';
 END IF;
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.subject_type IS DISTINCT FROM OLD.subject_type
    OR NEW.subject_hash IS DISTINCT FROM OLD.subject_hash OR NEW.channel IS DISTINCT FROM OLD.channel
    OR NEW.scope_type IS DISTINCT FROM OLD.scope_type OR NEW.scope_key IS DISTINCT FROM OLD.scope_key
    OR NEW.reason IS DISTINCT FROM OLD.reason OR NEW.created_by IS DISTINCT FROM OLD.created_by
    OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
   RAISE EXCEPTION 'suppression rule identity and creation facts are immutable';
 END IF;
 IF NEW.revoked_by IS NULL OR length(trim(NEW.revoked_by))=0
    OR NEW.revoked_at IS NULL OR NEW.revoked_at<OLD.created_at
    OR NEW.revocation_reason IS NULL OR length(trim(NEW.revocation_reason))=0 THEN
   RAISE EXCEPTION 'revocation requires actor, timestamp, and reason';
 END IF;
 RETURN NEW;
END; $;
CREATE TRIGGER suppression_rule_lifecycle BEFORE UPDATE OR DELETE ON suppression_rules
 FOR EACH ROW EXECUTE FUNCTION enforce_suppression_rule_lifecycle();

CREATE FUNCTION audit_suppression_rule_change() RETURNS trigger LANGUAGE plpgsql AS $
BEGIN
 IF TG_OP='INSERT' THEN
   INSERT INTO suppression_events(id,suppression_rule_id,event_type,actor,reason,occurred_at,event_metadata)
   VALUES (gen_random_uuid(),NEW.id,'created',NEW.created_by,NEW.reason,NEW.created_at,
           jsonb_build_object('scope_type',NEW.scope_type,'scope_key',NEW.scope_key,'channel',NEW.channel));
 ELSIF OLD.status='active' AND NEW.status='revoked' THEN
   INSERT INTO suppression_events(id,suppression_rule_id,event_type,actor,reason,occurred_at,event_metadata)
   VALUES (gen_random_uuid(),NEW.id,'revoked',NEW.revoked_by,NEW.revocation_reason,NEW.revoked_at,
           jsonb_build_object('scope_type',NEW.scope_type,'scope_key',NEW.scope_key,'channel',NEW.channel));
 END IF;
 RETURN NEW;
END; $;
CREATE TRIGGER suppression_rule_audit AFTER INSERT OR UPDATE OF status ON suppression_rules
 FOR EACH ROW EXECUTE FUNCTION audit_suppression_rule_change();

CREATE TABLE outbound_drafts (
 id UUID PRIMARY KEY, opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
 organization_contact_id UUID NOT NULL REFERENCES organization_contacts(id) ON DELETE RESTRICT,
 source_record_id UUID NOT NULL REFERENCES source_records(id) ON DELETE RESTRICT,
 policy_decision_id UUID NOT NULL REFERENCES market_policy_decisions(id) ON DELETE RESTRICT,
 market_code TEXT NOT NULL, recipient_type TEXT NOT NULL, channel TEXT NOT NULL,
 purpose TEXT NOT NULL, campaign_code TEXT, subject TEXT, body TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','needs_review','approved','rejected','cancelled')),
 content_hash CHAR(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE outbound_draft_claims (
 draft_id UUID NOT NULL REFERENCES outbound_drafts(id) ON DELETE RESTRICT,
 finding_id UUID NOT NULL, finding_version INTEGER NOT NULL CHECK (finding_version > 0),
 PRIMARY KEY(draft_id,finding_id,finding_version),
 FOREIGN KEY(finding_id,finding_version) REFERENCES findings(id,finding_version) ON DELETE RESTRICT
);

CREATE TABLE outbound_approval_events (
 id UUID PRIMARY KEY, draft_id UUID NOT NULL REFERENCES outbound_drafts(id) ON DELETE RESTRICT,
 decision TEXT NOT NULL CHECK (decision IN ('approved','rejected','revoked')),
 actor_id TEXT NOT NULL CHECK (length(trim(actor_id)) > 0), rationale TEXT NOT NULL,
 draft_content_hash CHAR(64) NOT NULL CHECK (draft_content_hash ~ '^[0-9a-f]{64}$'),
 occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dispatch_attempts (
 id UUID PRIMARY KEY, draft_id UUID NOT NULL REFERENCES outbound_drafts(id) ON DELETE RESTRICT,
 idempotency_key TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL CHECK (status IN ('queued','claimed','submitting','accepted','failed','outcome_unknown','cancelled')),
 provider_name TEXT, provider_message_id TEXT UNIQUE,
 attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 last_error_code TEXT, last_error_summary TEXT
);

CREATE TABLE dispatch_events (
 id UUID PRIMARY KEY, dispatch_attempt_id UUID NOT NULL REFERENCES dispatch_attempts(id) ON DELETE RESTRICT,
 event_type TEXT NOT NULL CHECK (event_type IN ('queued','claimed','submitting','accepted','failed','outcome_unknown','reconciled','cancelled','suppression_blocked')),
 occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), provider_event_id TEXT, reason TEXT,
 event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE cost_events (
 id UUID PRIMARY KEY, opportunity_id UUID REFERENCES opportunities(id) ON DELETE RESTRICT,
 market_code TEXT NOT NULL, offer_code TEXT,
 cost_type TEXT NOT NULL CHECK (cost_type IN ('labor','tooling','acquisition','delivery','support','payment_fee','refund','other')),
 amount NUMERIC(14,2) NOT NULL CHECK (amount >= 0), currency CHAR(3) NOT NULL,
 quantity NUMERIC(14,4) NOT NULL DEFAULT 1 CHECK (quantity >= 0), unit TEXT,
 occurred_at TIMESTAMPTZ NOT NULL, evidence_reference TEXT, recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX cost_events_market_date_idx ON cost_events(market_code,occurred_at);

CREATE TABLE outcome_snapshots (
 id UUID PRIMARY KEY, opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
 metric_name TEXT NOT NULL, metric_definition TEXT NOT NULL, value_numeric NUMERIC(18,4),
 value_text TEXT, unit TEXT, period_start DATE NOT NULL, period_end DATE NOT NULL,
 source_reference TEXT NOT NULL, access_basis TEXT NOT NULL, confounders TEXT,
 confidence TEXT NOT NULL CHECK (confidence IN ('low','medium','high')),
 captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (period_end >= period_start), CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL)
);

CREATE TABLE audit_events (
 id UUID PRIMARY KEY, entity_type TEXT NOT NULL, entity_id UUID NOT NULL, event_type TEXT NOT NULL,
 actor_type TEXT NOT NULL CHECK (actor_type IN ('human','system','agent','provider')),
 actor_id TEXT NOT NULL, occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), correlation_id UUID,
 details JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX audit_events_entity_idx ON audit_events(entity_type,entity_id,occurred_at);

CREATE FUNCTION enforce_policy_allow_basis() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source_allows_purpose BOOLEAN;
BEGIN
 IF NEW.decision='allow' THEN
   SELECT (NEW.purpose = ANY(permitted_purposes)) INTO source_allows_purpose FROM source_records WHERE id=NEW.source_record_id;
   IF source_allows_purpose IS DISTINCT FROM TRUE THEN
     RAISE EXCEPTION 'source record % does not explicitly permit purpose %',NEW.source_record_id,NEW.purpose;
   END IF;
   IF NEW.legal_review_reference IS NULL OR length(trim(NEW.legal_review_reference))=0 THEN
     RAISE EXCEPTION 'allow policy decision requires a legal/compliance clearance reference';
   END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER market_policy_allow_basis BEFORE INSERT ON market_policy_decisions
 FOR EACH ROW EXECUTE FUNCTION enforce_policy_allow_basis();

CREATE FUNCTION enforce_verified_finding_basis() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE latest_review_result TEXT;
BEGIN
 IF NEW.state='verified' THEN
   IF NOT EXISTS (SELECT 1 FROM finding_evidence WHERE finding_id=NEW.id) THEN
     RAISE EXCEPTION 'finding % cannot be verified without linked evidence',NEW.id;
   END IF;
   SELECT review_result INTO latest_review_result FROM finding_reviews
    WHERE finding_id=NEW.id ORDER BY reviewed_at DESC,id DESC LIMIT 1;
   IF latest_review_result IS DISTINCT FROM 'verified' THEN
     RAISE EXCEPTION 'finding % cannot be verified without a latest affirmative review',NEW.id;
   END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER verified_finding_basis BEFORE INSERT OR UPDATE OF state ON findings
 FOR EACH ROW EXECUTE FUNCTION enforce_verified_finding_basis();

CREATE FUNCTION enforce_draft_approval_basis() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.status='approved' AND NOT EXISTS (
   SELECT 1 FROM outbound_approval_events a
    WHERE a.draft_id=NEW.id AND a.decision='approved'
      AND a.draft_content_hash=NEW.content_hash AND a.occurred_at<=now()
      AND NOT EXISTS (SELECT 1 FROM outbound_approval_events later
        WHERE later.draft_id=a.draft_id
          AND (later.occurred_at>a.occurred_at OR (later.occurred_at=a.occurred_at AND later.id>a.id)))
 ) THEN
   RAISE EXCEPTION 'draft % lacks a current approval for its exact content hash',NEW.id;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER draft_approval_basis BEFORE INSERT OR UPDATE OF status,content_hash ON outbound_drafts
 FOR EACH ROW EXECUTE FUNCTION enforce_draft_approval_basis();

CREATE FUNCTION enforce_dispatch_gate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE draft outbound_drafts%ROWTYPE; policy_row market_policy_decisions%ROWTYPE;
        has_suppression BOOLEAN; has_claims BOOLEAN; has_invalid_claim BOOLEAN;
BEGIN
 -- Provider acceptance is a fact: reconcile it even if a suppression arrived after submission.
 IF NEW.status='accepted' THEN
   IF TG_OP='INSERT' OR OLD.status NOT IN ('submitting','outcome_unknown') THEN
     RAISE EXCEPTION 'accepted requires a prior submitting/outcome_unknown state';
   END IF;
   IF NEW.provider_message_id IS NULL OR length(trim(NEW.provider_message_id))=0
      OR NEW.provider_name IS NULL OR length(trim(NEW.provider_name))=0 THEN
     RAISE EXCEPTION 'accepted requires provider name and message ID';
   END IF;
   RETURN NEW;
 END IF;
 IF NEW.status IN ('queued','claimed','submitting') THEN
   SELECT * INTO draft FROM outbound_drafts WHERE id=NEW.draft_id FOR SHARE;
   IF NOT FOUND OR draft.status<>'approved' THEN RAISE EXCEPTION 'dispatch requires an approved draft'; END IF;
   SELECT * INTO policy_row FROM market_policy_decisions WHERE id=draft.policy_decision_id FOR SHARE;
   IF NOT FOUND OR policy_row.decision<>'allow'
      OR policy_row.market_code<>draft.market_code OR policy_row.recipient_type<>draft.recipient_type
      OR policy_row.channel<>draft.channel OR policy_row.purpose<>draft.purpose
      OR policy_row.source_record_id<>draft.source_record_id OR policy_row.valid_from>now()
      OR (policy_row.valid_until IS NOT NULL AND policy_row.valid_until<=now())
      OR policy_row.legal_review_reference IS NULL OR length(trim(policy_row.legal_review_reference))=0 THEN
     RAISE EXCEPTION 'dispatch policy is absent, mismatched, expired, or lacks clearance';
   END IF;
   IF NOT EXISTS (SELECT 1 FROM outbound_approval_events a
      WHERE a.draft_id=draft.id AND a.decision='approved' AND a.draft_content_hash=draft.content_hash
      AND NOT EXISTS (SELECT 1 FROM outbound_approval_events later WHERE later.draft_id=a.draft_id
        AND (later.occurred_at>a.occurred_at OR (later.occurred_at=a.occurred_at AND later.id>a.id)))) THEN
     RAISE EXCEPTION 'dispatch requires latest approval for current content hash';
   END IF;
   SELECT EXISTS (SELECT 1 FROM outbound_draft_claims WHERE draft_id=draft.id) INTO has_claims;
   IF NOT has_claims THEN RAISE EXCEPTION 'dispatch requires an evidence-backed finding claim'; END IF;
   SELECT EXISTS (SELECT 1 FROM outbound_draft_claims dc
      JOIN findings f ON f.id=dc.finding_id AND f.finding_version=dc.finding_version
      WHERE dc.draft_id=draft.id AND (
        f.state<>'verified'
        OR NOT EXISTS (SELECT 1 FROM finding_reviews r WHERE r.finding_id=f.id AND r.review_result='verified'
          AND NOT EXISTS (SELECT 1 FROM finding_reviews later WHERE later.finding_id=r.finding_id
            AND (later.reviewed_at>r.reviewed_at OR (later.reviewed_at=r.reviewed_at AND later.id>r.id))))
        OR NOT EXISTS (SELECT 1 FROM finding_evidence fe JOIN evidence_artifacts ea ON ea.id=fe.evidence_artifact_id
          WHERE fe.finding_id=f.id AND ea.captured_at+(f.freshness_window_days*interval '1 day')>now())
      )
   ) INTO has_invalid_claim;
   IF has_invalid_claim THEN RAISE EXCEPTION 'dispatch contains unverified, unsupported, or stale claims'; END IF;
   SELECT EXISTS (
     SELECT 1 FROM organization_contacts oc
     JOIN contact_points cp ON cp.id=oc.contact_point_id
     JOIN outbound_drafts d ON d.organization_contact_id=oc.id
     JOIN opportunities o ON o.id=d.opportunity_id
     JOIN organizations org ON org.id=o.organization_id
     JOIN suppression_rules sr ON sr.status='active' AND sr.channel IN (d.channel,'all')
      AND ((sr.subject_type='contact_point' AND sr.subject_hash=cp.address_hash)
        OR (sr.subject_type='organization' AND org.suppression_hash IS NOT NULL AND sr.subject_hash=org.suppression_hash)
        OR (sr.subject_type='domain' AND org.domain_hash IS NOT NULL AND sr.subject_hash=org.domain_hash))
      AND (sr.scope_type='global'
        OR (sr.scope_type='market' AND sr.scope_key=d.market_code)
        OR (sr.scope_type='purpose' AND sr.scope_key=d.purpose)
        OR (sr.scope_type='campaign' AND d.campaign_code IS NOT NULL AND sr.scope_key=d.campaign_code))
     WHERE d.id=draft.id
   ) INTO has_suppression;
   IF has_suppression THEN RAISE EXCEPTION 'active suppression blocks dispatch'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE FUNCTION enforce_dispatch_transition() RETURNS trigger LANGUAGE plpgsql AS $
DECLARE allowed BOOLEAN := FALSE;
BEGIN
 IF TG_OP='INSERT' THEN
   IF NEW.status<>'queued' OR NEW.attempt_count<>0 OR NEW.provider_message_id IS NOT NULL THEN
     RAISE EXCEPTION 'new dispatch attempts must begin queued with zero attempts and no provider message ID';
   END IF;
   RETURN NEW;
 END IF;
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.draft_id IS DISTINCT FROM OLD.draft_id
    OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
   RAISE EXCEPTION 'dispatch identity, draft, idempotency key, and creation time are immutable';
 END IF;
 IF NEW.attempt_count<OLD.attempt_count OR NEW.updated_at<OLD.updated_at THEN
   RAISE EXCEPTION 'attempt count and update timestamp cannot move backwards';
 END IF;
 IF OLD.provider_message_id IS NOT NULL AND NEW.provider_message_id IS DISTINCT FROM OLD.provider_message_id THEN
   RAISE EXCEPTION 'provider message ID is immutable once known';
 END IF;
 IF NEW.status=OLD.status THEN
   IF NEW.attempt_count<>OLD.attempt_count THEN RAISE EXCEPTION 'attempt count changes only on a claim'; END IF;
   IF OLD.status IN ('accepted','cancelled') AND (
      NEW.provider_name IS DISTINCT FROM OLD.provider_name OR NEW.provider_message_id IS DISTINCT FROM OLD.provider_message_id) THEN
     RAISE EXCEPTION 'terminal dispatch metadata is immutable';
   END IF;
   RETURN NEW;
 END IF;
 CASE OLD.status
   WHEN 'queued' THEN allowed := NEW.status IN ('claimed','cancelled');
   WHEN 'claimed' THEN allowed := NEW.status IN ('submitting','queued','failed','cancelled');
   WHEN 'submitting' THEN allowed := NEW.status IN ('accepted','failed','outcome_unknown');
   WHEN 'outcome_unknown' THEN allowed := NEW.status IN ('accepted','failed');
   WHEN 'failed' THEN allowed := NEW.status='queued';
   ELSE allowed := FALSE;
 END CASE;
 IF NOT allowed THEN
   RAISE EXCEPTION 'invalid dispatch state transition: % -> %',OLD.status,NEW.status;
 END IF;
 IF OLD.status='queued' AND NEW.status='claimed' THEN
   IF NEW.attempt_count<>OLD.attempt_count+1 THEN RAISE EXCEPTION 'claim must increment attempt_count exactly once'; END IF;
 ELSIF NEW.attempt_count<>OLD.attempt_count THEN
   RAISE EXCEPTION 'attempt_count increments only when queued work is claimed';
 END IF;
 IF NEW.status<>'accepted' AND NEW.provider_message_id IS DISTINCT FROM OLD.provider_message_id THEN
   RAISE EXCEPTION 'provider message ID may only be set on accepted status';
 END IF;
 RETURN NEW;
END; $;
CREATE TRIGGER dispatch_transition_guard BEFORE INSERT OR UPDATE ON dispatch_attempts
 FOR EACH ROW EXECUTE FUNCTION enforce_dispatch_transition();

CREATE FUNCTION audit_dispatch_state_change() RETURNS trigger LANGUAGE plpgsql AS $
BEGIN
 IF TG_OP='INSERT' OR NEW.status IS DISTINCT FROM OLD.status THEN
   INSERT INTO dispatch_events(id,dispatch_attempt_id,event_type,occurred_at,reason,event_metadata)
   VALUES (gen_random_uuid(),NEW.id,NEW.status,NEW.updated_at,
           NEW.last_error_summary,jsonb_build_object('attempt_count',NEW.attempt_count,'provider_name',NEW.provider_name));
 END IF;
 RETURN NEW;
END; $;
CREATE TRIGGER dispatch_state_audit AFTER INSERT OR UPDATE OF status ON dispatch_attempts
 FOR EACH ROW EXECUTE FUNCTION audit_dispatch_state_change();

CREATE TRIGGER dispatch_final_gate BEFORE INSERT OR UPDATE OF status ON dispatch_attempts
 FOR EACH ROW EXECUTE FUNCTION enforce_dispatch_gate();

CREATE FUNCTION reject_append_only_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'table % is append-only; % is not permitted',TG_TABLE_NAME,TG_OP;
END; $$;
CREATE TRIGGER touch_events_append_only BEFORE UPDATE OR DELETE ON touch_events FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER evidence_artifacts_append_only BEFORE UPDATE OR DELETE ON evidence_artifacts FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER finding_reviews_append_only BEFORE UPDATE OR DELETE ON finding_reviews FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER market_policy_decisions_append_only BEFORE UPDATE OR DELETE ON market_policy_decisions FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER suppression_events_append_only BEFORE UPDATE OR DELETE ON suppression_events FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER outbound_approval_events_append_only BEFORE UPDATE OR DELETE ON outbound_approval_events FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER dispatch_events_append_only BEFORE UPDATE OR DELETE ON dispatch_events FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
