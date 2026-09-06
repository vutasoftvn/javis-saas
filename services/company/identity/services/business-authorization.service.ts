import { APIError } from "encore.dev/api";
import { eq, and, lte, or, isNull, gt, desc } from "drizzle-orm";
import { db } from "../models/db";
import {
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  coreWorkspacePolicyVersions,
  identityWorkspaceMemberships,
} from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";
import { isKnownPermission } from "./permission-catalog";
import {
  combinePermissionRules,
  matchBestRuleInRole,
  PermissionEffect,
  PermissionRule,
} from "./permission-evaluator";

export type Effect = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";

export interface ResourceScope {
  workspaceId: string;
  projectId?: string;
  legalEntityId?: string;
}

export interface RuleDecision {
  effect: Effect;
  reasonCodes: string[];
  policyVersion: number;
  matchedRuleIds: string[];
  approvalRequired: boolean;
}

export async function getLatestPolicyVersion(workspaceId: bigint): Promise<number> {
  const [latest] = await db
    .select({ version: coreWorkspacePolicyVersions.version })
    .from(coreWorkspacePolicyVersions)
    .where(eq(coreWorkspacePolicyVersions.workspaceId, workspaceId))
    .orderBy(desc(coreWorkspacePolicyVersions.version))
    .limit(1);

  return latest?.version ?? 1;
}

