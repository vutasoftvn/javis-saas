import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  engagementAutopilotSettings,
  engagementAutopilotTemplates,
  engagementAutopilotRuns,
} from "../../../shared/db/schema/customer-engagement";

export interface AutopilotSettingsDto {
  workspaceId: string;
  enabled: boolean;
  envAllowlist: string[];
  triggerRuleIds: string[];
  containmentMin: number;
  errorMax: number;
  takeoverMax: number;
  updatedByWorkforceMemberId?: string | null;
  updatedAt?: string;
}

export interface UpdateAutopilotSettingsInput {
  enabled?: boolean;
  envAllowlist?: string[];
  triggerRuleIds?: string[];
  containmentMin?: number;
  errorMax?: number;
  takeoverMax?: number;
}

export class AutopilotSettingsService {
  private db = db;

  async getSettings(workspaceIdInput: bigint | string): Promise<AutopilotSettingsDto> {
    const workspaceId = typeof workspaceIdInput === "bigint" ? workspaceIdInput : BigInt(workspaceIdInput);
    const rows = await this.db
      .select()
      .from(engagementAutopilotSettings)
      .where(eq(engagementAutopilotSettings.workspaceId, workspaceId))
      .limit(1);

    if (rows.length === 0) {
      return {
        workspaceId: workspaceId.toString(),
        enabled: false,
        envAllowlist: ["test", "staging"],
        triggerRuleIds: [],
        containmentMin: 0.8,
        errorMax: 0.05,
        takeoverMax: 0.15,
      };
    }

    const r = rows[0];
    return {
      workspaceId: r.workspaceId.toString(),
      enabled: r.enabled,
      envAllowlist: (r.envAllowlist as string[]) || ["test", "staging"],
      triggerRuleIds: (r.triggerRuleIds as string[]) || [],
      containmentMin: parseFloat(r.containmentMin || "0.8"),
      errorMax: parseFloat(r.errorMax || "0.05"),
      takeoverMax: parseFloat(r.takeoverMax || "0.15"),
      updatedByWorkforceMemberId: r.updatedByWorkforceMemberId ? r.updatedByWorkforceMemberId.toString() : null,
      updatedAt: r.updatedAt.toISOString(),
    };
  }

  async updateSettings(
    workspaceIdInput: bigint | string,
    input: UpdateAutopilotSettingsInput,
    workforceMemberIdInput?: bigint | string | null
  ): Promise<AutopilotSettingsDto> {
    const workspaceId = typeof workspaceIdInput === "bigint" ? workspaceIdInput : BigInt(workspaceIdInput);
    const workforceMemberId = workforceMemberIdInput
      ? typeof workforceMemberIdInput === "bigint"
        ? workforceMemberIdInput
        : BigInt(workforceMemberIdInput)
      : null;
    const currentEnv = process.env.NODE_ENV || process.env.APP_ENV || "development";
    const isProd = currentEnv === "production";

    // ADR Prod-Gate Guard
    if (isProd && (input.enabled === true || input.envAllowlist?.includes("production"))) {
      const allowProdOverride = process.env.ENGAGEMENT_AUTOPILOT_PROD_GATE_OVERRIDE === "true";
      if (!allowProdOverride) {
        throw APIError.failedPrecondition(
          "ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE: Autopilot is currently gated from production environment"
        );
      }
    }

    const current = await this.getSettings(workspaceId);
    const updatedEnabled = input.enabled !== undefined ? input.enabled : current.enabled;
    const updatedEnvAllowlist = input.envAllowlist !== undefined ? input.envAllowlist : current.envAllowlist;
    const updatedTriggerRuleIds = input.triggerRuleIds !== undefined ? input.triggerRuleIds : current.triggerRuleIds;
    const updatedContainmentMin = input.containmentMin !== undefined ? input.containmentMin.toString() : current.containmentMin.toString();
    const updatedErrorMax = input.errorMax !== undefined ? input.errorMax.toString() : current.errorMax.toString();
    const updatedTakeoverMax = input.takeoverMax !== undefined ? input.takeoverMax.toString() : current.takeoverMax.toString();

    await this.db
      .insert(engagementAutopilotSettings)
      .values({
        id: generateSnowflake(),
        workspaceId,
        enabled: updatedEnabled,
        envAllowlist: updatedEnvAllowlist,
        triggerRuleIds: updatedTriggerRuleIds,
        containmentMin: updatedContainmentMin,
        errorMax: updatedErrorMax,
        takeoverMax: updatedTakeoverMax,
        updatedByWorkforceMemberId: workforceMemberId,
        updatedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: engagementAutopilotSettings.workspaceId,
        set: {
          enabled: updatedEnabled,
          envAllowlist: updatedEnvAllowlist,
          triggerRuleIds: updatedTriggerRuleIds,
          containmentMin: updatedContainmentMin,
          errorMax: updatedErrorMax,
          takeoverMax: updatedTakeoverMax,
          updatedByWorkforceMemberId: workforceMemberId,
          updatedAt: new Date(),
        },
      });

    return this.getSettings(workspaceId);
  }

