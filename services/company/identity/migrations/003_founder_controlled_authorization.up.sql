-- 003_founder_controlled_authorization.up.sql
--
-- Founder-controlled workforce authorization:
-- 1. Add allowed_member_types to core.workspace_roles and backfill system founder roles to ARRAY['HUMAN']
-- 2. Create core.workspace_authorization_states with default SHADOW mode and seed existing workspaces
-- 3. Seed operations.task.read permission and operations.task.list binding in core.capability_permission_bindings
-- 4. Create core.agent_capability_grants, core.authorization_events, core.agent_authorization_tickets
-- 5. Trigger on core.member_role_assignments enforcing allowed_member_types and matching workspace

-- 1. Extend workspace roles with allowed_member_types
ALTER TABLE core.workspace_roles ADD COLUMN IF NOT EXISTS allowed_member_types TEXT[];

-- Backfill system founder rows to ARRAY['HUMAN']
UPDATE core.workspace_roles
SET allowed_member_types = ARRAY['HUMAN']
WHERE role_key = 'founder';

-- Backfill non-founder existing roles: if they have assignments, gather member_types, otherwise default to both
UPDATE core.workspace_roles r
SET allowed_member_types = COALESCE(
    (
        SELECT array_agg(DISTINCT m.member_type)
        FROM core.member_role_assignments a
        JOIN core.workforce_members m ON a.workforce_member_id = m.id
        WHERE a.role_id = r.id
    ),
    ARRAY['HUMAN', 'AI_AGENT']
)
WHERE r.allowed_member_types IS NULL;

-- 2. Workspace authorization states (SHADOW | ENFORCED)
CREATE TABLE IF NOT EXISTS core.workspace_authorization_states (
    workspace_id BIGINT PRIMARY KEY REFERENCES core.workspaces(id) ON DELETE CASCADE,
    enforcement_mode TEXT NOT NULL DEFAULT 'SHADOW',
    authorization_epoch INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed SHADOW state for all existing workspaces
INSERT INTO core.workspace_authorization_states (workspace_id, enforcement_mode, authorization_epoch, updated_at)
SELECT id, 'SHADOW', 1, now()
FROM core.workspaces
ON CONFLICT (workspace_id) DO NOTHING;

-- 3. Capability permission bindings catalog
-- Ensure operations.task.read exists
INSERT INTO core.permission_definitions (permission_key, domain, description)
VALUES ('operations.task.read', 'operations', 'Xem thông tin và danh sách nhiệm vụ')
ON CONFLICT (permission_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS core.capability_permission_bindings (
    capability_id TEXT PRIMARY KEY,
    permission_key TEXT NOT NULL REFERENCES core.permission_definitions(permission_key) ON DELETE CASCADE,
    risk_class TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO core.capability_permission_bindings (capability_id, permission_key, risk_class, version)
VALUES ('operations.task.list', 'operations.task.read', 'READ', 1)
ON CONFLICT (capability_id) DO NOTHING;

-- 4. Agent capability grants
CREATE TABLE IF NOT EXISTS core.agent_capability_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    agent_workforce_member_id BIGINT NOT NULL REFERENCES core.workforce_members(id) ON DELETE CASCADE,
    capability_id TEXT NOT NULL REFERENCES core.capability_permission_bindings(capability_id) ON DELETE CASCADE,
    project_id BIGINT,
    legal_entity_id BIGINT,
    constraints JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    granted_by_founder_member_id BIGINT NOT NULL REFERENCES core.workforce_members(id) ON DELETE CASCADE,
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_capability_grants_lookup
    ON core.agent_capability_grants (workspace_id, agent_workforce_member_id, capability_id);

-- 5. Authorization events audit
CREATE TABLE IF NOT EXISTS core.authorization_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor_member_id BIGINT,
    target_member_id BIGINT,
    capability_id TEXT,
    role_id UUID,
    grant_id UUID,
    policy_version INTEGER,
    authorization_epoch INTEGER,
    before_hash TEXT,
    after_hash TEXT,
    reason TEXT,
    correlation_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_authorization_events_ws_created
    ON core.authorization_events (workspace_id, created_at);

-- 6. Agent authorization tickets
CREATE TABLE IF NOT EXISTS core.agent_authorization_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id TEXT NOT NULL UNIQUE,
    workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    checkpoint_ref TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    agent_workforce_member_id BIGINT NOT NULL REFERENCES core.workforce_members(id) ON DELETE CASCADE,
    authorization_epoch INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'ISSUED',
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_agent_auth_tickets_lookup
    ON core.agent_authorization_tickets (workspace_id, run_id, capability_id);

-- 7. Trigger on member_role_assignments enforcing allowed_member_types and workspace match
CREATE OR REPLACE FUNCTION core.trg_check_member_role_assignment()
RETURNS TRIGGER AS $$
DECLARE
    v_member_type TEXT;
    v_member_ws BIGINT;
    v_role_ws BIGINT;
    v_allowed_types TEXT[];
BEGIN
    SELECT workspace_id, member_type INTO v_member_ws, v_member_type
    FROM core.workforce_members
    WHERE id = NEW.workforce_member_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Workforce member % not found', NEW.workforce_member_id;
    END IF;

    SELECT workspace_id, allowed_member_types INTO v_role_ws, v_allowed_types
    FROM core.workspace_roles
    WHERE id = NEW.role_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Workspace role % not found', NEW.role_id;
    END IF;

    IF NEW.workspace_id <> v_member_ws OR NEW.workspace_id <> v_role_ws THEN
        RAISE EXCEPTION 'WORKSPACE_MISMATCH: workspace_id does not match member or role workspace';
    END IF;

    IF v_allowed_types IS NOT NULL AND array_length(v_allowed_types, 1) > 0 THEN
        IF NOT (v_member_type = ANY(v_allowed_types)) THEN
            RAISE EXCEPTION 'ROLE_MEMBER_TYPE_MISMATCH: Member type % is not allowed for role (allowed: %)', v_member_type, v_allowed_types;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_member_role_assignment ON core.member_role_assignments;
CREATE TRIGGER trg_check_member_role_assignment
    BEFORE INSERT OR UPDATE ON core.member_role_assignments
    FOR EACH ROW
    EXECUTE FUNCTION core.trg_check_member_role_assignment();
