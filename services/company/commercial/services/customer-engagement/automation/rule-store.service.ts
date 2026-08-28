import { APIError } from "encore.dev/api";
import { and, eq, desc } from "drizzle-orm";
import { db } from "../../../db";
import { engagementAutomationRules } from "../../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../../shared/types/tenant_context";
import { AutomationRule, validateRule } from "./rule-model";

export async function createOrVersionRule(
  ruleInput: Omit<AutomationRule, "version" | "enabled"> & { enabled?: boolean },
  ctx: TenantContext
): Promise<AutomationRule> {
  const wsId = BigInt(ctx.workspaceId);

  validateRule({
    ...ruleInput,
    version: 1,
    enabled: false,
  });

  // Check existing versions of ruleKey
  const existingRules = await db
    .select()
    .from(engagementAutomationRules)
    .where(
      and(
        eq(engagementAutomationRules.workspaceId, wsId),
        eq(engagementAutomationRules.ruleKey, ruleInput.ruleKey)
      )
    )
    .orderBy(desc(engagementAutomationRules.version));

  const nextVersion = existingRules.length > 0 ? existingRules[0].version + 1 : 1;
  const id = generateSnowflake();

  const [row] = await db
    .insert(engagementAutomationRules)
    .values({
      id,
      workspaceId: wsId,
      ruleKey: ruleInput.ruleKey,
      version: nextVersion,
      name: ruleInput.name,
      trigger: ruleInput.trigger,
      priority: ruleInput.priority ?? 100,
      condition: ruleInput.condition,
      actions: ruleInput.actions,
      enabled: ruleInput.enabled ?? false, // default disabled for safety
      stopOnMatch: ruleInput.stopOnMatch ?? false,
      effectiveFrom: ruleInput.effectiveFrom ?? new Date(),
      effectiveUntil: ruleInput.effectiveUntil ?? null,
      createdByWorkforceMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    ruleKey: row.ruleKey,
    version: row.version,
    name: row.name,
    trigger: row.trigger as any,
    priority: row.priority,
    condition: row.condition as any,
    actions: row.actions as any,
    enabled: row.enabled,
    stopOnMatch: row.stopOnMatch,
    effectiveFrom: row.effectiveFrom,
    effectiveUntil: row.effectiveUntil,
    createdAt: row.createdAt,
  };
}

export async function enableRule(ruleKey: string, ctx: TenantContext): Promise<AutomationRule> {
  const wsId = BigInt(ctx.workspaceId);

  // Find latest version
  const rows = await db
    .select()
    .from(engagementAutomationRules)
    .where(
      and(
        eq(engagementAutomationRules.workspaceId, wsId),
        eq(engagementAutomationRules.ruleKey, ruleKey)
      )
    )
    .orderBy(desc(engagementAutomationRules.version));

  if (rows.length === 0) {
    throw APIError.notFound("Automation rule not found");
  }

  const latest = rows[0];

  const [updated] = await db
    .update(engagementAutomationRules)
    .set({ enabled: true })
    .where(eq(engagementAutomationRules.id, latest.id))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    ruleKey: updated.ruleKey,
    version: updated.version,
    name: updated.name,
    trigger: updated.trigger as any,
    priority: updated.priority,
    condition: updated.condition as any,
    actions: updated.actions as any,
    enabled: updated.enabled,
    stopOnMatch: updated.stopOnMatch,
    effectiveFrom: updated.effectiveFrom,
    effectiveUntil: updated.effectiveUntil,
    createdAt: updated.createdAt,
  };
}

export async function disableRule(ruleKey: string, ctx: TenantContext): Promise<{ ruleKey: string; enabled: boolean }> {
  const wsId = BigInt(ctx.workspaceId);

  await db
    .update(engagementAutomationRules)
    .set({ enabled: false })
    .where(
      and(
        eq(engagementAutomationRules.workspaceId, wsId),
        eq(engagementAutomationRules.ruleKey, ruleKey)
      )
    );

  return { ruleKey, enabled: false };
}

export async function listRules(ctx: TenantContext): Promise<AutomationRule[]> {
  const wsId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(engagementAutomationRules)
    .where(eq(engagementAutomationRules.workspaceId, wsId))
    .orderBy(desc(engagementAutomationRules.createdAt));

  return rows.map((row) => ({
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    ruleKey: row.ruleKey,
    version: row.version,
    name: row.name,
    trigger: row.trigger as any,
    priority: row.priority,
    condition: row.condition as any,
    actions: row.actions as any,
    enabled: row.enabled,
    stopOnMatch: row.stopOnMatch,
    effectiveFrom: row.effectiveFrom,
    effectiveUntil: row.effectiveUntil,
    createdAt: row.createdAt,
  }));
}
