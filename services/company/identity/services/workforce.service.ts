// services/company/identity/services/workforce.service.ts
import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { identityWorkforceMembers } = schema;

export interface WorkforceMember {
  id: string;
  workspaceId: string;
  memberType: "HUMAN" | "AI_AGENT";
  humanUserId: string | null;
  agentSpecId: string | null;
  agentSpecVersion: string | null;
  managerMemberId: string | null;
  roleTitle: string;
  status: string;
}

export interface HireWorkforceMemberServiceParams {
  workspaceId: string;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  humanUserId?: string;
  agentSpecId?: string;
  agentSpecVersion?: string;
  managerMemberId?: string;
  authorization?: string;
}

export interface GetWorkforceMemberParams {
  id: string;
  workspaceId: string;
  authorization?: string;
}

function toWorkforceMember(row: {
  id: bigint;
  workspaceId: bigint;
  memberType: string;
  humanUserId: bigint | null;
  agentSpecId: string | null;
  agentSpecVersion: string | null;
  managerMemberId: bigint | null;
  roleTitle: string;
  status: string;
}): WorkforceMember {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    memberType: row.memberType as "HUMAN" | "AI_AGENT",
    humanUserId: row.humanUserId ? row.humanUserId.toString() : null,
    agentSpecId: row.agentSpecId,
    agentSpecVersion: row.agentSpecVersion,
    managerMemberId: row.managerMemberId ? row.managerMemberId.toString() : null,
    roleTitle: row.roleTitle,
    status: row.status,
  };
}

export async function hireWorkforceMemberRecord(params: HireWorkforceMemberServiceParams): Promise<WorkforceMember> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);

  const [row] = await db
    .insert(identityWorkforceMembers)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      memberType: params.memberType,
      humanUserId: params.humanUserId ? BigInt(params.humanUserId) : null,
      agentSpecId: params.agentSpecId || null,
      agentSpecVersion: params.agentSpecVersion || null,
      managerMemberId: params.managerMemberId ? BigInt(params.managerMemberId) : null,
      roleTitle: params.roleTitle,
    })
    .returning();

  if (!row) throw APIError.internal("failed to hire workforce member");
  return toWorkforceMember(row);
}

export async function getWorkforceMemberRecord(params: GetWorkforceMemberParams): Promise<WorkforceMember> {
  // Xác thực caller TRONG workspace họ khai (X-Workspace-Id), rồi resolve member
  // theo (id, workspace_id) — không fetch-global-rồi-suy-workspace-từ-row.
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);

  const [row] = await db
    .select()
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, BigInt(params.id)),
        eq(identityWorkforceMembers.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .limit(1);

  if (!row) throw APIError.notFound(`workforce member ${params.id} not found`);

  return toWorkforceMember(row);
}
