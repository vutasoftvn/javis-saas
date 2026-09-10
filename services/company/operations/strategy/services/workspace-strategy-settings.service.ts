import { and, eq } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import { workspaceStrategySettings } from "../../../shared/db/schema/strategy";
import type { TenantContext } from "../../../shared/types/tenant_context";

export type MidCycleReviewPolicy = "OFF" | "AUTO" | "CUSTOM";
export type ApprovalPolicy = "FOUNDER_ONLY" | "DELEGATED_APPROVER";

export const VALID_MID_CYCLE_REVIEW_POLICIES = ["OFF", "AUTO", "CUSTOM"] as const;
export const VALID_APPROVAL_POLICIES = ["FOUNDER_ONLY", "DELEGATED_APPROVER"] as const;
export const VALID_AGENT_PROFILES = [
  "operations",
  "finance",
  "marketing",
  "research_intelligence",
  "strategy",
] as const;

// Cấu hình vận hành cấp workspace cho operating loop (đã bỏ nhánh framework
// strategy-method trong clean-slate) — chỉ giữ config vận hành.
export interface WorkspaceStrategySettings {
  workspaceId: string;
  weeklyReviewEnabled: boolean;
  midCycleReviewPolicy: MidCycleReviewPolicy;
  endCycleReviewEnabled: boolean;
  allowedAgentProfiles: string[];
  approvalPolicy: ApprovalPolicy;
  revision: number;
  updatedByMemberId?: string | null;
  updatedAt?: string;
}

export const DEFAULT_WORKSPACE_STRATEGY_SETTINGS: Omit<
  WorkspaceStrategySettings,
  "workspaceId"
> = {
  weeklyReviewEnabled: true,
  midCycleReviewPolicy: "AUTO",
  endCycleReviewEnabled: true,
  allowedAgentProfiles: [],
  approvalPolicy: "FOUNDER_ONLY",
  revision: 1,
  updatedByMemberId: null,
  updatedAt: new Date(0).toISOString(),
};

export function validateStrategySettings(
  settings: Partial<WorkspaceStrategySettings>
): void {
  if (settings.midCycleReviewPolicy !== undefined) {
    if (!VALID_MID_CYCLE_REVIEW_POLICIES.includes(settings.midCycleReviewPolicy as any)) {
      throw APIError.invalidArgument(
        `Invalid midCycleReviewPolicy: '${settings.midCycleReviewPolicy}'. Must be one of: ${VALID_MID_CYCLE_REVIEW_POLICIES.join(", ")}`
      );
    }
  }

  if (settings.approvalPolicy !== undefined) {
    if (!VALID_APPROVAL_POLICIES.includes(settings.approvalPolicy as any)) {
      throw APIError.invalidArgument(
        `Invalid approvalPolicy: '${settings.approvalPolicy}'. Must be one of: ${VALID_APPROVAL_POLICIES.join(", ")}`
      );
    }
  }

  if (settings.allowedAgentProfiles !== undefined) {
    const seenProfiles = new Set<string>();
    for (const profile of settings.allowedAgentProfiles) {
      if (!VALID_AGENT_PROFILES.includes(profile as any)) {
        throw APIError.invalidArgument(
          `Unknown agent profile: '${profile}'. Must be one of: ${VALID_AGENT_PROFILES.join(", ")}`
        );
      }
      if (seenProfiles.has(profile)) {
        throw APIError.invalidArgument(`Duplicate agent profile: '${profile}'`);
      }
      seenProfiles.add(profile);
    }
  }
}

export function validatePolicyOverride(
  workspaceSettings: WorkspaceStrategySettings,
  override: Partial<WorkspaceStrategySettings>
): void {
  validateStrategySettings(override);

  // Override cấp project/cycle không được nới lỏng policy workspace.
  if (
    workspaceSettings.approvalPolicy === "FOUNDER_ONLY" &&
    override.approvalPolicy === "DELEGATED_APPROVER"
  ) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot relax workspace approvalPolicy 'FOUNDER_ONLY' to 'DELEGATED_APPROVER'"
    );
  }

  if (workspaceSettings.weeklyReviewEnabled && override.weeklyReviewEnabled === false) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot disable weekly reviews when enabled at workspace level"
    );
  }

  if (workspaceSettings.endCycleReviewEnabled && override.endCycleReviewEnabled === false) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot disable end cycle reviews when enabled at workspace level"
    );
  }

  if (
    workspaceSettings.midCycleReviewPolicy === "AUTO" &&
    override.midCycleReviewPolicy === "OFF"
  ) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot turn off mid-cycle reviews when auto-scheduled at workspace level"
    );
  }
}

