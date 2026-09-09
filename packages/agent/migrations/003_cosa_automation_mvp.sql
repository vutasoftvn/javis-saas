-- COSA Automation MVP (Task 1) — Agent Platform side.
-- docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
--
-- 1. agent.automation_run_manifests: the immutable, hash-verified execution
--    manifest pinned before a curated automation run enters RUNNING. Insert-once
--    per run_id; resume/reclaim reloads it by run_id and compares manifest_hash.
-- 2. agent.approvals.manifest_hash: bind an approval to the exact manifest that
--    was in force (Task 6 governance — approval valid only for
--    (run_id, tool_call_id, checkpoint_ref, manifest_hash)). Nullable/expand-only;
--    existing rows keep NULL, new automation approvals populate it.
--
-- agent.* schema DML is granted to agent_app by scripts/migrate.py's
-- _grant_application_access helper (it only skips `public`).

CREATE TABLE IF NOT EXISTS agent.automation_run_manifests (
  run_id        TEXT PRIMARY KEY REFERENCES agent.runs(run_id) ON DELETE CASCADE,
  manifest_hash TEXT NOT NULL,
  manifest_json JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_automation_run_manifests_hash
  ON agent.automation_run_manifests (manifest_hash);

ALTER TABLE agent.approvals
  ADD COLUMN IF NOT EXISTS manifest_hash TEXT;