  async emergencyKillSwitch(
    workspaceIdInput: bigint | string,
    workforceMemberIdInput?: bigint | string | null
  ): Promise<AutopilotSettingsDto> {
    const workspaceId = typeof workspaceIdInput === "bigint" ? workspaceIdInput : BigInt(workspaceIdInput);
    const workforceMemberId = workforceMemberIdInput
      ? typeof workforceMemberIdInput === "bigint"
        ? workforceMemberIdInput
        : BigInt(workforceMemberIdInput)
      : null;

    await this.db
      .update(engagementAutopilotSettings)
      .set({
        enabled: false,
        updatedByWorkforceMemberId: workforceMemberId,
        updatedAt: new Date(),
      })
      .where(eq(engagementAutopilotSettings.workspaceId, workspaceId));

    return this.getSettings(workspaceId);
  }

  async recordRun(
    workspaceIdInput: bigint | string,
    run: {
      runId: string;
      triggerRuleId: string;
      threadId: bigint | string;
      outcome?: string;
      handedOff?: boolean;
      approvalCount?: number;
    }
  ): Promise<void> {
    const workspaceId = typeof workspaceIdInput === "bigint" ? workspaceIdInput : BigInt(workspaceIdInput);
    const threadId = typeof run.threadId === "bigint" ? run.threadId : BigInt(run.threadId);

    await this.db.insert(engagementAutopilotRuns).values({
      id: generateSnowflake(),
      workspaceId,
      runId: run.runId,
      triggerRuleId: run.triggerRuleId,
      threadId,
      outcome: run.outcome || "completed",
      handedOff: run.handedOff || false,
      approvalCount: run.approvalCount || 0,
      createdAt: new Date(),
    });
  }

  async checkThresholdBreach(workspaceIdInput: bigint | string): Promise<{ tripped: boolean; reason?: string }> {
    const workspaceId = typeof workspaceIdInput === "bigint" ? workspaceIdInput : BigInt(workspaceIdInput);
    const settings = await this.getSettings(workspaceId);
    if (!settings.enabled) {
      return { tripped: false };
    }

    const recentRuns = await this.db
      .select()
      .from(engagementAutopilotRuns)
      .where(eq(engagementAutopilotRuns.workspaceId, workspaceId))
      .orderBy(desc(engagementAutopilotRuns.createdAt))
      .limit(50);

    if (recentRuns.length < 10) {
      return { tripped: false };
    }

    const total = recentRuns.length;
    const errors = recentRuns.filter((r) => r.outcome === "failed").length;
    const handoffs = recentRuns.filter((r) => r.handedOff).length;
    const completedWithoutHandoff = recentRuns.filter((r) => r.outcome === "completed" && !r.handedOff).length;

    const errorRate = errors / total;
    const takeoverRate = handoffs / total;
    const containmentRate = completedWithoutHandoff / total;

    if (errorRate > settings.errorMax) {
      await this.emergencyKillSwitch(workspaceId);
      return {
        tripped: true,
        reason: `error_rate_breached: ${errorRate.toFixed(4)} > ${settings.errorMax}`,
      };
    }

    if (takeoverRate > settings.takeoverMax) {
      await this.emergencyKillSwitch(workspaceId);
      return {
        tripped: true,
        reason: `takeover_rate_breached: ${takeoverRate.toFixed(4)} > ${settings.takeoverMax}`,
      };
    }

    if (containmentRate < settings.containmentMin) {
      await this.emergencyKillSwitch(workspaceId);
      return {
        tripped: true,
        reason: `containment_rate_breached: ${containmentRate.toFixed(4)} < ${settings.containmentMin}`,
      };
    }

    return { tripped: false };
  }
}
