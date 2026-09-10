-- Fix gaps in 001_founder_trial_mvp_baseline (a pg_dump --schema-only squash
-- that lost several objects the running code still depends on):
--
--  1. core.workspace_policy_versions + core.business_policy_cutover_markers were
--     dropped, but services/company/identity's tenant-context / business-policy
--     resolver queries workspace_policy_versions on every /operations/* request.
--  2. integration.event_outbox.id and integration.event_audit.id lost their
--     `GENERATED ALWAYS AS IDENTITY` clause (pg_dump splits it into a separate
--     ALTER that the squash filtered out). The Drizzle schema declares
--     `.generatedAlwaysAsIdentity()`, so INSERTs omit `id` and the DB must fill
--     it — without identity they fail the NOT NULL constraint.
--
-- Expand-only, idempotent.

CREATE TABLE IF NOT EXISTS core.workspace_policy_versions (
  workspace_id      BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  version           INTEGER NOT NULL,
  policy_hash       TEXT NOT NULL,
  actor_member_id   BIGINT,
  reason            TEXT,
  source            TEXT NOT NULL DEFAULT 'native',
  cutover_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, version)
);

CREATE TABLE IF NOT EXISTS core.business_policy_cutover_markers (
  workspace_id          BIGINT PRIMARY KEY REFERENCES core.workspaces(id) ON DELETE CASCADE,
  cutover_completed     BOOLEAN NOT NULL DEFAULT false,
  cutover_at            TIMESTAMPTZ,
  migrated_rule_count   INTEGER NOT NULL DEFAULT 0,
  needs_review_count    INTEGER NOT NULL DEFAULT 0,
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Re-attach the identity clause only where it is missing (attidentity = '' means
-- not an identity column). Safe on a fresh baseline DB (no rows) and a no-op on
-- a DB migrated the pre-squash way (already identity).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'integration' AND c.relname = 'event_outbox'
      AND a.attname = 'id' AND a.attidentity = '' AND NOT a.atthasdef
  ) THEN
    EXECUTE 'ALTER TABLE integration.event_outbox ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'integration' AND c.relname = 'event_audit'
      AND a.attname = 'id' AND a.attidentity = '' AND NOT a.atthasdef
  ) THEN
    EXECUTE 'ALTER TABLE integration.event_audit ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY';
  END IF;
END $$;
