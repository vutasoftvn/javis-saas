import { and, eq } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import { workspaceStrategySettings } from "../../../shared/db/schema/strategy";
import type { TenantContext } from "../../../shared/types/tenant_context";

export type StrategyMethod = "CLASSIC" | "BSC_FILTER";
export type BscMode = "OFF" | "OPTIONAL" | "REQUIRED";
export type BscPerspective =
  | "FINANCIAL"
  | "CUSTOMER"
  | "INTERNAL_PROCESS"
  | "LEARNING_AND_GROWTH";
export type MidCycleReviewPolicy = "OFF" | "AUTO" | "CUSTOM";
export type ApprovalPolicy = "FOUNDER_ONLY" | "DELEGATED_APPROVER";

export const VALID_STRATEGY_METHODS = ["CLASSIC", "BSC_FILTER"] as const;
export const VALID_BSC_MODES = ["OFF", "OPTIONAL", "REQUIRED"] as const;
export const VALID_BSC_PERSPECTIVES = [
  "FINANCIAL",
  "CUSTOMER",
  "INTERNAL_PROCESS",
  "LEARNING_AND_GROWTH",
] as const;
export const VALID_MID_CYCLE_REVIEW_POLICIES = ["OFF", "AUTO", "CUSTOM"] as const;
export const VALID_APPROVAL_POLICIES = ["FOUNDER_ONLY", "DELEGATED_APPROVER"] as const;
export const VALID_AGENT_PROFILES = [
  "operations",
  "finance",
  "marketing",
  "research_intelligence",
  "strategy",
] as const;

export interface WorkspaceStrategySettings {
  workspaceId: string;
  strategyMethod: StrategyMethod;
  bscMode: BscMode;
  enabledBscPerspectives: BscPerspective[];
  towsSelectionLimit: number;
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
  strategyMethod: "CLASSIC",
  bscMode: "OFF",
  enabledBscPerspectives: [],
  towsSelectionLimit: 1,
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
  if (settings.strategyMethod !== undefined) {
    if (!VALID_STRATEGY_METHODS.includes(settings.strategyMethod as any)) {
      throw APIError.invalidArgument(
        `Invalid strategyMethod: '${settings.strategyMethod}'. Must be one of: ${VALID_STRATEGY_METHODS.join(", ")}`
      );
    }
  }

  if (settings.bscMode !== undefined) {
    if (!VALID_BSC_MODES.includes(settings.bscMode as any)) {
      throw APIError.invalidArgument(
        `Invalid bscMode: '${settings.bscMode}'. Must be one of: ${VALID_BSC_MODES.join(", ")}`
      );
    }
  }

  if (settings.enabledBscPerspectives !== undefined) {
    const seen = new Set<string>();
    for (const p of settings.enabledBscPerspectives) {
      if (!VALID_BSC_PERSPECTIVES.includes(p as any)) {
        throw APIError.invalidArgument(
          `Invalid BSC perspective: '${p}'. Must be one of: ${VALID_BSC_PERSPECTIVES.join(", ")}`
        );
      }
      if (seen.has(p)) {
        throw APIError.invalidArgument(`Duplicate BSC perspective: '${p}'`);
      }
      seen.add(p);
    }
  }

  if (settings.towsSelectionLimit !== undefined) {
    if (
      !Number.isInteger(settings.towsSelectionLimit) ||
      settings.towsSelectionLimit < 1 ||
      settings.towsSelectionLimit > 2
    ) {
      throw APIError.invalidArgument("towsSelectionLimit must be an integer between 1 and 2");
    }
  }

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

  // Consistency checks
  const strategyMethod = settings.strategyMethod;
  const bscMode = settings.bscMode;
  const perspectives = settings.enabledBscPerspectives;

  if (strategyMethod === "BSC_FILTER" && bscMode === "OFF") {
    throw APIError.invalidArgument(
      "strategyMethod 'BSC_FILTER' cannot be combined with bscMode 'OFF'"
    );
  }

  if (bscMode === "REQUIRED" && (!perspectives || perspectives.length === 0)) {
    throw APIError.invalidArgument(
      "enabledBscPerspectives cannot be empty when bscMode is REQUIRED"
    );
  }
}

const BSC_MODE_STRICTNESS: Record<BscMode, number> = {
  OFF: 0,
  OPTIONAL: 1,
  REQUIRED: 2,
};

