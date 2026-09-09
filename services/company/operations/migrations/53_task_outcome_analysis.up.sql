-- 53_task_outcome_analysis.up.sql
--
-- Task Result (append-only revision), Outcome Analysis Request (idempotent),
-- Outcome Assessment (narrow-record), KR Contribution Assessment (spec §8).
-- KHÔNG cột nào cho phép cập nhật KR.actualValue. Expand-only.

CREATE TABLE operating.task_results (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  task_id               BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
  contract_id           BIGINT NOT NULL REFERENCES operating.task_outcome_contracts(id),
  result_revision       INTEGER NOT NULL,
  submitted_by_kind     VARCHAR(16) NOT NULL,   -- agent | human | system
  submitted_by_id       TEXT,
  work_attempt_ids      JSONB NOT NULL DEFAULT '[]'::jsonb,
  summary               TEXT NOT NULL,
  structured_outputs    JSONB NOT NULL DEFAULT '{}'::jsonb,
  artifact_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  claimed_measurements  JSONB NOT NULL DEFAULT '{}'::jsonb,
  blockers              JSONB NOT NULL DEFAULT '[]'::jsonb,
  idempotency_key       TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uix_task_results_task_revision
  ON operating.task_results (task_id, result_revision);
CREATE UNIQUE INDEX uix_task_results_idem
  ON operating.task_results (workspace_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE TABLE operating.outcome_analysis_requests (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  task_result_id        BIGINT NOT NULL REFERENCES operating.task_results(id) ON DELETE CASCADE,
  contract_id           BIGINT NOT NULL REFERENCES operating.task_outcome_contracts(id),
  contract_revision     INTEGER NOT NULL,
  analysis_kind         VARCHAR(32) NOT NULL,   -- TASK_OUTCOME | PROJECT_OUTCOME_SYNTHESIS
  analysis_policy       VARCHAR(20) NOT NULL,   -- AUTO_ALL_TASKS | AUTO_BY_RULE | MANUAL
  status                VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
                          -- QUEUED | RUNNING | READY | FAILED | BLOCKED_CONFIGURATION
  selected_agent_instance_id TEXT,
  selected_assignment_id     TEXT,
  selected_run_id            TEXT,
  skill_id              TEXT,
  skill_version         TEXT,
  definition_hash       TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uix_outcome_analysis_requests_idem
  ON operating.outcome_analysis_requests
     (workspace_id, task_result_id, analysis_kind, contract_revision);

CREATE TABLE operating.outcome_assessments (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  request_id            BIGINT NOT NULL REFERENCES operating.outcome_analysis_requests(id) ON DELETE CASCADE,
  task_result_id        BIGINT NOT NULL REFERENCES operating.task_results(id) ON DELETE CASCADE,
  contract_id           BIGINT NOT NULL REFERENCES operating.task_outcome_contracts(id),
  agent_instance_id     TEXT NOT NULL,
  assignment_id         TEXT NOT NULL,
  run_id                TEXT NOT NULL,
  skill_id              TEXT NOT NULL,
  skill_version         TEXT NOT NULL,
  definition_hash       TEXT NOT NULL,
  rubric_version        TEXT,
  evidence_used_refs    JSONB NOT NULL DEFAULT '[]'::jsonb,
  missing_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  expected_vs_actual    JSONB NOT NULL DEFAULT '{}'::jsonb,
  criterion_scores      JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidence            DOUBLE PRECISION,
  risk_flags            JSONB NOT NULL DEFAULT '[]'::jsonb,
  causal_limits         JSONB NOT NULL DEFAULT '[]'::jsonb,
  next_action_proposals JSONB NOT NULL DEFAULT '[]'::jsonb,
  recommendation        VARCHAR(24) NOT NULL,   -- ACCEPT | REWORK | REJECT | NEEDS_HUMAN_DECISION
  status                VARCHAR(16) NOT NULL DEFAULT 'READY', -- READY | FAILED | SUPERSEDED
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_outcome_assessments_result
  ON operating.outcome_assessments (task_result_id, status);

CREATE TABLE operating.kr_contribution_assessments (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  assessment_id         BIGINT NOT NULL REFERENCES operating.outcome_assessments(id) ON DELETE CASCADE,
  kr_link_id            BIGINT REFERENCES operating.task_outcome_kr_links(id) ON DELETE SET NULL,
  key_result_id         BIGINT REFERENCES strategy.key_results(id) ON DELETE SET NULL,
  state                 VARCHAR(24) NOT NULL DEFAULT 'PROPOSED',
                          -- PROPOSED | VERIFIED | REJECTED | INSUFFICIENT_EVIDENCE
  claimed_effect        JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  causal_confidence     DOUBLE PRECISION,
  verified_by_member_id BIGINT,
  verified_at           TIMESTAMPTZ,
  reason                TEXT,
  version               INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_kr_contribution_assessments_assessment
  ON operating.kr_contribution_assessments (assessment_id, state);
