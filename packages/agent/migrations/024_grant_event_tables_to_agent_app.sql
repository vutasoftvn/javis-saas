-- Bug B2: event_inbox (migration 019) + event_trigger_rules (020) được tạo không
-- kèm schema nên nằm ở `public`; _grant_application_access trong scripts/migrate.py
-- cố tình bỏ qua `public` -> agent_app thiếu quyền DML, runtime lỗi
-- "permission denied for table event_inbox". Cấp tường minh ở đây.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_inbox TO agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_trigger_rules TO agent_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agent_app;
