import { APIError } from "encore.dev/api";
import { eq, and, desc, sql } from "drizzle-orm";
import { createHash } from "node:crypto";
import { db } from "../models/db";
import {
  corePermissionDefinitions,
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  coreWorkspacePolicyVersions,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";
import { PERMISSION_CATALOG, isKnownPermission } from "./permission-catalog";
import {
  authorizeBusinessAction,
  getLatestPolicyVersion,
  ResourceScope,
  RuleDecision,
} from "./business-authorization.service";
import { requireFounderCommand } from "./command-authority.service";

export type MutationKind = "ASSIGN_ROLE" | "REVOKE_ROLE" | "SET_ROLE_PERMISSION";

export interface RoleAssignmentMutation {
  kind: "ASSIGN_ROLE";
  memberId: string;
  roleId: string;
  scope?: {
    workspaceId?: string;
    projectId?: string;
    legalEntityId?: string;
  };
  validUntil?: string;
}

export interface RevokeRoleMutation {
  kind: "REVOKE_ROLE";
  assignmentId: string;
}

export interface SetRolePermissionMutation {
  kind: "SET_ROLE_PERMISSION";
  roleId: string;
  permissionKey: string;
  effect: "ALLOW" | "DENY" | "REQUIRE_APPROVAL";
  conditions?: Record<string, any>;
}

export type PermissionMutation =
  | RoleAssignmentMutation
  | RevokeRoleMutation
  | SetRolePermissionMutation;

export interface UpdatePermissionsRequest {
  expectedVersion: number;
  reason: string;
  mutations: PermissionMutation[];
}

export interface SimulatePermissionsRequest {
  action: string;
  memberId?: string;
  scope?: ResourceScope;
  facts?: Record<string, any>;
}

export interface PermissionDefinitionItem {
  permissionKey: string;
  domain: string;
  description: string | null;
}

export interface WorkspaceRoleItem {
  id: string;
  roleKey: string;
  name: string;
  isSystem: boolean;
  permissions: Array<{
    permissionKey: string;
    effect: string;
    conditions: Record<string, any>;
  }>;
}

export interface MemberRoleAssignmentItem {
  id: string;
  workforceMemberId: string;
  roleId: string;
  roleKey?: string;
  roleName?: string;
  projectId: string | null;
  legalEntityId: string | null;
  validFrom: string;
  validUntil: string | null;
}

export interface GetPermissionsResponse {
  catalog: PermissionDefinitionItem[];
  roles: WorkspaceRoleItem[];
  assignments: MemberRoleAssignmentItem[];
  version: number;
  effectivePermissions: Record<string, string>;
}

export async function getPermissionsService(
  ctx: TenantContext
): Promise<GetPermissionsResponse> {
  const wsId = BigInt(ctx.workspaceId);
  const version = await getLatestPolicyVersion(wsId);

  // 1. Catalog
  const dbCatalog = await db.select().from(corePermissionDefinitions);
  const catalog: PermissionDefinitionItem[] =
    dbCatalog.length > 0
      ? dbCatalog.map((c) => ({
          permissionKey: c.permissionKey,
          domain: c.domain,
          description: c.description,
        }))
      : PERMISSION_CATALOG.map((c) => ({
          permissionKey: c.permissionKey,
          domain: c.domain,
          description: c.description,
        }));

  // 2. Roles
  const roles = await db
    .select()
    .from(coreWorkspaceRoles)
    .where(eq(coreWorkspaceRoles.workspaceId, wsId));

  const roleIds = roles.map((r) => r.id);
  const rolePermissionsMap = new Map<
    string,
    Array<{ permissionKey: string; effect: string; conditions: Record<string, any> }>
  >();

  if (roleIds.length > 0) {
    const permissions = await db.select().from(coreRolePermissions);
    for (const p of permissions) {
      if (!rolePermissionsMap.has(p.roleId)) {
        rolePermissionsMap.set(p.roleId, []);
      }
      rolePermissionsMap.get(p.roleId)!.push({
        permissionKey: p.permissionKey,
        effect: p.effect,
        conditions: (p.conditions as any) || {},
      });
    }
  }

  const roleItems: WorkspaceRoleItem[] = roles.map((r) => ({
    id: r.id,
    roleKey: r.roleKey,
    name: r.name,
    isSystem: r.isSystem,
    permissions: rolePermissionsMap.get(r.id) || [],
  }));

  // 3. Assignments
  const assignments = await db
    .select({
      id: coreMemberRoleAssignments.id,
      workforceMemberId: coreMemberRoleAssignments.workforceMemberId,
      roleId: coreMemberRoleAssignments.roleId,
      projectId: coreMemberRoleAssignments.projectId,
      legalEntityId: coreMemberRoleAssignments.legalEntityId,
      validFrom: coreMemberRoleAssignments.validFrom,
      validUntil: coreMemberRoleAssignments.validUntil,
      roleKey: coreWorkspaceRoles.roleKey,
      roleName: coreWorkspaceRoles.name,
    })
    .from(coreMemberRoleAssignments)
    .innerJoin(
      coreWorkspaceRoles,
      eq(coreMemberRoleAssignments.roleId, coreWorkspaceRoles.id)
    )
    .where(eq(coreMemberRoleAssignments.workspaceId, wsId));

  const assignmentItems: MemberRoleAssignmentItem[] = assignments.map((a) => ({
    id: a.id,
    workforceMemberId: String(a.workforceMemberId),
    roleId: a.roleId,
    roleKey: a.roleKey,
    roleName: a.roleName,
    projectId: a.projectId ? String(a.projectId) : null,
    legalEntityId: a.legalEntityId ? String(a.legalEntityId) : null,
    validFrom: a.validFrom.toISOString(),
    validUntil: a.validUntil ? a.validUntil.toISOString() : null,
  }));

  // 4. Effective permissions for caller
  const effectivePermissions: Record<string, string> = {};
  for (const c of catalog) {
    const decision = await authorizeBusinessAction(ctx, c.permissionKey, {
      workspaceId: ctx.workspaceId,
    });
    effectivePermissions[c.permissionKey] = decision.effect;
  }

  return {
    catalog,
    roles: roleItems,
    assignments: assignmentItems,
    version,
    effectivePermissions,
  };
}

export async function simulatePermissionsService(
  ctx: TenantContext,
  req: SimulatePermissionsRequest
): Promise<{
  decision: RuleDecision;
  impacts: Array<{
    memberId: string;
    action: string;
    effect: string;
    reason: string;
  }>;
}> {
  const wsId = BigInt(ctx.workspaceId);
  const targetMemberId = req.memberId || ctx.workforceMemberId;

  // Giả lập TenantContext
  const simCtx: TenantContext = {
    workspaceId: ctx.workspaceId,
    userId: ctx.userId,
    workforceMemberId: targetMemberId,
    membershipRole:
      String(targetMemberId) === String(ctx.workforceMemberId)
        ? ctx.membershipRole
        : "member",
    permissions: [],
    correlationId: ctx.correlationId,
  };

  const decision = await authorizeBusinessAction(
    simCtx,
    req.action,
    { workspaceId: ctx.workspaceId, ...req.scope },
    req.facts
  );

  const impacts = [
    {
      memberId: targetMemberId || "unknown",
      action: req.action,
      effect: decision.effect,
      reason: decision.reasonCodes.join(", ") || "Evaluated by policy",
    },
  ];

  return {
    decision,
    impacts,
  };
}

export async function updatePermissionsService(
  ctx: TenantContext,
  req: UpdatePermissionsRequest
): Promise<{ success: boolean; version: number }> {
  // Chỉ founder/co-founder được manage permissions
  requireFounderCommand(ctx, "permissions.manage");

  const wsId = BigInt(ctx.workspaceId);
  const currentVersion = await getLatestPolicyVersion(wsId);

  if (req.expectedVersion !== currentVersion) {
    throw APIError.failedPrecondition(
      `VERSION_CONFLICT: Expected version ${req.expectedVersion} but current is ${currentVersion}`
    );
  }

  return await db.transaction(async (tx) => {
    for (const m of req.mutations) {
      if (m.kind === "SET_ROLE_PERMISSION") {
        if (!isKnownPermission(m.permissionKey)) {
          throw APIError.invalidArgument(`Unknown permission key: ${m.permissionKey}`);
        }
        // Verify role belongs to workspace
        const [role] = await tx
          .select()
          .from(coreWorkspaceRoles)
          .where(
            and(
              eq(coreWorkspaceRoles.id, m.roleId),
              eq(coreWorkspaceRoles.workspaceId, wsId)
            )
          )
          .limit(1);

        if (!role) {
          throw APIError.notFound(`Role ${m.roleId} not found in workspace`);
        }

        // Upsert role permission. IA15: khi caller chỉ đổi effect và KHÔNG
        // gửi conditions (vd Flutter chỉ PUT effect), bản update trước đây
        // luôn ghi đè conditions thành {} — xóa mất maxAmountMinor/currency
        // đang áp dụng của rule cũ. Row đã tồn tại (conflict) mà thiếu
        // conditions trong payload thì GIỮ NGUYÊN conditions cũ (tham chiếu
        // thẳng cột hiện có trong SET, không phải giá trị ứng dụng tự suy
        // diễn) — chỉ row MỚI (chưa tồn tại) mới mặc định {}.
        await tx
          .insert(coreRolePermissions)
          .values({
            roleId: m.roleId,
            permissionKey: m.permissionKey,
            effect: m.effect,
            conditions: m.conditions ?? {},
          })
          .onConflictDoUpdate({
            target: [coreRolePermissions.roleId, coreRolePermissions.permissionKey],
            set: {
              effect: m.effect,
              conditions:
                m.conditions !== undefined ? m.conditions : sql`${coreRolePermissions.conditions}`,
            },
          });
      } else if (m.kind === "ASSIGN_ROLE") {
        // Verify role
        const [role] = await tx
          .select()
          .from(coreWorkspaceRoles)
          .where(
            and(
              eq(coreWorkspaceRoles.id, m.roleId),
              eq(coreWorkspaceRoles.workspaceId, wsId)
            )
          )
          .limit(1);

        if (!role) {
          throw APIError.notFound(`Role ${m.roleId} not found in workspace`);
        }

        // Verify member belongs to workspace
        const memberId = BigInt(m.memberId);
        const [member] = await tx
          .select()
          .from(identityWorkforceMembers)
          .where(
            and(
              eq(identityWorkforceMembers.id, memberId),
              eq(identityWorkforceMembers.workspaceId, wsId)
            )
          )
          .limit(1);

        if (!member) {
          throw APIError.notFound(`Member ${m.memberId} not found in workspace`);
        }

        if (role.allowedMemberTypes && role.allowedMemberTypes.length > 0) {
          if (!role.allowedMemberTypes.includes(member.memberType)) {
            throw APIError.invalidArgument(
              `ROLE_MEMBER_TYPE_MISMATCH: Member type ${member.memberType} is not allowed for role ${role.name}`
            );
          }
        }

        await tx.insert(coreMemberRoleAssignments).values({
          workspaceId: wsId,
          workforceMemberId: memberId,
          roleId: m.roleId,
          projectId: m.scope?.projectId ? BigInt(m.scope.projectId) : null,
          legalEntityId: m.scope?.legalEntityId ? BigInt(m.scope.legalEntityId) : null,
          validUntil: m.validUntil ? new Date(m.validUntil) : null,
        });
      } else if (m.kind === "REVOKE_ROLE") {
        // Find existing assignment
        const [assignment] = await tx
          .select({
            id: coreMemberRoleAssignments.id,
            roleId: coreMemberRoleAssignments.roleId,
            roleKey: coreWorkspaceRoles.roleKey,
          })
          .from(coreMemberRoleAssignments)
          .innerJoin(
            coreWorkspaceRoles,
            eq(coreMemberRoleAssignments.roleId, coreWorkspaceRoles.id)
          )
          .where(
            and(
              eq(coreMemberRoleAssignments.id, m.assignmentId),
              eq(coreMemberRoleAssignments.workspaceId, wsId)
            )
          )
          .limit(1);

        if (!assignment) {
          throw APIError.notFound(`Assignment ${m.assignmentId} not found`);
        }

        // Nếu là role founder, kiểm tra xem có phải assignment founder cuối cùng không
        if (assignment.roleKey === "founder") {
          const founderAssignments = await tx
            .select({ id: coreMemberRoleAssignments.id })
            .from(coreMemberRoleAssignments)
            .innerJoin(
              coreWorkspaceRoles,
              eq(coreMemberRoleAssignments.roleId, coreWorkspaceRoles.id)
            )
            .where(
              and(
                eq(coreMemberRoleAssignments.workspaceId, wsId),
                eq(coreWorkspaceRoles.roleKey, "founder")
              )
            );

          if (founderAssignments.length <= 1) {
            throw APIError.failedPrecondition(
              "CANNOT_REVOKE_LAST_FOUNDER: Không thể thu hồi quyền quản trị của founder cuối cùng"
            );
          }
        }

        await tx
          .delete(coreMemberRoleAssignments)
          .where(eq(coreMemberRoleAssignments.id, m.assignmentId));
      }
    }

    const nextVersion = currentVersion + 1;
    const policyHash = createHash("sha256")
      .update(
        JSON.stringify({
          wsId: wsId.toString(),
          nextVersion,
          mutations: req.mutations,
          reason: req.reason,
        })
      )
      .digest("hex");

    await tx.insert(coreWorkspacePolicyVersions).values({
      workspaceId: wsId,
      version: nextVersion,
      policyHash,
      actorMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      reason: req.reason,
    });

    return { success: true, version: nextVersion };
  });
}
