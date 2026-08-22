import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";

export interface Organization {
  id: number;
  workspaceId: number;
  name: string;
}

export interface CreateOrganizationParams {
  workspaceId: number;
  name: string;
}

export const createOrganization = api(
  { method: "POST", path: "/identity/organizations", expose: true },
  async (params: CreateOrganizationParams): Promise<Organization> => {
    const row = await identityDB.queryRow<{ id: number; workspace_id: number; name: string }>`
      INSERT INTO core.organizations (workspace_id, name)
      VALUES (${params.workspaceId}, ${params.name})
      RETURNING id, workspace_id, name
    `;
    if (!row) throw APIError.internal("failed to create organization");
    return { id: row.id, workspaceId: row.workspace_id, name: row.name };
  }
);

export interface WorkforceMember {
  id: number;
  organizationId: number;
  memberType: "HUMAN" | "AI_AGENT";
  humanUserId: number | null;
  agentDefinitionId: number | null;
  roleTitle: string;
  status: string;
}

export interface HireWorkforceMemberParams {
  organizationId: number;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  humanUserId?: number;
  agentDefinitionId?: number;
}

interface WorkforceMemberRow {
  id: number;
  organization_id: number;
  member_type: string;
  human_user_id: number | null;
  agent_definition_id: number | null;
  role_title: string;
  status: string;
}

function rowToWorkforceMember(row: WorkforceMemberRow): WorkforceMember {
  return {
    id: row.id,
    organizationId: row.organization_id,
    memberType: row.member_type as "HUMAN" | "AI_AGENT",
    humanUserId: row.human_user_id,
    agentDefinitionId: row.agent_definition_id,
    roleTitle: row.role_title,
    status: row.status,
  };
}

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (params: HireWorkforceMemberParams): Promise<WorkforceMember> => {
    const row = await identityDB.queryRow<WorkforceMemberRow>`
      INSERT INTO core.workforce_members (organization_id, member_type, human_user_id, agent_definition_id, role_title)
      VALUES (${params.organizationId}, ${params.memberType}, ${params.humanUserId ?? null}, ${params.agentDefinitionId ?? null}, ${params.roleTitle})
      RETURNING id, organization_id, member_type, human_user_id, agent_definition_id, role_title, status
    `;
    if (!row) throw APIError.internal("failed to hire workforce member");
    return rowToWorkforceMember(row);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({ id }: { id: number }): Promise<WorkforceMember> => {
    const row = await identityDB.queryRow<WorkforceMemberRow>`
      SELECT id, organization_id, member_type, human_user_id, agent_definition_id, role_title, status
      FROM core.workforce_members WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`workforce member ${id} not found`);
    return rowToWorkforceMember(row);
  }
);
