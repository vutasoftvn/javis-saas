-- Rollback Bug B2 grant: thu hồi DML mà 024 đã cấp cho agent_app.
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.event_inbox FROM agent_app;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.event_trigger_rules FROM agent_app;
