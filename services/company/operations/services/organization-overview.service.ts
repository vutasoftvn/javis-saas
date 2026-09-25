import { APIError } from "encore.dev/api";
import { and, asc, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  identityWorkforceMembers,
  identityWorkspaces,
} from "../../shared/db/schema/identity";
import { TenantContext } from "../../shared/types/tenant_context";

// Contract Organization hẹp và có kiểm quyền server-side (spec 2026-09-25 §7):
// thay các lời gọi `/org/*` không tồn tại của Flutter.

const { workspaceAgents } = schema;

export const ORGANIZATION_WORKFORCE_MANAGE = "organization.workforce.manage";

export interface OrganizationOverviewResponse {
  organizationId: string;
  name: string;
  lifecycleStage: string;
  viewerRole: string;
  canManageWorkforce: boolean;
  humanMemberCount: number;
  aiMemberCount: number;
}

export interface OrganizationWorkforceMember {
  id: string;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  managerMemberId: string | null;
  status: string;
  workspaceAgentId: string | null;
}

export interface WorkforceListResponse {
  organizationId: string;
  members: OrganizationWorkforceMember[];
}

export interface CreateAiWorkforceRequest {
  organizationId: string;
  roleTitle: string;
  workspaceAgentId: string;
  managerMemberId?: string;
  idempotencyKey: string;
}

export interface CreateAiWorkforceResponse {
  member: OrganizationWorkforceMember;
}

const NUMERIC_ID = /^\d{1,19}$/;

export function canManageWorkforce(ctx: TenantContext): boolean {
  if (ctx.isAiAgent) return false;
  return ctx.permissions.includes("*") || ctx.permissions.includes(ORGANIZATION_WORKFORCE_MANAGE);
}

export async function getOrganizationOverview(
  ctx: TenantContext
): Promise<OrganizationOverviewResponse> {
  const wsId = BigInt(ctx.workspaceId);
  const [workspace] = await db
    .select({ name: identityWorkspaces.name, lifecycleStage: identityWorkspaces.lifecycleStage })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, wsId))
    .limit(1);
  if (!workspace) throw APIError.notFound("organization not found");

  const members = await db
    .select({ memberType: identityWorkforceMembers.memberType })
    .from(identityWorkforceMembers)
    .where(
      and(eq(identityWorkforceMembers.workspaceId, wsId), isNull(identityWorkforceMembers.deletedAt))
    );

  return {
    organizationId: ctx.workspaceId,
    name: workspace.name,
    lifecycleStage: workspace.lifecycleStage,
    viewerRole: ctx.membershipRole,
    canManageWorkforce: canManageWorkforce(ctx),
    humanMemberCount: members.filter((m) => m.memberType === "HUMAN").length,
    aiMemberCount: members.filter((m) => m.memberType === "AI_AGENT").length,
  };
}

export async function listOrganizationWorkforce(ctx: TenantContext): Promise<WorkforceListResponse> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select({
      id: identityWorkforceMembers.id,
      memberType: identityWorkforceMembers.memberType,
      roleTitle: identityWorkforceMembers.roleTitle,
      managerMemberId: identityWorkforceMembers.managerMemberId,
      status: identityWorkforceMembers.status,
      workspaceAgentId: workspaceAgents.id,
    })
    .from(identityWorkforceMembers)
    .leftJoin(
      workspaceAgents,
      and(
        eq(workspaceAgents.workforceMemberId, identityWorkforceMembers.id),
        eq(workspaceAgents.workspaceId, identityWorkforceMembers.workspaceId)
      )
    )
    .where(
      and(eq(identityWorkforceMembers.workspaceId, wsId), isNull(identityWorkforceMembers.deletedAt))
    )
    .orderBy(asc(identityWorkforceMembers.createdAt));

  return {
    organizationId: ctx.workspaceId,
    members: rows.map((row) => ({
      id: row.id.toString(),
      memberType: row.memberType === "AI_AGENT" ? "AI_AGENT" : "HUMAN",
      roleTitle: row.roleTitle,
      managerMemberId: row.managerMemberId ? row.managerMemberId.toString() : null,
      status: row.status,
      workspaceAgentId: row.workspaceAgentId ? row.workspaceAgentId.toString() : null,
    })),
  };
}

