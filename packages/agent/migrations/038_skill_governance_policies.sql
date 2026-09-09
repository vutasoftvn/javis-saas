-- Migration 038: Founder-controlled analysis policy + Skill Governance
-- lifecycle (Task 7A, spec §10).
--
-- Append-only policy draft / policy version / policy event / skill-governance
-- proposal. Mỗi policy version ghi analysis policy, task scope/depth/SLA/budget
-- rules, exact analyst employee + assignment, pinned skill ref, effective
-- timestamp, creator, approver, rollback target. Capability allowlist snapshot
-- reject bất kỳ capability ngoài 6-item Outcome Analyst boundary.
-- Expand-only + có down.

CREATE TABLE IF NOT EXISTS agent.outcome_analysis_policy_drafts (
    draft_id            UUID PRIMARY KEY,
    workspace_id        TEXT NOT NULL,
    analysis_kind       TEXT NOT NULL DEFAULT 'TASK_OUTCOME',
    policy              TEXT NOT NULL CHECK (policy IN ('AUTO_ALL_TASKS','AUTO_BY_RULE','MANUAL')),
    analyst_employee_id UUID NOT NULL,
    analyst_assignment_id UUID NOT NULL,
    skill_id            TEXT NOT NULL,
    skill_version       TEXT NOT NULL,
    definition_hash     TEXT NOT NULL,
    capability_allowlist JSONB NOT NULL DEFAULT '[]'::jsonb,
    depth_rules         JSONB NOT NULL DEFAULT '{}'::jsonb,
    status              TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','PUBLISHED','SUPERSEDED')),
    version             INTEGER NOT NULL DEFAULT 1,
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outcome_analysis_policy_drafts_ws
    ON agent.outcome_analysis_policy_drafts (workspace_id, analysis_kind, status);

CREATE TABLE IF NOT EXISTS agent.outcome_analysis_policy_versions (
    policy_version_id  UUID PRIMARY KEY,
    workspace_id       TEXT NOT NULL,
    analysis_kind      TEXT NOT NULL,
    version_no         INTEGER NOT NULL,
    policy             TEXT NOT NULL,
    analyst_employee_id UUID NOT NULL,
    analyst_assignment_id UUID NOT NULL,
    skill_id           TEXT NOT NULL,
    skill_version      TEXT NOT NULL,
    definition_hash    TEXT NOT NULL,
    capability_allowlist JSONB NOT NULL DEFAULT '[]'::jsonb,
    depth_rules        JSONB NOT NULL DEFAULT '{}'::jsonb,
    effective_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by         TEXT NOT NULL,
    approved_by        TEXT NOT NULL,
    rollback_target_version_id UUID NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, analysis_kind, version_no)
);

CREATE TABLE IF NOT EXISTS agent.outcome_analysis_policy_events (
    event_id       UUID PRIMARY KEY,
    workspace_id   TEXT NOT NULL,
    analysis_kind  TEXT NOT NULL,
    event_type     TEXT NOT NULL,   -- draft_created | published | rolled_back
    actor_id       TEXT NOT NULL,
    payload        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
