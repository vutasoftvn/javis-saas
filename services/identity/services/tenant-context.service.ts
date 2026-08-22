import { APIError } from "encore.dev/api";
import { eq, and, sql } from "drizzle-orm";
import { randomUUID } from "crypto";
import { TenantContext } from "../../shared/types/tenant_context";
import { db, schema } from "../models/db";
import { verifyAccessToken } from "./token.service";
import { verifyPlatformToken } from "../../control-plane/services/token.service";
import { validateUserMembership } from "../../control-plane/services/company.service";

const {
  identityUsers,
  identityWorkspaces,
  identityWorkspaceMembers,
  identityOrganizations,
  identityWorkforceMembers,
} = schema;

export interface ResolveTenantContextParams {
  authorization?: string;
  workspaceId?: string | number;
  companyId?: string | number;
  correlationId?: string;
}

export function getRolePermissions(role: string): readonly string[] {
  switch (role) {
    case "founder":
    case "co-founder":
      return Object.freeze(["*"]);
    case "user":
    case "member":
    case "admin":
      return Object.freeze(["read", "write"]);
    case "auditor":
      return Object.freeze(["read"]);
    default:
      return Object.freeze(["read"]);
  }
}

export async function resolveTenantContext(
  params: ResolveTenantContextParams
): Promise<TenantContext> {
  const correlationId = params.correlationId?.trim() || randomUUID();

  if (!params.authorization) {
    throw APIError.unauthenticated("missing authorization header or token");
  }

  const rawToken = params.authorization.startsWith("Bearer ")
    ? params.authorization.slice(7).trim()
    : params.authorization.trim();

  if (!rawToken) {
    throw APIError.unauthenticated("invalid authorization token");
  }

  // 1. Kiểm tra xem token là Platform token hay Local identity token
  let isPlatform = false;
  let platformSub: string | null = null;
  try {
    const platformPayload = verifyPlatformToken(rawToken);
    if (platformPayload.aud === "control_plane") {
      isPlatform = true;
      platformSub = platformPayload.sub;
    }
  } catch {
    // Không phải platform token, thử với local identity token
  }

  if (isPlatform && platformSub) {
    if (!params.companyId) {
      throw APIError.invalidArgument("companyId is required when using platform token");
    }

    const membership = await validateUserMembership({
      platformToken: rawToken,
      companyId: String(params.companyId),
    });

    // Lookup local workspace for this company
    let [ws] = await db
      .select({ id: identityWorkspaces.id })
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.platformCompanyId, membership.companyId))
      .limit(1);

    let workspaceIdStr = ws ? ws.id.toString() : (params.workspaceId ? String(params.workspaceId) : "1");

    // Lookup local user
    let [localUser] = await db
      .select({ id: identityUsers.id })
      .from(identityUsers)
      .where(eq(identityUsers.platformUserId, membership.userId))
      .limit(1);

    // Lookup workforce member if user exists
    let workforceMemberId: string | undefined = undefined;
    if (localUser) {
      const [wfMember] = await db
        .select({ id: identityWorkforceMembers.id })
        .from(identityWorkforceMembers)
        .where(eq(identityWorkforceMembers.humanUserId, localUser.id))
        .limit(1);
      if (wfMember) {
        workforceMemberId = wfMember.id.toString();
      }
    }

    const role = membership.roleId || "user";
    const context: TenantContext = Object.freeze({
      companyId: membership.companyId,
      workspaceId: workspaceIdStr,
      userId: membership.userId,
      workforceMemberId,
      membershipRole: role,
      permissions: getRolePermissions(role),
      correlationId,
    });

    return context;
  }

  // 2. Local identity token
  let identitySub: string;
  try {
    const payload = verifyAccessToken(rawToken);
    identitySub = payload.sub;
  } catch {
    throw APIError.unauthenticated("invalid or expired token");
  }

  const localUserId = BigInt(identitySub);

  // Lấy thông tin user
  const [userRow] = await db
    .select({
      id: identityUsers.id,
      platformUserId: identityUsers.platformUserId,
      role: identityUsers.role,
    })
    .from(identityUsers)
    .where(eq(identityUsers.id, localUserId))
    .limit(1);

  if (!userRow) {
    throw APIError.notFound("user not found");
  }

  // Xác định workspace
  let targetWorkspaceId: bigint;
  let memberRole = userRow.role || "member";

  if (params.workspaceId) {
    targetWorkspaceId = BigInt(params.workspaceId);
    const [membership] = await db
      .select({
        role: identityWorkspaceMembers.role,
      })
      .from(identityWorkspaceMembers)
      .where(
        and(
          eq(identityWorkspaceMembers.workspaceId, targetWorkspaceId),
          eq(identityWorkspaceMembers.userId, localUserId)
        )
      )
      .limit(1);

    if (membership) {
      memberRole = membership.role;
    }
  } else {
    // Lấy membership đầu tiên của user
    const [firstMembership] = await db
      .select({
        workspaceId: identityWorkspaceMembers.workspaceId,
        role: identityWorkspaceMembers.role,
      })
      .from(identityWorkspaceMembers)
      .where(eq(identityWorkspaceMembers.userId, localUserId))
      .limit(1);

    if (firstMembership) {
      targetWorkspaceId = firstMembership.workspaceId;
      memberRole = firstMembership.role;
    } else {
      targetWorkspaceId = BigInt(1);
    }
  }

  // Lấy companyId từ workspace nếu có liên kết platform
  const [wsRow] = await db
    .select({
      id: identityWorkspaces.id,
      platformCompanyId: identityWorkspaces.platformCompanyId,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, targetWorkspaceId))
    .limit(1);

  const companyId = wsRow?.platformCompanyId || (params.companyId ? String(params.companyId) : targetWorkspaceId.toString());

  // Tìm workforce member id
  let workforceMemberId: string | undefined = undefined;
  const [wfMember] = await db
    .select({ id: identityWorkforceMembers.id })
    .from(identityWorkforceMembers)
    .where(eq(identityWorkforceMembers.humanUserId, localUserId))
    .limit(1);

  if (wfMember) {
    workforceMemberId = wfMember.id.toString();
  }

  const context: TenantContext = Object.freeze({
    companyId,
    workspaceId: targetWorkspaceId.toString(),
    userId: localUserId.toString(),
    workforceMemberId,
    membershipRole: memberRole,
    permissions: getRolePermissions(memberRole),
    correlationId,
  });

  return context;
}