export function validatePolicyOverride(
  workspaceSettings: WorkspaceStrategySettings,
  override: Partial<WorkspaceStrategySettings>
): void {
  // Validate basic shape
  validateStrategySettings(override);

  // An override cannot relax the workspace policy
  if (override.bscMode !== undefined) {
    const wsStrictness = BSC_MODE_STRICTNESS[workspaceSettings.bscMode];
    const overrideStrictness = BSC_MODE_STRICTNESS[override.bscMode];
    if (overrideStrictness < wsStrictness) {
      throw APIError.invalidArgument(
        `Project/cycle strategy policy cannot relax workspace BSC mode from '${workspaceSettings.bscMode}' to '${override.bscMode}'`
      );
    }
  }

  if (
    workspaceSettings.strategyMethod === "BSC_FILTER" &&
    override.strategyMethod === "CLASSIC"
  ) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot relax workspace strategyMethod 'BSC_FILTER' to 'CLASSIC'"
    );
  }

  if (
    workspaceSettings.approvalPolicy === "FOUNDER_ONLY" &&
    override.approvalPolicy === "DELEGATED_APPROVER"
  ) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot relax workspace approvalPolicy 'FOUNDER_ONLY' to 'DELEGATED_APPROVER'"
    );
  }

  if (
    workspaceSettings.towsSelectionLimit === 1 &&
    override.towsSelectionLimit === 2
  ) {
    throw APIError.invalidArgument(
      "Project/cycle strategy policy cannot expand towsSelectionLimit beyond workspace limit of 1"
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

  if (
    override.enabledBscPerspectives &&
    workspaceSettings.enabledBscPerspectives.length > 0
  ) {
    const wsPerspectives = new Set(workspaceSettings.enabledBscPerspectives);
    for (const p of override.enabledBscPerspectives) {
      if (!wsPerspectives.has(p)) {
        throw APIError.invalidArgument(
          `Project/cycle cannot enable BSC perspective '${p}' because it is not enabled in workspace settings`
        );
      }
    }
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
    strategyMethod: row.strategyMethod as StrategyMethod,
    bscMode: row.bscMode as BscMode,
    enabledBscPerspectives: (row.enabledBscPerspectives || []) as BscPerspective[],
    towsSelectionLimit: row.towsSelectionLimit,
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
  strategyMethod?: StrategyMethod;
  bscMode?: BscMode;
  enabledBscPerspectives?: BscPerspective[];
  towsSelectionLimit?: number;
  weeklyReviewEnabled?: boolean;
  midCycleReviewPolicy?: MidCycleReviewPolicy;
  endCycleReviewEnabled?: boolean;
  allowedAgentProfiles?: string[];
  approvalPolicy?: ApprovalPolicy;
  expectedRevision?: number;
}

export async function updateWorkspaceStrategySettings(
  ctx: TenantContext,
  params: UpdateWorkspaceStrategySettingsInput
): Promise<WorkspaceStrategySettings> {
  const wsId = BigInt(params.workspaceId);

  // Fetch current row or default
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
    strategyMethod:
      params.strategyMethod ??
      (existing ? (existing.strategyMethod as StrategyMethod) : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.strategyMethod),
    bscMode:
      params.bscMode ??
      (existing ? (existing.bscMode as BscMode) : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.bscMode),
    enabledBscPerspectives:
      params.enabledBscPerspectives ??
      (existing ? (existing.enabledBscPerspectives as BscPerspective[]) : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.enabledBscPerspectives),
    towsSelectionLimit:
      params.towsSelectionLimit ??
      (existing ? existing.towsSelectionLimit : DEFAULT_WORKSPACE_STRATEGY_SETTINGS.towsSelectionLimit),
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
        strategyMethod: merged.strategyMethod,
        bscMode: merged.bscMode,
        enabledBscPerspectives: merged.enabledBscPerspectives,
        towsSelectionLimit: merged.towsSelectionLimit,
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

    return {
      workspaceId: row.workspaceId.toString(),
      strategyMethod: row.strategyMethod as StrategyMethod,
      bscMode: row.bscMode as BscMode,
      enabledBscPerspectives: row.enabledBscPerspectives as BscPerspective[],
      towsSelectionLimit: row.towsSelectionLimit,
      weeklyReviewEnabled: row.weeklyReviewEnabled,
      midCycleReviewPolicy: row.midCycleReviewPolicy as MidCycleReviewPolicy,
      endCycleReviewEnabled: row.endCycleReviewEnabled,
      allowedAgentProfiles: row.allowedAgentProfiles as string[],
      approvalPolicy: row.approvalPolicy as ApprovalPolicy,
      revision: row.revision,
      updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
      updatedAt: row.updatedAt.toISOString(),
    };
  } else {
    const [row] = await db
      .insert(workspaceStrategySettings)
      .values({
        workspaceId: wsId,
        strategyMethod: merged.strategyMethod,
        bscMode: merged.bscMode,
        enabledBscPerspectives: merged.enabledBscPerspectives,
        towsSelectionLimit: merged.towsSelectionLimit,
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

    return {
      workspaceId: row.workspaceId.toString(),
      strategyMethod: row.strategyMethod as StrategyMethod,
      bscMode: row.bscMode as BscMode,
      enabledBscPerspectives: row.enabledBscPerspectives as BscPerspective[],
      towsSelectionLimit: row.towsSelectionLimit,
      weeklyReviewEnabled: row.weeklyReviewEnabled,
      midCycleReviewPolicy: row.midCycleReviewPolicy as MidCycleReviewPolicy,
      endCycleReviewEnabled: row.endCycleReviewEnabled,
      allowedAgentProfiles: row.allowedAgentProfiles as string[],
      approvalPolicy: row.approvalPolicy as ApprovalPolicy,
      revision: row.revision,
      updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
      updatedAt: row.updatedAt.toISOString(),
    };
  }
}