export async function getWorkspaceStrategySettings(
  workspaceId: bigint | string
): Promise<WorkspaceStrategySettings> {
  const wsId = BigInt(workspaceId);

  const [row] = await db
    .select()
    .from(workspaceStrategySettings)
    .where(eq(workspaceStrategySettings.workspaceId, wsId))
    .limit(1);

  if (!row) {
    return {
      workspaceId: String(wsId),
      ...DEFAULT_WORKSPACE_STRATEGY_SETTINGS,
    };
  }

  return {
    workspaceId: row.workspaceId.toString(),
    weeklyReviewEnabled: row.weeklyReviewEnabled,
    midCycleReviewPolicy: row.midCycleReviewPolicy as MidCycleReviewPolicy,
    endCycleReviewEnabled: row.endCycleReviewEnabled,
    allowedAgentProfiles: (row.allowedAgentProfiles || []) as string[],
    approvalPolicy: row.approvalPolicy as ApprovalPolicy,
    revision: row.revision,
    updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
    updatedAt: row.updatedAt ? row.updatedAt.toISOString() : undefined,
  };
}

export interface UpdateWorkspaceStrategySettingsInput {
  workspaceId: string;
  weeklyReviewEnabled?: boolean;
  midCycleReviewPolicy?: MidCycleReviewPolicy;
  endCycleReviewEnabled?: boolean;
  allowedAgentProfiles?: string[];
  approvalPolicy?: ApprovalPolicy;
  expectedRevision?: number;
}

function projectRow(row: typeof workspaceStrategySettings.$inferSelect): WorkspaceStrategySettings {
  return {
    workspaceId: row.workspaceId.toString(),
    weeklyReviewEnabled: row.weeklyReviewEnabled,
    midCycleReviewPolicy: row.midCycleReviewPolicy as MidCycleReviewPolicy,
    endCycleReviewEnabled: row.endCycleReviewEnabled,
    allowedAgentProfiles: (row.allowedAgentProfiles || []) as string[],
    approvalPolicy: row.approvalPolicy as ApprovalPolicy,
    revision: row.revision,
    updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function updateWorkspaceStrategySettings(
  ctx: TenantContext,
  params: UpdateWorkspaceStrategySettingsInput
): Promise<WorkspaceStrategySettings> {
  const wsId = BigInt(params.workspaceId);

  const [existing] = await db
    .select()
    .from(workspaceStrategySettings)
    .where(eq(workspaceStrategySettings.workspaceId, wsId))
    .limit(1);

  const currentRevision = existing ? existing.revision : 1;

  if (
    params.expectedRevision !== undefined &&
    params.expectedRevision !== currentRevision
  ) {
    throw APIError.aborted(
      `Settings revision conflict: expected revision ${params.expectedRevision}, but current is ${currentRevision}`
    );
  }

  const merged: WorkspaceStrategySettings = {
    workspaceId: String(wsId),
    weeklyReviewEnabled:
      params.weeklyReviewEnabled ??
      (existing ? existing.weeklyReviewEnabled : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.weeklyReviewEnabled),
    midCycleReviewPolicy:
      params.midCycleReviewPolicy ??
      (existing ? (existing.midCycleReviewPolicy as MidCycleReviewPolicy) : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.midCycleReviewPolicy),
    endCycleReviewEnabled:
      params.endCycleReviewEnabled ??
      (existing ? existing.endCycleReviewEnabled : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.endCycleReviewEnabled),
    allowedAgentProfiles:
      params.allowedAgentProfiles ??
      (existing ? (existing.allowedAgentProfiles as string[]) : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.allowedAgentProfiles),
    approvalPolicy:
      params.approvalPolicy ??
      (existing ? (existing.approvalPolicy as ApprovalPolicy) : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.approvalPolicy),
    revision: existing ? existing.revision + 1 : 1,
    updatedByMemberId: ctx.workforceMemberId ? String(ctx.workforceMemberId) : null,
  };

  validateStrategySettings(merged);

  const updatedByMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const now = new Date();

  if (existing) {
    const [row] = await db
      .update(workspaceStrategySettings)
      .set({
        weeklyReviewEnabled: merged.weeklyReviewEnabled,
        midCycleReviewPolicy: merged.midCycleReviewPolicy,
        endCycleReviewEnabled: merged.endCycleReviewEnabled,
        allowedAgentProfiles: merged.allowedAgentProfiles,
        approvalPolicy: merged.approvalPolicy,
        revision: merged.revision,
        updatedByMemberId,
        updatedAt: now,
      })
      .where(
        and(
          eq(workspaceStrategySettings.workspaceId, wsId),
          eq(workspaceStrategySettings.revision, currentRevision)
        )
      )
      .returning();

    if (!row) {
      throw APIError.aborted(
        `Settings revision conflict: expected revision ${currentRevision}, but it changed before the update completed`
      );
    }

    return projectRow(row);
  }

  const [row] = await db
    .insert(workspaceStrategySettings)
    .values({
      workspaceId: wsId,
      weeklyReviewEnabled: merged.weeklyReviewEnabled,
      midCycleReviewPolicy: merged.midCycleReviewPolicy,
      endCycleReviewEnabled: merged.endCycleReviewEnabled,
      allowedAgentProfiles: merged.allowedAgentProfiles,
      approvalPolicy: merged.approvalPolicy,
      revision: 1,
      updatedByMemberId,
      updatedAt: now,
    })
    .onConflictDoNothing({ target: workspaceStrategySettings.workspaceId })
    .returning();

  if (!row) {
    throw APIError.aborted(
      "Settings revision conflict: settings were created by another request"
    );
  }

  return projectRow(row);
}
