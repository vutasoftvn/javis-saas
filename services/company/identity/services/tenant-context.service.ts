import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { randomUUID } from "crypto";
import { TenantContext } from "../../shared/types/tenant_context";
import { db, schema } from "../models/db";
import { verifyAccessToken } from "./token.service";
import { assertSessionAfterRevocation } from "./membership-reconciliation.service";
import { verifyCosaDelegationForCapability } from "../../shared/auth/cosa-delegation.service";

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
  /**
   * Capability id mà endpoint cho phép agent dùng thay mặt user. Rỗng/thiếu ⇒
   * endpoint chỉ nhận phiên đăng nhập của người dùng (mặc định, least privilege).
   */
  agentCapabilities?: readonly string[];
}

interface AgentDelegationIdentity {
  userSub: string;
  jti: string;
}

/**
 * Agent (apps/cosa) gọi Company bằng delegation ký bởi COSA_COMPANY_DELEGATION_SECRET,
 * scoped {workspace_id, run_id, capability_ids}. Chỉ chấp nhận khi endpoint khai báo
 * capability và token có ít nhất một capability đó, đúng workspace. Trả null nếu token
 * không phải delegation hợp lệ (để caller báo unauthenticated như cũ).
 */
function verifyAgentDelegation(
  rawToken: string,
  workspaceId: string,
  capabilities: readonly string[]
): AgentDelegationIdentity | null {
  let scopeError: Error | null = null;
  for (const capabilityId of capabilities) {
    try {
      const claims = verifyCosaDelegationForCapability(rawToken, { workspaceId, capabilityId });
      // apps/cosa mint `sub` = principal của request, dạng "user:<local user id>".
      const userSub = claims.sub.startsWith("user:") ? claims.sub.slice(5) : claims.sub;
      return { userSub, jti: claims.jti };
    } catch (err) {
      const message = (err as Error).message;
      if (message.startsWith("invalid cosa delegation token")) {
        return null;
      }
      scopeError = err as Error;
    }
  }
  if (scopeError) {
    throw APIError.permissionDenied(`cosa delegation rejected: ${scopeError.message}`);
  }
  return null;
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

  // Xác thực local identity token (public path). Nếu không phải phiên người dùng
  // và endpoint cho phép agent, thử delegation của agent: agent hành động thay mặt
  // user nên vẫn đi qua đúng membership/role của user bên dưới (không vượt quyền user).
  let identitySub: string;
  let sessionAuthTime: number | undefined;
  let isAiAgent = false;
  let delegationCorrelationId: string | undefined;
  try {
    const payload = verifyAccessToken(rawToken);
    identitySub = payload.sub;
    sessionAuthTime = payload.auth_time;
  } catch {
    const delegated = params.agentCapabilities?.length
      ? verifyAgentDelegation(rawToken, String(params.workspaceId), params.agentCapabilities)
      : null;
    if (!delegated) {
      throw APIError.unauthenticated("invalid or expired token");
    }
    identitySub = delegated.userSub;
    isAiAgent = true;
    delegationCorrelationId = delegated.jti;
  }

  // BigInt() ném SyntaxError trần với chuỗi không phải số — phải map thành
  // lỗi 4xx thay vì để lọt ra client thành 500.
  let localUserId: bigint;
  let targetWorkspaceId: bigint;
  try {
    localUserId = BigInt(identitySub);
  } catch {
    throw APIError.unauthenticated("invalid token subject");
  }
  try {
    targetWorkspaceId = BigInt(params.workspaceId);
  } catch {
    throw APIError.invalidArgument("workspaceId must be a numeric id");
  }

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
      membershipState: identityWorkspaceMemberships.membershipState,
      sessionNotBefore: identityWorkspaceMemberships.sessionNotBefore,
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
  // Core đã thu hồi membership (tombstone từ event/sync) ⇒ local JWT còn hạn
  // cũng không được đọc/ghi workspace này nữa (spec 2026-09-25 §6).
  if (membership.membershipState !== "active") {
    throw APIError.permissionDenied(
      `membership của user tại workspace ${params.workspaceId} đã bị thu hồi`
    );
  }
  // Session epoch (plan 2026-09-25 Task 4): membership từng bị thu hồi rồi cấp lại
  // không trả quyền cho local session cấp trước lần thu hồi. Delegation của agent
  // do apps/cosa mint theo từng run ngắn hạn nên chỉ kiểm membership active ở trên.
  if (!isAiAgent) {
    assertSessionAfterRevocation(sessionAuthTime, membership.sessionNotBefore, String(params.workspaceId));
  }

  // Tìm workforce member id — scoped chỉ tới workspace hiện tại
  let workforceMemberId: string | undefined = undefined;
  const [wfMember] = await db
    .select({ id: identityWorkforceMembers.id })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.humanUserId, localUserId),
        eq(identityWorkforceMembers.workspaceId, targetWorkspaceId)
      )
    )
    .limit(1);

  if (wfMember) {
    workforceMemberId = wfMember.id.toString();
  }

  let policyVersion = 1;
  const [latestVer] = await db
    .select({ version: schema.coreWorkspacePolicyVersions.version })
    .from(schema.coreWorkspacePolicyVersions)
    .where(eq(schema.coreWorkspacePolicyVersions.workspaceId, targetWorkspaceId))
    .orderBy(desc(schema.coreWorkspacePolicyVersions.version))
    .limit(1);
  if (latestVer) {
    policyVersion = latestVer.version;
  }

  const context: TenantContext = Object.freeze({
    workspaceId: targetWorkspaceId.toString(),
    userId: localUserId.toString(),
    workforceMemberId,
    membershipRole: membership.role,
    permissions: getRolePermissions(membership.role),
    correlationId: delegationCorrelationId ?? correlationId,
    platformUserId: userRow.platformUserId ?? null,
    policyVersion,
    ...(isAiAgent ? { isAiAgent: true } : {}),
  });

  return context;
}
