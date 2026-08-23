INSERT INTO cosa.roles (id, scope, level, description)
VALUES ('auditor', 'company', 20, 'Read-only company auditor')
ON CONFLICT (id) DO NOTHING;
