-- Rollback for 010_automation_plan_propose_permission_binding.up.sql (grant liên quan bị xoá theo FK CASCADE).
DELETE FROM core.role_permissions WHERE permission_key = 'automation.plan.propose';
DELETE FROM core.capability_permission_bindings WHERE capability_id = 'automation.plan.propose';
DELETE FROM core.permission_definitions WHERE permission_key = 'automation.plan.propose';
