import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { randomUUID } from "crypto";
import { TenantContext } from "../../shared/types/tenant_context";
import { db, schema } from "../models/db";
import { verifyAccessToken } from "./token.service";

const {
  identityUserProjections,
  identityWorkspaces,
  identityWorkspaceMemberships,
  identityWorkforceMembers,
} = schema;

export interface ResolveTenantContextParams {
  authorization?: string;
  workspaceId: string | number;
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

  if (params.workspaceId === undefined || params.workspaceId === null || params.workspaceId === "") {
    throw APIError.invalidArgument("workspaceId is required");
  }

  const rawToken = params.authorization.startsWith("Bearer ")
    ? params.authorization.slice(7).trim()
    : params.authorization.trim();

  if (!rawToken) {
    throw APIError.unauthenticated("invalid authorization token");
  }

  // Xác thực local identity token (public path)
  let identitySub: string;
  try {
    const payload = verifyAccessToken(rawToken);
    identitySub = payload.sub;
  } catch {
    throw APIError.unauthenticated("invalid or expired token");
  }

  const localUserId = BigInt(identitySub);
  const targetWorkspaceId = BigInt(params.workspaceId);

  // Lấy thông tin user
  const [userRow] = await db
    .select({
      id: identityUserProjections.id,
      platformUserId: identityUserProjections.platformUserId,
    })
    .from(identityUserProjections)
    .where(eq(identityUserProjections.id, localUserId))
    .limit(1);

  if (!userRow) {
    throw APIError.notFound("user not found");
  }

  // Xác minh membership của user trong workspace này (công khai chỉ chứng minh
  // membership địa phương — không có fallback để lookup workspace theo companyId
  // hay chọn workspace mặc định)
  const [membership] = await db
    .select({
      role: identityWorkspaceMemberships.role,
    })
    .from(identityWorkspaceMemberships)
    .where(
      and(
        eq(identityWorkspaceMemberships.workspaceId, targetWorkspaceId),
        eq(identityWorkspaceMemberships.userId, localUserId)
      )
    )
    .limit(1);

  if (!membership) {
    throw APIError.permissionDenied(
      `user không thuộc workspace ${params.workspaceId}`
    );
  }

  // Tìm workforce member id — scoped chỉ tới workspace hiện tại
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
    workspaceId: targetWorkspaceId.toString(),
    userId: localUserId.toString(),
    workforceMemberId,
    membershipRole: membership.role,
    permissions: getRolePermissions(membership.role),
    correlationId,
  });

  return context;
}
