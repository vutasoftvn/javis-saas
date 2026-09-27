-- Rollback for 009_founder_notify_send_permission_binding.up.sql (grant liên quan bị xoá theo FK CASCADE).
DELETE FROM core.capability_permission_bindings WHERE capability_id = 'founder.notify.send';
DELETE FROM core.permission_definitions WHERE permission_key = 'founder.notify.send';
