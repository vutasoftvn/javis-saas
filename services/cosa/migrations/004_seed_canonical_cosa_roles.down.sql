-- Remove the canonical roles this migration added that were not in the 001
-- baseline seed. Leave founder / co-founder / superadmin / support (also seeded
-- by 001) and any role currently referenced by a profile / user / invitation.
DELETE FROM cosa.roles r
WHERE r.id IN ('mentor', 'investor', 'tech', 'marketing', 'sales', 'finance',
               'hr', 'operations', 'member')
  AND NOT EXISTS (SELECT 1 FROM cosa.profiles p WHERE p.role_id = r.id)
  AND NOT EXISTS (SELECT 1 FROM cosa.users u WHERE u.platform_role_id = r.id)
  AND NOT EXISTS (SELECT 1 FROM cosa.workspace_invitations i WHERE i.role_id = r.id);
