-- Customer Engagement (P0) — Human Desk: inbox / thread / message / assignment / decision request.
-- Tham chiếu CRM sales.* / commercial.* bằng workspace-scoped ref; KHÔNG nhân bản CRM.
CREATE SCHEMA IF NOT EXISTS engagement;

CREATE TABLE engagement.engagement_inboxes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  channel_type TEXT NOT NULL,                 -- 'api' | 'web_chat' | 'email' | 'zalo' | 'whatsapp' | 'facebook'
  name TEXT NOT NULL,
  locale TEXT,
  business_hours JSONB,
  sla_policy JSONB NOT NULL,                  -- seed P0: {version, timezone, business_calendar, tiers:{standard,priority,vip}} — xem "P0 policy defaults"
  default_tier TEXT NOT NULL DEFAULT 'standard',  -- standard | priority | vip
  default_team_id BIGINT,
  allowed_agent_spec_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  connector_installation_ref TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_inboxes_workspace ON engagement.engagement_inboxes(workspace_id);
ALTER TABLE engagement.engagement_inboxes ADD CONSTRAINT uq_engagement_inboxes_id_ws UNIQUE (id, workspace_id);

CREATE TABLE engagement.engagement_channel_endpoints (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  inbox_id BIGINT NOT NULL,
  provider_ref TEXT NOT NULL,
  delivery_capability TEXT NOT NULL DEFAULT 'send',
  verification_config_ref TEXT,
  secret_ref TEXT,                            -- opaque reference; KHÔNG lưu secret thật
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (inbox_id, workspace_id)
    REFERENCES engagement.engagement_inboxes(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_channel_endpoints_inbox ON engagement.engagement_channel_endpoints(inbox_id);

CREATE TABLE engagement.engagement_threads (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  inbox_id BIGINT NOT NULL,
  contact_id BIGINT,
  account_id BIGINT,
  lead_id BIGINT,
  opportunity_id BIGINT,
  customer_id BIGINT,
  status TEXT NOT NULL DEFAULT 'open',        -- open | pending_customer | pending_internal | snoozed | resolved
  priority TEXT NOT NULL DEFAULT 'normal',
  active_mode TEXT NOT NULL DEFAULT 'team_queue', -- human_assigned | team_queue | agent_autopilot | agent_copilot | awaiting_decision
  owner_member_id BIGINT,
  snoozed_until TIMESTAMPTZ,
  correlation_id TEXT NOT NULL,
  tier TEXT NOT NULL DEFAULT 'standard',      -- standard | priority | vip (resolve tại openThread)
  sla_policy_version INTEGER,
  sla_snapshot JSONB,                         -- snapshot policy tier tại thời điểm mở; ticket đang mở giữ snapshot cũ trừ khi rebaseline có audit
  first_response_due_at TIMESTAMPTZ,
  resolution_due_at TIMESTAMPTZ,
  escalation_level INTEGER NOT NULL DEFAULT 0,
  escalation_route_key TEXT,
  last_customer_msg_at TIMESTAMPTZ,
  first_response_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (inbox_id, workspace_id)
    REFERENCES engagement.engagement_inboxes(id, workspace_id) ON DELETE CASCADE
);
ALTER TABLE engagement.engagement_threads ADD CONSTRAINT uq_engagement_threads_id_ws UNIQUE (id, workspace_id);
CREATE INDEX idx_engagement_threads_workspace ON engagement.engagement_threads(workspace_id);
CREATE INDEX idx_engagement_threads_queue ON engagement.engagement_threads(workspace_id, status, priority);
CREATE INDEX idx_engagement_threads_owner ON engagement.engagement_threads(workspace_id, owner_member_id);

CREATE TABLE engagement.engagement_messages (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  direction TEXT NOT NULL,                    -- inbound | outbound | system
  visibility TEXT NOT NULL,                   -- customer | internal
  sender_kind TEXT NOT NULL,                  -- customer | workforce_member | automation | system
  sender_ref TEXT,
  body TEXT NOT NULL,
  body_content_hash TEXT NOT NULL,
  classification TEXT NOT NULL DEFAULT 'confidential',
  retention_until TIMESTAMPTZ NOT NULL,       -- fail-closed: KHÔNG nullable, KHÔNG "giữ vô thời hạn" (mặc định created_at + 365d)
  delivery_state TEXT,                        -- null cho inbound/internal; queued|sent|delivered|failed|cancelled cho outbound+customer
  idempotency_key TEXT NOT NULL,
  external_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_engagement_messages_thread_idem
  ON engagement.engagement_messages(thread_id, idempotency_key);
CREATE INDEX idx_engagement_messages_thread ON engagement.engagement_messages(thread_id, created_at);
-- dedupe inbound theo provider message id (P2), nullable nên partial unique:
CREATE UNIQUE INDEX uq_engagement_messages_external
  ON engagement.engagement_messages(workspace_id, external_message_id)
  WHERE external_message_id IS NOT NULL;
-- composite target cần unique key:
ALTER TABLE engagement.engagement_messages ADD CONSTRAINT uq_engagement_messages_id_ws UNIQUE (id, workspace_id);

CREATE TABLE engagement.engagement_assignments (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  assigned_team_id BIGINT,
  assigned_member_id BIGINT,
  assigned_agent_spec_id TEXT,
  reason TEXT NOT NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
-- tối đa 1 assignment active / thread:
CREATE UNIQUE INDEX uq_engagement_assignments_active
  ON engagement.engagement_assignments(thread_id) WHERE ended_at IS NULL;

CREATE TABLE engagement.engagement_thread_labels (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  label_key TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  source TEXT NOT NULL,                       -- human | automation | agent_proposal
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_engagement_thread_labels
  ON engagement.engagement_thread_labels(thread_id, label_key);

CREATE TABLE engagement.engagement_thread_outcomes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  intent TEXT,
  resolution_code TEXT,
  escalation_reason TEXT,
  csat_ref TEXT,
  sales_signal_evidence JSONB,
  decision_request_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_thread_outcomes_thread ON engagement.engagement_thread_outcomes(thread_id);

CREATE TABLE engagement.engagement_customer_interactions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  contact_id BIGINT,
  account_id BIGINT,
  lead_id BIGINT,
  opportunity_id BIGINT,
  customer_id BIGINT,
  thread_id BIGINT,
  summary TEXT NOT NULL,
  source_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  confidence TEXT NOT NULL DEFAULT 'medium',
  retention_until TIMESTAMPTZ NOT NULL,       -- fail-closed (mặc định created_at + 365d)
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_cust_interactions_contact
  ON engagement.engagement_customer_interactions(workspace_id, contact_id);

CREATE TABLE engagement.engagement_thread_transitions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  actor JSONB NOT NULL,                       -- { kind, id }
  reason_code TEXT NOT NULL,
  previous_state TEXT,
  current_state TEXT NOT NULL,
  previous_mode TEXT,
  current_mode TEXT,
  correlation_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_thread_transitions_thread
  ON engagement.engagement_thread_transitions(thread_id, created_at);

-- Authority = capability được bind rõ tới WorkforceMember trong TỪNG workspace.
-- KHÔNG suy quyền từ role_title / "admin" / "founder". Seed ở trạng thái pending_binding;
-- chỉ 'enabled' sau khi mọi capability trong approval_policy.required_capabilities có >=1 grant active.
CREATE TABLE engagement.engagement_decision_authorities (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  authority_key TEXT NOT NULL,                -- vd. commercial.discount.up_to_10_pct, billing.refund_or_credit
  decision_kind TEXT NOT NULL,               -- discount | pricing_exception | pricing_high_risk | refund_or_credit | cancellation_exception | contract_commercial | contract_legal_privacy
  match_criteria JSONB NOT NULL DEFAULT '{}'::jsonb,   -- điều kiện định lượng: {max_discount_pct, below_price_floor, payment_term_nonstandard, ...}
  approval_policy JSONB NOT NULL,             -- {required_capabilities:[...], distinct_approvers:N, requester_must_differ:true, requester_cannot_execute:true}
  version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'pending_binding',   -- pending_binding | enabled | disabled
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_decision_authorities
  ON engagement.engagement_decision_authorities(workspace_id, authority_key, version);

-- Grant: capability cụ thể của authority được gán cho một WorkforceMember thật, có hiệu lực thời gian.
CREATE TABLE engagement.engagement_decision_authority_grants (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  authority_key TEXT NOT NULL,
  workforce_member_id BIGINT NOT NULL,
  capability TEXT NOT NULL,                   -- vd. sales_manager, finance_controller, legal_reviewer, workspace_business_owner
  active_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  active_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_authority_grants_lookup
  ON engagement.engagement_decision_authority_grants(workspace_id, authority_key, capability);

CREATE TABLE engagement.engagement_decision_requests (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT,
  request_type TEXT NOT NULL,                 -- = decision_kind
  status TEXT NOT NULL DEFAULT 'draft',       -- draft|submitted|under_review|needs_information|approved|execution_pending|executed|rejected|expired
  contact_id BIGINT, account_id BIGINT, lead_id BIGINT, opportunity_id BIGINT, customer_id BIGINT,
  policy_id TEXT, policy_version TEXT, policy_snapshot_ref TEXT,
  facts_ref TEXT,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  options JSONB NOT NULL DEFAULT '[]'::jsonb,
  recommendation_ref TEXT,
  requested_by_actor JSONB NOT NULL,
  requested_by_workforce_member_id BIGINT NOT NULL,   -- để enforce requester != approver != executor
  authority_key TEXT NOT NULL,
  authority_version INTEGER NOT NULL,
  approval_policy_snapshot JSONB NOT NULL,    -- copy approval_policy tại lúc submit
  approval_deadline TIMESTAMPTZ,
  decision TEXT,                              -- approved | rejected | needs_information (kết luận cuối)
  decision_reason TEXT,
  approved_at TIMESTAMPTZ,                    -- thời điểm approval_policy được thoả
  executed_by_workforce_member_id BIGINT,
  execution_ref TEXT,
  correlation_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_decision_requests_ws_status
  ON engagement.engagement_decision_requests(workspace_id, status);
CREATE INDEX idx_engagement_decision_requests_thread
  ON engagement.engagement_decision_requests(thread_id);

-- Mỗi phê duyệt của một người = 1 dòng. N-of-M distinct approvers suy ra từ đây, không phải 2 cột cứng.
CREATE TABLE engagement.engagement_decision_request_approvals (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  decision_request_id BIGINT NOT NULL,
  workforce_member_id BIGINT NOT NULL,
  capability TEXT NOT NULL,                   -- capability mà người này cover (từ grant)
  decision TEXT NOT NULL,                     -- approve | reject | needs_information
  reason TEXT,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_dr_approvals_distinct
  ON engagement.engagement_decision_request_approvals(decision_request_id, workforce_member_id);

CREATE TABLE engagement.engagement_decision_request_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  decision_request_id BIGINT NOT NULL,
  event_type TEXT NOT NULL,                   -- submitted|review_started|approval_recorded|needs_information|approved|rejected|expired|execution_started|executed|execution_failed
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  actor JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_dr_events_dr
  ON engagement.engagement_decision_request_events(decision_request_id, created_at);

-- Escalation route: primary / backup / duty_manager bind tới WorkforceMember thật, theo hiệu lực.
-- KHÔNG hard-code email / cá nhân trong sla_policy JSON.
CREATE TABLE engagement.engagement_escalation_routes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  route_key TEXT NOT NULL,                    -- vd. support-oncall
  role TEXT NOT NULL,                         -- primary | backup | duty_manager
  workforce_member_id BIGINT NOT NULL,
  active_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  active_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_escalation_routes_lookup
  ON engagement.engagement_escalation_routes(workspace_id, route_key, role);

-- Legal hold: record riêng, có lý do + người tạo + hạn. Chặn xoá; KHÔNG âm thầm kéo dài retention.
CREATE TABLE engagement.engagement_legal_holds (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  scope TEXT NOT NULL,                        -- thread | contact | workspace
  scope_ref BIGINT,                           -- thread_id / contact_id; null khi scope=workspace
  reason TEXT NOT NULL,
  created_by_workforce_member_id BIGINT NOT NULL,
  effective_until TIMESTAMPTZ NOT NULL,
  released_at TIMESTAMPTZ,
  released_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_legal_holds_scope
  ON engagement.engagement_legal_holds(workspace_id, scope, scope_ref);

-- Data Subject Request (GDPR Art.5 / NĐ 13/2023/NĐ-CP): export | delete.
CREATE TABLE engagement.engagement_data_subject_requests (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  kind TEXT NOT NULL,                         -- export | delete
  subject_contact_id BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'received',    -- received | verified | suppressed | exported | purging | completed | blocked_legal_hold | rejected
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  verified_at TIMESTAMPTZ,
  verified_by_workforce_member_id BIGINT,     -- Privacy Officer
  export_ref TEXT,
  export_expires_at TIMESTAMPTZ,              -- tải trong 24h
  suppressed_at TIMESTAMPTZ,                  -- khoá truy cập ngay sau tiếp nhận (delete)
  primary_purge_due_at TIMESTAMPTZ,          -- <= verified_at + 30 ngày
  backup_purge_due_at TIMESTAMPTZ,           -- <= 35 ngày
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_dsr_ws_status
  ON engagement.engagement_data_subject_requests(workspace_id, status);

-- Attachment (metadata P0; raw byte store = P2). retention_until NOT NULL (mặc định +90d cho raw, +730d cho metadata-only row).
CREATE TABLE engagement.engagement_message_attachments (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  filename TEXT NOT NULL,
  content_type TEXT,
  byte_size BIGINT,
  content_ref TEXT,                           -- reference tới object store tại workspace_home_region; null nếu chưa upload
  content_hash TEXT,
  retention_until TIMESTAMPTZ NOT NULL,       -- fail-closed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (message_id, workspace_id)
    REFERENCES engagement.engagement_messages(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_message_attachments_msg
  ON engagement.engagement_message_attachments(message_id);

CREATE TABLE engagement.engagement_outbound_deliveries (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  channel_type TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',      -- queued | sent | delivered | failed
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 8,
  claim_token TEXT,
  visibility_timeout_at TIMESTAMPTZ,
  last_error TEXT,
  dead_letter_reason TEXT,
  external_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  FOREIGN KEY (message_id, workspace_id)
    REFERENCES engagement.engagement_messages(id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_engagement_outbound_deliveries_idem
  ON engagement.engagement_outbound_deliveries(workspace_id, idempotency_key);
CREATE INDEX idx_engagement_outbound_deliveries_due
  ON engagement.engagement_outbound_deliveries(status, visibility_timeout_at);

CREATE TABLE engagement.engagement_identity_review_items (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  candidate_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  reason TEXT NOT NULL,                       -- multiple_candidates | unverified | do_not_contact | account_conflict
  status TEXT NOT NULL DEFAULT 'open',        -- open | resolved | dismissed
  resolved_by_workforce_member_id BIGINT,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_identity_review_items_thread
  ON engagement.engagement_identity_review_items(thread_id);