function normalizeCreateRequest(input: CreateAiWorkforceRequest): {
  roleTitle: string;
  workspaceAgentId: bigint;
  managerMemberId: bigint | null;
} {
  const roleTitle = (input.roleTitle ?? "").trim();
  if (!roleTitle || roleTitle.length > 120) {
    throw APIError.invalidArgument("roleTitle is required (max 120 characters)");
  }
  const idempotencyKey = (input.idempotencyKey ?? "").trim();
  if (!idempotencyKey || idempotencyKey.length > 128) {
    throw APIError.invalidArgument("idempotencyKey is required (max 128 characters)");
  }
  if (!NUMERIC_ID.test(input.workspaceAgentId ?? "")) {
    throw APIError.invalidArgument("workspaceAgentId must be a numeric id");
  }
  if (input.managerMemberId !== undefined && !NUMERIC_ID.test(input.managerMemberId)) {
    throw APIError.invalidArgument("managerMemberId must be a numeric id");
  }
  return {
    roleTitle,
    workspaceAgentId: BigInt(input.workspaceAgentId),
    managerMemberId: input.managerMemberId ? BigInt(input.managerMemberId) : null,
  };
}

/**
 * Đưa một workspace agent đã publish (ACTIVE, có version + hash pin) vào sơ đồ
 * tổ chức dưới dạng WorkforceMember AI. Agent đã có đúng một WorkforceMember
 * (tạo lúc createWorkspaceAgent) nên thao tác này chỉ cập nhật vị trí
 * roleTitle/manager của member đó — lặp lại cùng input là idempotent, không
 * sinh member trùng. Client không gửi được prompt/spec/capability.
 */
export async function createAiWorkforceMember(
  ctx: TenantContext,
  input: CreateAiWorkforceRequest
): Promise<CreateAiWorkforceResponse> {
  if (!canManageWorkforce(ctx)) {
    throw APIError.permissionDenied(`Missing permission ${ORGANIZATION_WORKFORCE_MANAGE}`);
  }
  const normalized = normalizeCreateRequest(input);
  const wsId = BigInt(ctx.workspaceId);

  return db.transaction(async (tx) => {
    const [agent] = await tx
      .select({
        id: workspaceAgents.id,
        state: workspaceAgents.state,
        agentAssetVersion: workspaceAgents.agentAssetVersion,
        agentDefinitionHash: workspaceAgents.agentDefinitionHash,
        workforceMemberId: workspaceAgents.workforceMemberId,
      })
      .from(workspaceAgents)
      .where(
        and(eq(workspaceAgents.id, normalized.workspaceAgentId), eq(workspaceAgents.workspaceId, wsId))
      )
      .limit(1);
    if (!agent) {
      throw APIError.notFound("workspace agent not found in organization");
    }
    if (agent.state !== "ACTIVE" || !agent.agentAssetVersion || !agent.agentDefinitionHash) {
      throw APIError.failedPrecondition("workspace agent is not deployable");
    }

    if (normalized.managerMemberId !== null) {
      if (normalized.managerMemberId === agent.workforceMemberId) {
        throw APIError.invalidArgument("a workforce member cannot manage itself");
      }
      const [manager] = await tx
        .select({ id: identityWorkforceMembers.id })
        .from(identityWorkforceMembers)
        .where(
          and(
            eq(identityWorkforceMembers.id, normalized.managerMemberId),
            eq(identityWorkforceMembers.workspaceId, wsId),
            isNull(identityWorkforceMembers.deletedAt)
          )
        )
        .limit(1);
      if (!manager) throw APIError.invalidArgument("managerMemberId is not in this organization");
    }

    const [member] = await tx
      .update(identityWorkforceMembers)
      .set({
        roleTitle: normalized.roleTitle,
        managerMemberId: normalized.managerMemberId,
        status: "active",
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(identityWorkforceMembers.id, agent.workforceMemberId),
          eq(identityWorkforceMembers.workspaceId, wsId),
          eq(identityWorkforceMembers.memberType, "AI_AGENT"),
          isNull(identityWorkforceMembers.deletedAt)
        )
      )
      .returning();
    if (!member) {
      throw APIError.failedPrecondition("workspace agent has no active AI workforce member");
    }

    return {
      member: {
        id: member.id.toString(),
        memberType: "AI_AGENT",
        roleTitle: member.roleTitle,
        managerMemberId: member.managerMemberId ? member.managerMemberId.toString() : null,
        status: member.status,
        workspaceAgentId: agent.id.toString(),
      },
    };
  });
}
