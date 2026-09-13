-- Migration 015 down: Rollback security profile backfill
-- Chú ý: fail-closed nếu đã có bằng chứng sử dụng (activation, workforce, non-template, custom events...).

DO $$
DECLARE
  v_has_usage boolean;
BEGIN
  -- 1. Kiểm tra nếu có bất kỳ security assignment nào đã kích hoạt, không phải TEMPLATE, hoặc có metadata thực thi
  SELECT EXISTS (
    SELECT 1
    FROM operating.project_agent_assignments
    WHERE profile_key = 'security'
      AND (
        state != 'TEMPLATE'
        OR version != 1
        OR agent_workforce_member_id IS NOT NULL
        OR spec_id IS NOT NULL
        OR spec_version IS NOT NULL
        OR spec_hash IS NOT NULL
        OR activation_policy_snapshot IS NOT NULL
        OR activated_by IS NOT NULL
        OR activated_at IS NOT NULL
        OR paused_by IS NOT NULL
        OR paused_at IS NOT NULL
        OR disabled_reason IS NOT NULL
      )
  ) INTO v_has_usage;

  IF v_has_usage THEN
    RAISE EXCEPTION 'migration 015 down refused: security profile has usage evidence';
  END IF;

  -- 2. Kiểm tra nếu có sự kiện nào khác ngoài sự kiện tạo template ban đầu do migration 015 backfill
  SELECT EXISTS (
    SELECT 1
    FROM operating.project_agent_assignment_events e
    JOIN operating.project_agent_assignments a ON a.id = e.assignment_id
    WHERE a.profile_key = 'security'
      AND (
        e.event_type != 'ASSIGNMENT_TEMPLATE_CREATED'
        OR (e.event_payload->>'source') IS DISTINCT FROM 'security_profile_catalog_backfill_v1'
      )
  ) INTO v_has_usage;

  IF v_has_usage THEN
    RAISE EXCEPTION 'migration 015 down refused: security profile has usage evidence';
  END IF;

  -- 3. Kiểm tra nếu có assignment nào có nhiều hơn 1 sự kiện
  SELECT EXISTS (
    SELECT 1
    FROM operating.project_agent_assignment_events e
    JOIN operating.project_agent_assignments a ON a.id = e.assignment_id
    WHERE a.profile_key = 'security'
    GROUP BY e.assignment_id
    HAVING COUNT(*) > 1
  ) INTO v_has_usage;

  IF v_has_usage THEN
    RAISE EXCEPTION 'migration 015 down refused: security profile has usage evidence';
  END IF;

  -- 4. Kiểm tra nếu có deliberation frame nào tham chiếu đến ciso role
  SELECT EXISTS (
    SELECT 1
    FROM operating.project_executive_deliberation_frames f,
         jsonb_array_elements(f.selected_roles) AS r
    WHERE (r->>'roleKey') = 'ciso'
  ) INTO v_has_usage;

  IF v_has_usage THEN
    RAISE EXCEPTION 'migration 015 down refused: ciso role is referenced in deliberation frames';
  END IF;

  -- 5. Xoá an toàn sự kiện và assignment template của security
  DELETE FROM operating.project_agent_assignment_events
  WHERE assignment_id IN (
    SELECT id FROM operating.project_agent_assignments WHERE profile_key = 'security'
  );

  DELETE FROM operating.project_agent_assignments
  WHERE profile_key = 'security';

END $$;
