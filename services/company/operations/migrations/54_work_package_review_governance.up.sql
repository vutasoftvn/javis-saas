-- 54_work_package_review_governance.up.sql
--
-- Review bất biến của manager/founder + priority override event + task-level
-- outcome review + KR contribution verification append-only (spec §7-8, §12).
-- Không auto-accept: chỉ review của người mới tạo outcome nghiệp vụ.
-- Expand-only.

CREATE TABLE operating.work_package_reviews (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  work_package_id       BIGINT NOT NULL REFERENCES operating.task_work_packages(id) ON DELETE CASCADE,
  work_attempt_id       BIGINT REFERENCES operating.work_package_attempts(id) ON DELETE SET NULL,
  reviewer_member_id    BIGINT,
  reviewer_kind         VARCHAR(16) NOT NULL DEFAULT 'manager', -- manager | founder
  artifact_version_ref  TEXT NOT NULL,
  decision              VARCHAR(16) NOT NULL CHECK (decision IN ('ACCEPT', 'REWORK', 'REJECT')),
  rubric_scores         JSONB NOT NULL DEFAULT '{}'::jsonb,
  reason_code           TEXT NOT NULL,
  narrative             TEXT,
  supersedes_review_id  BIGINT REFERENCES operating.work_package_reviews(id) ON DELETE SET NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_work_package_reviews_wp
  ON operating.work_package_reviews (work_package_id, created_at);

CREATE TABLE operating.task_outcome_reviews (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  task_result_id        BIGINT NOT NULL REFERENCES operating.task_results(id) ON DELETE CASCADE,
  assessment_id         BIGINT REFERENCES operating.outcome_assessments(id) ON DELETE SET NULL,
  expected_result_revision INTEGER NOT NULL,
  reviewer_member_id    BIGINT,
  decision              VARCHAR(16) NOT NULL CHECK (decision IN ('ACCEPT', 'REWORK', 'REJECT')),
  reason_code           TEXT NOT NULL,
  narrative             TEXT,
  supersedes_review_id  BIGINT REFERENCES operating.task_outcome_reviews(id) ON DELETE SET NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_task_outcome_reviews_result
  ON operating.task_outcome_reviews (task_result_id, created_at);

-- Priority override chỉ tạo event bất biến; không ghi đè requested_priority.
CREATE TABLE operating.work_package_priority_events (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  work_package_id       BIGINT NOT NULL REFERENCES operating.task_work_packages(id) ON DELETE CASCADE,
  actor_member_id       BIGINT,
  requested_priority    VARCHAR(4) NOT NULL,
  prior_effective_priority VARCHAR(4) NOT NULL,
  new_effective_priority   VARCHAR(4) NOT NULL,
  reason                TEXT NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_work_package_priority_events_wp
  ON operating.work_package_priority_events (work_package_id, created_at);
