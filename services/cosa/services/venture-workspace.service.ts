import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "./snowflake.service";

const {
  plans,
  workspaces,
  workspaceMemberships,
  workspaceLicenses,
  workspaceEntitlements,
  workspaceSyncLogs,
  users,
  profiles,
} = schema;

export interface ProvisionParams {
  ownerUserId: bigint;
  workspaceName: string;
  clientCreationId: string;
  planId?: string;
}

export interface ProvisionResult {
  platformWorkspaceId: string;
  planId: string;
  effectiveFeatures: Record<string, unknown>;
  effectiveLimits: Record<string, unknown>;
}

export interface WorkspaceMembershipInfo {
  platformWorkspaceId: string;
  workspaceName: string;
  userId: string;
  email: string | null;
  displayName: string | null;
  role: string;
  membershipId: string;
  membershipUpdatedAt: string;
}

export interface WorkspaceEntitlementView {
  platformWorkspaceId: string;
  planId: string;
  effectiveLimits: Record<string, unknown>;
  effectiveFeatures: Record<string, unknown>;
  snapshotSignature: string | null;
}

export async function provisionVentureWorkspace(params: ProvisionParams): Promise<ProvisionResult> {
  const name = params.workspaceName.trim() || "Venture Workspace";
  const planId = params.planId ?? "free";

  // Idempotency: nếu clientCreationId đã dùng, trả lại kết quả cũ.
  const [prev] = await db
    .select()
    .from(workspaceSyncLogs)
    .where(eq(workspaceSyncLogs.clientCreationId, params.clientCreationId))
    .limit(1);

  if (prev) {
    const [ent] = await db
      .select()
      .from(workspaceEntitlements)
      .where(eq(workspaceEntitlements.workspaceId, prev.workspaceId))
      .limit(1);

    return {
      platformWorkspaceId: prev.workspaceId.toString(),
      planId: ent?.planId ?? planId,
      effectiveFeatures: (ent?.effectiveFeatures ?? {}) as Record<string, unknown>,
      effectiveLimits: (ent?.effectiveLimits ?? {}) as Record<string, unknown>,
    };
  }

  const [plan] = await db.select().from(plans).where(eq(plans.id, planId)).limit(1);
  if (!plan) {
    throw APIError.internal(`plan ${planId} chưa được seed`);
  }

  const wsId = BigInt(generateSnowflakeStr());
  await db.transaction(async (tx) => {
    await tx.insert(workspaces).values({
      id: wsId,
      workspaceName: name,
      ownerId: params.ownerUserId,
    });
    await tx.insert(workspaceMemberships).values({
      id: BigInt(generateSnowflakeStr()),
      workspaceId: wsId,
      userId: params.ownerUserId,
      roleId: "founder",
    });
    await tx.insert(workspaceLicenses).values({
      id: BigInt(generateSnowflakeStr()),
      workspaceId: wsId,
      planId,
      licenseKey: `wl_${wsId.toString()}`,
      status: "active",
    });
    await tx.insert(workspaceEntitlements).values({
      workspaceId: wsId,
      planId,
      effectiveLimits: plan.defaultLimits as object,
      effectiveFeatures: plan.defaultFeatures as object,
      snapshotSignature: `sig_${wsId.toString()}_${Date.now()}`,
    });
    await tx.insert(workspaceSyncLogs).values({
      id: BigInt(generateSnowflakeStr()),
      workspaceId: wsId,
      clientCreationId: params.clientCreationId,
      syncStatus: "pending",
    });
  });

  return {
    platformWorkspaceId: wsId.toString(),
    planId,
    effectiveFeatures: plan.defaultFeatures as Record<string, unknown>,
    effectiveLimits: plan.defaultLimits as Record<string, unknown>,
  };
}

export async function listWorkspaceMembershipsForUser(userId: bigint): Promise<WorkspaceMembershipInfo[]> {
  const rows = await db
    .select({
      membershipId: workspaceMemberships.id,
      workspaceId: workspaceMemberships.workspaceId,
      roleId: workspaceMemberships.roleId,
      membershipUpdatedAt: workspaceMemberships.updatedAt,
      workspaceName: workspaces.workspaceName,
      userId: users.id,
      email: users.email,
      fullName: profiles.fullName,
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaceMemberships.workspaceId, workspaces.id))
    .innerJoin(users, eq(workspaceMemberships.userId, users.id))
    .leftJoin(profiles, eq(users.id, profiles.id))
    .where(eq(workspaceMemberships.userId, userId));

  return rows.map((r) => ({
    platformWorkspaceId: r.workspaceId.toString(),
    workspaceName: r.workspaceName,
    userId: r.userId.toString(),
    email: r.email,
    displayName: r.fullName,
    role: r.roleId,
    membershipId: r.membershipId.toString(),
    membershipUpdatedAt: r.membershipUpdatedAt.toISOString(),
  }));
}

export async function validateWorkspaceMembership(
  userId: bigint,
  platformWorkspaceId: bigint
): Promise<WorkspaceMembershipInfo | null> {
  const [row] = await db
    .select({
      membershipId: workspaceMemberships.id,
      workspaceId: workspaceMemberships.workspaceId,
      roleId: workspaceMemberships.roleId,
      membershipUpdatedAt: workspaceMemberships.updatedAt,
      workspaceName: workspaces.workspaceName,
      userId: users.id,
      email: users.email,
      fullName: profiles.fullName,
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaceMemberships.workspaceId, workspaces.id))
    .innerJoin(users, eq(workspaceMemberships.userId, users.id))
    .leftJoin(profiles, eq(users.id, profiles.id))
    .where(
      and(
        eq(workspaceMemberships.userId, userId),
        eq(workspaceMemberships.workspaceId, platformWorkspaceId)
      )
    )
    .limit(1);

  if (!row) return null;

  return {
    platformWorkspaceId: row.workspaceId.toString(),
    workspaceName: row.workspaceName,
    userId: row.userId.toString(),
    email: row.email,
    displayName: row.fullName,
    role: row.roleId,
    membershipId: row.membershipId.toString(),
    membershipUpdatedAt: row.membershipUpdatedAt.toISOString(),
  };
}

export async function getWorkspaceEntitlement(platformWorkspaceId: bigint): Promise<WorkspaceEntitlementView> {
  const [row] = await db
    .select()
    .from(workspaceEntitlements)
    .where(eq(workspaceEntitlements.workspaceId, platformWorkspaceId))
    .limit(1);

  if (!row) {
    throw APIError.notFound("Không tìm thấy entitlement của workspace");
  }

  return {
    platformWorkspaceId: row.workspaceId.toString(),
    planId: row.planId,
    effectiveLimits: (row.effectiveLimits ?? {}) as Record<string, unknown>,
    effectiveFeatures: (row.effectiveFeatures ?? {}) as Record<string, unknown>,
    snapshotSignature: row.snapshotSignature,
  };
}

export async function markWorkspaceSynced(platformWorkspaceId: bigint): Promise<void> {
  await db
    .update(workspaceSyncLogs)
    .set({
      syncStatus: "success",
      syncedAt: new Date(),
    })
    .where(eq(workspaceSyncLogs.workspaceId, platformWorkspaceId));
}

