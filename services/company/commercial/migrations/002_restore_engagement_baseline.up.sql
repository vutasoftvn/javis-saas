-- 002_restore_engagement_baseline.up.sql
--
-- Startup Core Task-2 reconciliation: the clean-slate 001 commercial baseline
-- omitted the entire `engagement` subsystem (customer support Human Desk +
-- copilot + channels + automation + autopilot), but the Drizzle schema
-- (shared/db/schema/customer-engagement.ts), services and handlers still use it.
-- This restores it by replaying, in original order, the five pre-clean-slate
-- migrations deleted in 81461673 (11_customer_engagement .. 15_engagement_autopilot).
-- Expand-only; no framework (BSC/PESTEL/SWOT/TOWS) coupling.

-- ============================================================================
-- from 11_customer_engagement.up.sql
-- ============================================================================
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

-- ============================================================================
-- from 12_engagement_copilot.up.sql
-- ============================================================================
-- P1: Customer Support Copilot — enablement per workspace (fail-closed) + audit invocation.
CREATE TABLE engagement.engagement_copilot_settings (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT false,          -- fail-closed
  allowed_intents JSONB NOT NULL DEFAULT '["summarize","draft_reply","extract_facts","sales_signal"]'::jsonb,
  knowledge_scope JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {profile_types:[...], include_untrusted:false}
  allowed_agent_spec_id TEXT,                      -- pin: phải set trước khi enable
  allowed_agent_spec_version TEXT,
  allowed_agent_spec_hash TEXT,
  eval_evidence_ref TEXT,                          -- ref eval evidence tươi; bắt buộc để enable
  eval_evidence_hash TEXT,                         -- hash spec mà evidence chứng nhận
  updated_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_copilot_settings_ws
  ON engagement.engagement_copilot_settings(workspace_id);

CREATE TABLE engagement.engagement_copilot_invocations (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  requested_by_workforce_member_id BIGINT NOT NULL,
  intent TEXT NOT NULL,
  run_id TEXT NOT NULL,
  agent_spec_id TEXT NOT NULL,
  agent_spec_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'dispatched',       -- dispatched | running | completed | failed | cancelled
  artifact_ref TEXT,                               -- ref artifact draft/summary khi completed
  summary_ref TEXT,
  identity_verified BOOLEAN NOT NULL DEFAULT false,
  feedback TEXT,                                   -- accepted | edited | rejected
  feedback_edited_ref TEXT,                        -- ref bản người sửa (nếu edited)
  feedback_by_workforce_member_id BIGINT,
  feedback_at TIMESTAMPTZ,
  correlation_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_copilot_invocations_thread
  ON engagement.engagement_copilot_invocations(thread_id, created_at);
CREATE UNIQUE INDEX uq_engagement_copilot_invocations_run
  ON engagement.engagement_copilot_invocations(workspace_id, run_id);

-- ============================================================================
-- from 13_engagement_channels.up.sql
-- ============================================================================
-- P2: kênh khách hàng thật — dedupe raw + routing + connector.
ALTER TABLE engagement.engagement_channel_endpoints
  ADD COLUMN IF NOT EXISTS connector_key TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS inbound_routing_key TEXT,
  ADD COLUMN IF NOT EXISTS auto_create_contact BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS skew_seconds INTEGER NOT NULL DEFAULT 300;

CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_channel_endpoints_routing
  ON engagement.engagement_channel_endpoints(workspace_id, inbound_routing_key)
  WHERE inbound_routing_key IS NOT NULL;

ALTER TABLE engagement.engagement_threads
  ADD COLUMN IF NOT EXISTS external_conversation_ref TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_threads_external_conv
  ON engagement.engagement_threads(inbox_id, external_conversation_ref)
  WHERE external_conversation_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS engagement.engagement_channel_inbound_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  endpoint_id BIGINT NOT NULL,
  provider_delivery_id TEXT NOT NULL,
  provider_message_id TEXT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome TEXT NOT NULL DEFAULT 'accepted',
  thread_id BIGINT,
  message_id BIGINT,
  error TEXT,
  raw_hash TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_engagement_channel_inbound_events_dedupe
  ON engagement.engagement_channel_inbound_events(endpoint_id, provider_delivery_id);

CREATE INDEX IF NOT EXISTS idx_engagement_channel_inbound_events_ep
  ON engagement.engagement_channel_inbound_events(endpoint_id, received_at);

-- ============================================================================
-- from 14_engagement_automation.up.sql
-- ============================================================================
-- P3: deterministic automation — rule typed/versioned + ledger idempotency + delayed schedule.
CREATE TABLE engagement.engagement_automation_rules (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,                      -- ổn định qua các version
  version INTEGER NOT NULL DEFAULT 1,
  name TEXT NOT NULL,
  trigger TEXT NOT NULL,                       -- thread_opened | message_received | thread_status_changed | csat_recorded | time_sweep
  priority INTEGER NOT NULL DEFAULT 100,       -- nhỏ chạy trước
  condition JSONB NOT NULL,                    -- predicate tree typed
  actions JSONB NOT NULL,                      -- array typed action
  enabled BOOLEAN NOT NULL DEFAULT false,      -- fail-closed: rule mới off cho tới khi bật
  stop_on_match BOOLEAN NOT NULL DEFAULT false,
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_until TIMESTAMPTZ,
  created_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_automation_rules_ver
  ON engagement.engagement_automation_rules(workspace_id, rule_key, version);
CREATE INDEX idx_engagement_automation_rules_trigger
  ON engagement.engagement_automation_rules(workspace_id, trigger, enabled, priority);

CREATE TABLE engagement.engagement_automation_applications (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  thread_id BIGINT NOT NULL,
  trigger TEXT NOT NULL,
  action_index INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  dedupe_key TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL,                       -- applied | skipped_condition_changed | skipped_ownership_changed | skipped_rule_disabled | skipped_no_authority | error
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_automation_applications
  ON engagement.engagement_automation_applications(rule_key, rule_version, thread_id, action_index, dedupe_key);
CREATE INDEX idx_engagement_automation_applications_thread
  ON engagement.engagement_automation_applications(thread_id, created_at);

CREATE TABLE engagement.engagement_automation_schedules (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  thread_id BIGINT NOT NULL,
  action_index INTEGER NOT NULL,
  action JSONB NOT NULL,                       -- snapshot action delayed
  condition JSONB NOT NULL,                    -- snapshot condition phải still-true khi đến hạn
  due_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',      -- pending | done | skipped | error
  skip_reason TEXT,
  claimed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_automation_schedules_due
  ON engagement.engagement_automation_schedules(status, due_at);

-- CSAT trên outcome
ALTER TABLE engagement.engagement_thread_outcomes
  ADD COLUMN IF NOT EXISTS csat_score INTEGER,
  ADD COLUMN IF NOT EXISTS csat_recorded_at TIMESTAMPTZ;

-- ============================================================================
-- from 15_engagement_autopilot.up.sql
-- ============================================================================
-- Migration 15: Customer Engagement P4 Autopilot Feature Flag & Settings

CREATE TABLE IF NOT EXISTS engagement.engagement_autopilot_settings (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL UNIQUE,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  env_allowlist JSONB NOT NULL DEFAULT '["test", "staging"]'::jsonb,
  trigger_rule_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  containment_min NUMERIC(5, 4) NOT NULL DEFAULT 0.8000,
  error_max NUMERIC(5, 4) NOT NULL DEFAULT 0.0500,
  takeover_max NUMERIC(5, 4) NOT NULL DEFAULT 0.1500,
  updated_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS engagement.engagement_autopilot_templates (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  template_key TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  body_hash TEXT NOT NULL,
  body TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_engagement_autopilot_template UNIQUE (workspace_id, template_key, version)
);

CREATE TABLE IF NOT EXISTS engagement.engagement_autopilot_runs (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  run_id TEXT NOT NULL UNIQUE,
  trigger_rule_id TEXT NOT NULL,
  thread_id BIGINT NOT NULL,
  outcome TEXT NOT NULL DEFAULT 'completed',
  handed_off BOOLEAN NOT NULL DEFAULT FALSE,
  approval_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_engagement_autopilot_runs_ws_created
  ON engagement.engagement_autopilot_runs (workspace_id, created_at DESC);

