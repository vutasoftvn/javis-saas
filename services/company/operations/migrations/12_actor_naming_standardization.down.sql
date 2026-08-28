-- Rollback 12_actor_naming_standardization.up.sql
ALTER TABLE strategy.decision_records RENAME COLUMN actor_member_id TO actor_workforce_member_id;
ALTER TABLE strategy.experiments RENAME COLUMN owner_member_id TO owner_workforce_member_id;
ALTER TABLE strategy.projects RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE strategy.okr_objectives RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE strategy.initiatives RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE operating.tasks ADD COLUMN IF NOT EXISTS assignee_id BIGINT;
