-- Rollback for 011_okr_key_result_update_permission_binding.up.sql (grant liên quan bị xoá theo FK CASCADE).
DELETE FROM core.role_permissions WHERE permission_key = 'okr.key_result.update';
DELETE FROM core.capability_permission_bindings WHERE capability_id = 'okr.key_result.update';
DELETE FROM core.permission_definitions WHERE permission_key = 'okr.key_result.update';
