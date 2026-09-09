-- 52_ai_work_packages.up.sql
--
-- Work package + attempt + event là business truth của queue AI (spec §7).
-- Company IDs là Snowflake BIGINT; tham chiếu Agent Platform là opaque TEXT.
-- Expand-only.

CREATE TABLE operating.task_work_packages (
  id                          BIGINT PRIMARY KEY,
  workspace_id                BIGINT NOT NULL,
  task_id                     BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
  outcome_contract_id         BIGINT NOT NULL REFERENCES operating.task_outcome_contracts(id),
  title                       TEXT,
  objective                   TEXT NOT NULL,
  input_refs                  JSONB NOT NULL DEFAULT '[]'::jsonb,
  output_contract             JSONB NOT NULL DEFAULT '{}'::jsonb,
  acceptance_rubric           JSONB NOT NULL DEFAULT '{}'::jsonb,
  requested_by_manager_id     BIGINT,
  assigned_agent_instance_id  TEXT NOT NULL,
  requested_priority          VARCHAR(4) NOT NULL CHECK (requested_priority IN ('P0','P1','P2','P3')),
  effective_priority          VARCHAR(4) NOT NULL CHECK (effective_priority IN ('P0','P1','P2','P3')),
  priority_reason             TEXT,
  status                      VARCHAR(30) NOT NULL DEFAULT 'QUEUED'
                                CHECK (status IN (
                                  'QUEUED','LEASED','RUNNING','VALIDATION_PASSED',
                                  'PENDING_MANAGER_REVIEW','ESCALATED_TO_FOUNDER',
                                  'ACCEPTED','REWORK','REJECTED','BLOCKED','ON_HOLD','CANCELLED'
                                )),
  dependency_ids              JSONB NOT NULL DEFAULT '[]'::jsonb,
  review_due_at               TIMESTAMPTZ,
  budget_limit                NUMERIC,
  idempotency_key             TEXT,
  version                     INTEGER NOT NULL DEFAULT 1,
  queued_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
  due_at                      TIMESTAMPTZ,
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uix_task_work_packages_idem
  ON operating.task_work_packages (workspace_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX ix_task_work_packages_queue
  ON operating.task_work_packages (workspace_id, status, effective_priority, due_at, queued_at);

CREATE INDEX ix_task_work_packages_task
  ON operating.task_work_packages (workspace_id, task_id);

CREATE TABLE operating.work_package_attempts (
  id                          BIGINT PRIMARY KEY,
  workspace_id                BIGINT NOT NULL,
  work_package_id             BIGINT NOT NULL REFERENCES operating.task_work_packages(id) ON DELETE CASCADE,
  sequence_no                 INTEGER NOT NULL,
  assigned_agent_instance_id  TEXT NOT NULL,
  assignment_snapshot         JSONB,
  spec_snapshot               JSONB,
  run_id                      TEXT,
  status                      VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
  started_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at                    TIMESTAMPTZ,
  ended_reason                TEXT
);

CREATE UNIQUE INDEX uix_work_package_attempts_seq
  ON operating.work_package_attempts (work_package_id, sequence_no);

-- Không có hai active attempt cho cùng một package (spec §7).
CREATE UNIQUE INDEX uix_work_package_attempts_active
  ON operating.work_package_attempts (work_package_id)
  WHERE ended_at IS NULL;

CREATE TABLE operating.work_package_events (
  id              BIGINT PRIMARY KEY,
  workspace_id    BIGINT NOT NULL,
  work_package_id BIGINT NOT NULL REFERENCES operating.task_work_packages(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL,
  actor_kind      TEXT NOT NULL,
  actor_id        TEXT,
  before_json     JSONB,
  after_json      JSONB,
  reason          TEXT,
  correlation_id  TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_work_package_events_wp
  ON operating.work_package_events (work_package_id, created_at);
