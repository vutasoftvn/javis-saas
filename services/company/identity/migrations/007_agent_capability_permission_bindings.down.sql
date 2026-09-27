-- Rollback for 007_agent_capability_permission_bindings.up.sql (grant liên quan bị xoá theo FK CASCADE).
DELETE FROM core.capability_permission_bindings WHERE capability_id IN (
  'operations.task.create_draft', 'operations.task.advance', 'okr.key_result.create',
  'okr.key_result.checkin', 'startup_os.goal.create', 'startup_os.project.triage',
  'startup_os.onboard.session_start', 'startup_os.onboard.dimension_update',
  'startup_os.onboard.snapshot_create', 'strategy.evidence.create', 'strategy.pilot.create_draft',
  'venture.profile.propose_update', 'legal.obligation.create_draft',
  'finance.transaction.classify_propose', 'finance.accounting_document.create_draft',
  'finance.transaction.record'
);
DELETE FROM core.permission_definitions WHERE permission_key = 'operations.task.write';
