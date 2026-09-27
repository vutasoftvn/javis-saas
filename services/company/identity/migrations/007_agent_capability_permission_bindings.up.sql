-- 007_agent_capability_permission_bindings.up.sql
--
-- Spec 2026-09-27-chat-business-actions / ADR-CHAT-ACTIONS-001: capability ghi của agent
-- (T1/T2 trong apps/cosa/capabilities/access_matrix.py, có AGENT_CAP ở company) phải có binding
-- capability -> permission để company cấp được live authorization ticket. Trước đây chỉ có
-- operations.task.list ⇒ mọi hành động ghi của agent bị từ chối ở bước ticket.
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py.
-- Expand-only, idempotent.

INSERT INTO core.permission_definitions (permission_key, domain, description)
VALUES ('operations.task.write', 'operations', 'Tạo và cập nhật trạng thái nhiệm vụ')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO core.capability_permission_bindings (capability_id, permission_key, risk_class, version)
VALUES
  ('operations.task.create_draft',             'operations.task.write',      'INTERNAL_WRITE', 1),
  ('operations.task.advance',                  'operations.task.write',      'INTERNAL_WRITE', 1),
  ('okr.key_result.create',                    'strategy.write',             'INTERNAL_WRITE', 1),
  ('okr.key_result.checkin',                   'strategy.write',             'INTERNAL_WRITE', 1),
  ('startup_os.goal.create',                   'strategy.write',             'INTERNAL_WRITE', 1),
  ('startup_os.project.triage',                'strategy.transition',        'INTERNAL_WRITE', 1),
  ('startup_os.onboard.session_start',         'strategy.write',             'INTERNAL_WRITE', 1),
  ('startup_os.onboard.dimension_update',      'strategy.write',             'INTERNAL_WRITE', 1),
  ('startup_os.onboard.snapshot_create',       'strategy.write',             'INTERNAL_WRITE', 1),
  ('strategy.evidence.create',                 'strategy.write',             'INTERNAL_WRITE', 1),
  ('strategy.pilot.create_draft',              'strategy.write',             'INTERNAL_WRITE', 1),
  ('venture.profile.propose_update',           'strategy.write',             'INTERNAL_WRITE', 1),
  ('legal.obligation.create_draft',            'legal.obligation.manage',    'LEGAL',          1),
  ('finance.transaction.classify_propose',     'finance.reconcile',          'INTERNAL_WRITE', 1),
  ('finance.accounting_document.create_draft', 'finance.reconcile',          'INTERNAL_WRITE', 1),
  ('finance.transaction.record',               'finance.transaction.record', 'FINANCIAL',      1)
ON CONFLICT (capability_id) DO NOTHING;