export async function authorizeBusinessAction(
  ctx: TenantContext,
  action: string,
  scope?: ResourceScope,
  facts?: Record<string, any>
): Promise<RuleDecision> {
  if (!ctx) {
    throw APIError.unauthenticated("Tenant context is required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const policyVersion = await getLatestPolicyVersion(wsId);

  // Scope tenant isolation check
  if (scope?.workspaceId && String(scope.workspaceId) !== String(ctx.workspaceId)) {
    return {
      effect: "DENY",
      reasonCodes: ["CROSS_WORKSPACE_ACCESS_DENIED"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
    };
  }

  // Catalog validation
  if (!isKnownPermission(action)) {
    return {
      effect: "DENY",
      reasonCodes: ["UNKNOWN_ACTION"],
      policyVersion,
      matchedRuleIds: [],
      approvalRequired: false,
    };
  }

  const roleName = (ctx.membershipRole || "").toLowerCase();
  const isFounder = ["founder", "co-founder"].includes(roleName);

  // If workforceMemberId is present, query active role assignments
  const applicableRules: PermissionRule[] = [];
  const matchedRuleIds: string[] = [];

  if (ctx.workforceMemberId) {
    const memberId = BigInt(ctx.workforceMemberId);
    const now = new Date();

    const assignments = await db
      .select({
        assignmentId: coreMemberRoleAssignments.id,
        roleId: coreMemberRoleAssignments.roleId,
        projectId: coreMemberRoleAssignments.projectId,
        legalEntityId: coreMemberRoleAssignments.legalEntityId,
      })
      .from(coreMemberRoleAssignments)
      .where(
        and(
          eq(coreMemberRoleAssignments.workspaceId, wsId),
          eq(coreMemberRoleAssignments.workforceMemberId, memberId),
          lte(coreMemberRoleAssignments.validFrom, now),
          or(
            isNull(coreMemberRoleAssignments.validUntil),
            gt(coreMemberRoleAssignments.validUntil, now)
          )
        )
      );

    for (const a of assignments) {
      // Check project scope
      if (a.projectId !== null) {
        if (!scope?.projectId || String(a.projectId) !== String(scope.projectId)) {
          continue; // Scope does not match this assignment
        }
      }

      // Check legal entity scope
      if (a.legalEntityId !== null) {
        if (!scope?.legalEntityId || String(a.legalEntityId) !== String(scope.legalEntityId)) {
          continue; // Scope does not match this assignment
        }
      }

      // Fetch role permissions
      const rolePerms = await db
        .select({
          permissionKey: coreRolePermissions.permissionKey,
          effect: coreRolePermissions.effect,
          conditions: coreRolePermissions.conditions,
        })
        .from(coreRolePermissions)
        .where(eq(coreRolePermissions.roleId, a.roleId));

      const convertedRules: PermissionRule[] = rolePerms.map((rp) => ({
        id: `${a.roleId}:${rp.permissionKey}`,
        effect: rp.effect as PermissionEffect,
        permissionKey: rp.permissionKey,
        conditions: (rp.conditions as any) || {},
      }));

      const bestInRole = matchBestRuleInRole(convertedRules, action, facts);
      if (bestInRole) {
        applicableRules.push(bestInRole);
        matchedRuleIds.push(bestInRole.id);
      }
    }
  }

  if (applicableRules.length > 0) {
    const combinedEffect = combinePermissionRules(applicableRules);
    return {
      effect: combinedEffect,
      reasonCodes: [combinedEffect],
      policyVersion,
      matchedRuleIds,
      approvalRequired: combinedEffect === "REQUIRE_APPROVAL",
    };
  }

  // If no specific role assignments matched:
  // If user is founder/co-founder, grant default ALLOW
  if (isFounder) {
    return {
      effect: "ALLOW",
      reasonCodes: ["FOUNDER_DEFAULT_ALLOW"],
      policyVersion,
      matchedRuleIds: ["system:founder"],
      approvalRequired: false,
    };
  }

  return {
    effect: "DENY",
    reasonCodes: ["NO_MATCHING_RULE"],
    policyVersion,
    matchedRuleIds: [],
    approvalRequired: false,
  };
}

export interface BusinessPolicyRuleGroup {
  rules: PermissionRule[];
}

export interface BusinessPolicyRuleSet {
  isFounder: boolean;
  policyVersion: number;
  ruleGroups: BusinessPolicyRuleGroup[];
}

/**
 * IA02 phần 2 — trả RAW rule set (không evaluate 1 action cụ thể) để
 * CapabilityGateway phía Python (apps/cosa) có thể tự evaluate đồng bộ
 * ngay trong hot path tool-call, không cần gọi HTTP mỗi lần thực thi
 * capability (điều này KHÔNG khả thi — evaluate() trong gateway chạy đồng
 * bộ). Rules được nhóm theo TỪNG role assignment (không flatten phẳng)
 * để bên gọi có thể tái tạo đúng thuật toán combinePermissionRules gốc:
 * matchBestRuleInRole riêng cho từng role rồi combine kết quả across roles
 * — flatten phẳng trước rồi match 1 lần có thể chọn nhầm 1 rule cụ thể
 * hơn từ role A trong khi role B có rule cùng độ cụ thể nhưng effect khác
 * (vd. DENY) mà đáng ra phải thắng theo combinePermissionRules.
 *
 * LƯU Ý phạm vi (đã XÁC NHẬN qua FK constraint thật, không chỉ suy đoán):
 * coreRolePermissions.permission_key có FK tới permission_definitions
 * (permission-catalog.ts, PERMISSION_CATALOG) — CHỈ những key đã đăng ký
 * trong catalog mới insert được. Muốn 1 rule áp dụng cho 1 capability_id cụ
 * thể phía Python agent (vd. "finance.write.transaction_record"), key đó
 * phải được thêm vào PERMISSION_CATALOG + migration seed permission_definitions
 * TRƯỚC — không thể tự ý dùng string tuỳ ý ở coreRolePermissions ngay cả
 * khi workspace muốn. Hàm này KHÔNG tự thêm catalog entry mới hay suy đoán
 * mapping capability_id -> permissionKey; chỉ trả nguyên rule đã cấu hình
 * hợp lệ theo catalog hiện có. Việc mở rộng catalog để phủ capability_id
 * phía agent là quyết định sản phẩm/kiến trúc riêng (catalog hiện chỉ có
 * các key nghiệp vụ cấp cao như "finance.request.approve", không có key
 * theo capability_id chi tiết của từng Python capability).
 */
export async function getBusinessPolicyRulesForMemberService(p: {
  workspaceId: bigint;
  workforceMemberId?: bigint;
  projectId?: bigint;
  legalEntityId?: bigint;
}): Promise<BusinessPolicyRuleSet> {
  const policyVersion = await getLatestPolicyVersion(p.workspaceId);

  let isFounder = false;
  if (p.workforceMemberId) {
    const { identityWorkforceMembers } = await import("../../shared/db/schema/identity");
    const [member] = await db
      .select({ humanUserId: identityWorkforceMembers.humanUserId })
      .from(identityWorkforceMembers)
      .where(
        and(
          eq(identityWorkforceMembers.id, p.workforceMemberId),
          eq(identityWorkforceMembers.workspaceId, p.workspaceId)
        )
      );
    if (member?.humanUserId) {
      const [membership] = await db
        .select({ role: identityWorkspaceMemberships.role })
        .from(identityWorkspaceMemberships)
        .where(
          and(
            eq(identityWorkspaceMemberships.workspaceId, p.workspaceId),
            eq(identityWorkspaceMemberships.userId, member.humanUserId)
          )
        );
      isFounder = ["founder", "co-founder"].includes((membership?.role || "").toLowerCase());
    }
  }

  const ruleGroups: BusinessPolicyRuleGroup[] = [];

  if (p.workforceMemberId) {
    const now = new Date();
    const assignments = await db
      .select({
        assignmentId: coreMemberRoleAssignments.id,
        roleId: coreMemberRoleAssignments.roleId,
        projectId: coreMemberRoleAssignments.projectId,
        legalEntityId: coreMemberRoleAssignments.legalEntityId,
      })
      .from(coreMemberRoleAssignments)
      .where(
        and(
          eq(coreMemberRoleAssignments.workspaceId, p.workspaceId),
          eq(coreMemberRoleAssignments.workforceMemberId, p.workforceMemberId),
          lte(coreMemberRoleAssignments.validFrom, now),
          or(
            isNull(coreMemberRoleAssignments.validUntil),
            gt(coreMemberRoleAssignments.validUntil, now)
          )
        )
      );

    for (const a of assignments) {
      if (a.projectId !== null) {
        if (!p.projectId || String(a.projectId) !== String(p.projectId)) continue;
      }
      if (a.legalEntityId !== null) {
        if (!p.legalEntityId || String(a.legalEntityId) !== String(p.legalEntityId)) continue;
      }

      const rolePerms = await db
        .select({
          permissionKey: coreRolePermissions.permissionKey,
          effect: coreRolePermissions.effect,
          conditions: coreRolePermissions.conditions,
        })
        .from(coreRolePermissions)
        .where(eq(coreRolePermissions.roleId, a.roleId));

      ruleGroups.push({
        rules: rolePerms.map((rp) => ({
          id: `${a.roleId}:${rp.permissionKey}`,
          effect: rp.effect as PermissionEffect,
          permissionKey: rp.permissionKey,
          conditions: (rp.conditions as any) || {},
        })),
      });
    }
  }

  return { isFounder, policyVersion, ruleGroups };
}

export async function requireBusinessAction(
  ctx: TenantContext,
  action: string,
  scope?: ResourceScope,
  facts?: Record<string, any>
): Promise<RuleDecision> {
  const decision = await authorizeBusinessAction(ctx, action, scope, facts);

  if (decision.effect === "DENY") {
    throw APIError.permissionDenied(
      `Permission denied for action '${action}' (reasons: ${decision.reasonCodes.join(", ")})`
    );
  }

  if (decision.effect === "REQUIRE_APPROVAL") {
    const err = APIError.failedPrecondition(
      `Approval required for action '${action}'`
    );
    (err as any).code = "APPROVAL_REQUIRED";
    throw err;
  }

  return decision;
}
