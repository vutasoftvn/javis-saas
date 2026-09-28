-- 019_ai_initiative_promotion_snapshots.sql
--
-- Durable idempotency + authoritative-snapshot store for Company -> COSA AI
-- Initiative promotion delivery (Task 6, plan 2026-09-28-stage-adaptive-ai-
-- operating-system). Replaces the in-memory dict that previously backed
-- apps/cosa/api/ai_initiative_internal_routes.py: without this table, a
-- process restart forgets which promotion snapshots were already consumed
-- (breaking idempotent retry) and Task 8's execution policy gate has no
-- durable "current snapshot" to read after restart.

CREATE TABLE IF NOT EXISTS models.ai_initiative_promotion_snapshots (
  idempotency_key text PRIMARY KEY,
  workspace_id text NOT NULL,
  project_id text NOT NULL,
  initiative_id text NOT NULL,
  initiative_revision integer NOT NULL,
  decision_id text NOT NULL,
  decision_hash text NOT NULL,
  lifecycle_state text NOT NULL,
  risk_tier text NOT NULL,
  autonomy_tier text NOT NULL,
  pins jsonb NOT NULL DEFAULT '{}'::jsonb,
  value_contract_revision integer,
  data_readiness_revision integer,
  budget_policy_revision integer,
  evaluation_suite_revision integer,
  -- Task 11 — carried alongside data_readiness_revision so the knowledge
  -- readiness gate can decide NOT_READY/CONDITIONAL/READY + lexical/semantic
  -- without a cross-plane lookup into Company's data-readiness assessment table.
  data_readiness_status text,
  retrieval_mode text,
  consumed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_initiative_snapshots_ws_init_rev
  ON models.ai_initiative_promotion_snapshots (workspace_id, initiative_id, initiative_revision DESC);
