-- 51_task_outcome_contracts.up.sql
--
-- Outcome Contract bắt buộc theo task (spec §6). Mỗi task có tối đa một
-- contract CONFIRMED đang hiệu lực; revision mới được APPEND, không update
-- in-place field đã CONFIRMED. DRAFT chỉ dành cho AI proposal / input thiếu.
--
-- Expand-only (Encore guardrail #4): bảng mới + cột nullable + index. KHÔNG
-- backfill contract giả cho task lịch sử — UI đánh dấu cần remediation.

CREATE TABLE operating.task_outcome_contracts (
  id                            BIGINT PRIMARY KEY,
  workspace_id                  BIGINT NOT NULL,
  task_id                       BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
  revision                      INTEGER NOT NULL DEFAULT 1,
  status                        VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
                                  CHECK (status IN ('DRAFT', 'CONFIRMED', 'SUPERSEDED')),
  outcome_type                  VARCHAR(20) NOT NULL
                                  CHECK (outcome_type IN ('DIRECT_KR', 'ENABLING_KR', 'VALIDATION', 'BAU')),
  expected_outcome              TEXT NOT NULL,
  acceptance_criteria           JSONB NOT NULL DEFAULT '{}'::jsonb,
  expected_evidence_refs        JSONB NOT NULL DEFAULT '[]'::jsonb,
  measurement_plan              JSONB,
  impact_hypothesis             TEXT NOT NULL,
  service_objective             TEXT,
  primary_kr_id                 BIGINT REFERENCES strategy.key_results(id) ON DELETE SET NULL,
  initiative_id                 BIGINT REFERENCES strategy.initiatives(id) ON DELETE SET NULL,
  proposed_by_agent_instance_id TEXT,
  created_by_member_id          BIGINT,
  confirmed_by_member_id        BIGINT,
  confirmed_at                  TIMESTAMPTZ,
  supersedes_contract_id        BIGINT REFERENCES operating.task_outcome_contracts(id) ON DELETE SET NULL,
  change_reason                 TEXT,
  version                       INTEGER NOT NULL DEFAULT 1,
  created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uix_task_outcome_contracts_task_revision
  ON operating.task_outcome_contracts (task_id, revision);

CREATE INDEX ix_task_outcome_contracts_ws_task
  ON operating.task_outcome_contracts (workspace_id, task_id, status);

-- Tối đa một contract CONFIRMED "đang hiệu lực" cho mỗi task.
CREATE UNIQUE INDEX uix_task_outcome_contracts_active_confirmed
  ON operating.task_outcome_contracts (task_id)
  WHERE status = 'CONFIRMED';

CREATE TABLE operating.task_outcome_kr_links (
  id            BIGINT PRIMARY KEY,
  workspace_id  BIGINT NOT NULL,
  contract_id   BIGINT NOT NULL REFERENCES operating.task_outcome_contracts(id) ON DELETE CASCADE,
  key_result_id BIGINT NOT NULL REFERENCES strategy.key_results(id) ON DELETE CASCADE,
  relation_type VARCHAR(20) NOT NULL
                  CHECK (relation_type IN ('DIRECT', 'ENABLING', 'VALIDATION')),
  is_primary    BOOLEAN NOT NULL DEFAULT false,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Đúng một primary KR cho mỗi contract (partial unique index).
CREATE UNIQUE INDEX uix_task_outcome_kr_links_primary
  ON operating.task_outcome_kr_links (contract_id)
  WHERE is_primary = true;

CREATE UNIQUE INDEX uix_task_outcome_kr_links_contract_kr
  ON operating.task_outcome_kr_links (contract_id, key_result_id);

-- Con trỏ tới contract đang hiệu lực; NULL cho task lịch sử chưa remediate.
ALTER TABLE operating.tasks
  ADD COLUMN active_outcome_contract_id BIGINT
    REFERENCES operating.task_outcome_contracts(id) ON DELETE SET NULL;
