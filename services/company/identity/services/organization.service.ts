import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { identityOrganizations, identityWorkforceMembers } = schema;

export interface Organization {
  id: string;
  workspaceId: string;
  name: string;
}

export interface CreateOrganizationParams {
  workspaceId: string | number;
  name: string;
}

export interface WorkforceMember {
  id: string;
  organizationId: string;
  memberType: "HUMAN" | "AI_AGENT";
  humanUserId: string | null;
  agentDefinitionId: string | null;
  agentProfileId: string | null;
  roleTitle: string;
  status: string;
}

export interface HireWorkforceMemberParams {
  organizationId: string | number;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  humanUserId?: string | number;
  agentDefinitionId?: string | number;
  agentProfileId?: string;
}

export async function createOrganizationRecord(params: CreateOrganizationParams): Promise<Organization> {
  const [row] = await db
    .insert(identityOrganizations)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      name: params.name,
    })
    .returning({
      id: identityOrganizations.id,
      workspaceId: identityOrganizations.workspaceId,
      name: identityOrganizations.name,
    });

  if (!row) throw APIError.internal("failed to create organization");
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    name: row.name,
  };
}

export async function hireWorkforceMemberRecord(params: HireWorkforceMemberParams): Promise<WorkforceMember> {
  const [row] = await db
    .insert(identityWorkforceMembers)
    .values({
      id: generateSnowflake(),
      organizationId: BigInt(params.organizationId),
      memberType: params.memberType,
      humanUserId: params.humanUserId ? BigInt(params.humanUserId) : null,
      agentDefinitionId: params.agentDefinitionId ? BigInt(params.agentDefinitionId) : null,
      agentProfileId: params.agentProfileId || null,
      roleTitle: params.roleTitle,
    })
    .returning({
      id: identityWorkforceMembers.id,
      organizationId: identityWorkforceMembers.organizationId,
      memberType: identityWorkforceMembers.memberType,
      humanUserId: identityWorkforceMembers.humanUserId,
      agentDefinitionId: identityWorkforceMembers.agentDefinitionId,
      agentProfileId: identityWorkforceMembers.agentProfileId,
      roleTitle: identityWorkforceMembers.roleTitle,
      status: identityWorkforceMembers.status,
    });

  if (!row) throw APIError.internal("failed to hire workforce member");
  return {
    id: row.id.toString(),
    organizationId: row.organizationId.toString(),
    memberType: row.memberType as "HUMAN" | "AI_AGENT",
    humanUserId: row.humanUserId ? row.humanUserId.toString() : null,
    agentDefinitionId: row.agentDefinitionId ? row.agentDefinitionId.toString() : null,
    agentProfileId: row.agentProfileId,
    roleTitle: row.roleTitle,
    status: row.status,
  };
}

export async function getWorkforceMemberRecord(id: string | number): Promise<WorkforceMember> {
  const [row] = await db
    .select({
      id: identityWorkforceMembers.id,
      organizationId: identityWorkforceMembers.organizationId,
      memberType: identityWorkforceMembers.memberType,
      humanUserId: identityWorkforceMembers.humanUserId,
      agentDefinitionId: identityWorkforceMembers.agentDefinitionId,
      agentProfileId: identityWorkforceMembers.agentProfileId,
      roleTitle: identityWorkforceMembers.roleTitle,
      status: identityWorkforceMembers.status,
    })
    .from(identityWorkforceMembers)
    .where(eq(identityWorkforceMembers.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workforce member ${id} not found`);
  return {
    id: row.id.toString(),
    organizationId: row.organizationId.toString(),
    memberType: row.memberType as "HUMAN" | "AI_AGENT",
    humanUserId: row.humanUserId ? row.humanUserId.toString() : null,
    agentDefinitionId: row.agentDefinitionId ? row.agentDefinitionId.toString() : null,
    agentProfileId: row.agentProfileId,
    roleTitle: row.roleTitle,
    status: row.status,
  };
}
