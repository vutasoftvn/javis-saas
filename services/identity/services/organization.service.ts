import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { identityOrganizations, identityWorkforceMembers } = schema;

export interface Organization {
  id: number;
  workspaceId: number;
  name: string;
}

export interface CreateOrganizationParams {
  workspaceId: number;
  name: string;
}

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

export async function createOrganizationRecord(params: CreateOrganizationParams): Promise<Organization> {
  const [row] = await db
    .insert(identityOrganizations)
    .values({
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
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    name: row.name,
  };
}

export async function hireWorkforceMemberRecord(params: HireWorkforceMemberParams): Promise<WorkforceMember> {
  const [row] = await db
    .insert(identityWorkforceMembers)
    .values({
      organizationId: BigInt(params.organizationId),
      memberType: params.memberType,
      humanUserId: params.humanUserId ? BigInt(params.humanUserId) : null,
      agentDefinitionId: params.agentDefinitionId ? BigInt(params.agentDefinitionId) : null,
      roleTitle: params.roleTitle,
    })
    .returning({
      id: identityWorkforceMembers.id,
      organizationId: identityWorkforceMembers.organizationId,
      memberType: identityWorkforceMembers.memberType,
      humanUserId: identityWorkforceMembers.humanUserId,
      agentDefinitionId: identityWorkforceMembers.agentDefinitionId,
      roleTitle: identityWorkforceMembers.roleTitle,
      status: identityWorkforceMembers.status,
    });

  if (!row) throw APIError.internal("failed to hire workforce member");
  return {
    id: Number(row.id),
    organizationId: Number(row.organizationId),
    memberType: row.memberType as "HUMAN" | "AI_AGENT",
    humanUserId: row.humanUserId ? Number(row.humanUserId) : null,
    agentDefinitionId: row.agentDefinitionId ? Number(row.agentDefinitionId) : null,
    roleTitle: row.roleTitle,
    status: row.status,
  };
}

export async function getWorkforceMemberRecord(id: number): Promise<WorkforceMember> {
  const [row] = await db
    .select({
      id: identityWorkforceMembers.id,
      organizationId: identityWorkforceMembers.organizationId,
      memberType: identityWorkforceMembers.memberType,
      humanUserId: identityWorkforceMembers.humanUserId,
      agentDefinitionId: identityWorkforceMembers.agentDefinitionId,
      roleTitle: identityWorkforceMembers.roleTitle,
      status: identityWorkforceMembers.status,
    })
    .from(identityWorkforceMembers)
    .where(eq(identityWorkforceMembers.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workforce member ${id} not found`);
  return {
    id: Number(row.id),
    organizationId: Number(row.organizationId),
    memberType: row.memberType as "HUMAN" | "AI_AGENT",
    humanUserId: row.humanUserId ? Number(row.humanUserId) : null,
    agentDefinitionId: row.agentDefinitionId ? Number(row.agentDefinitionId) : null,
    roleTitle: row.roleTitle,
    status: row.status,
  };
}
