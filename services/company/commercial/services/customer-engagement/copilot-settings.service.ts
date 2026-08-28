import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import { engagementCopilotSettings } from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { ENGAGEMENT_PERMISSIONS, requireEngagementPermission } from "./rbac";

export interface CopilotSettingsDTO {
  id: string;
  workspaceId: string;
  enabled: boolean;
  allowedIntents: string[];
  knowledgeScope: Record<string, unknown>;
  allowedAgentSpecId: string | null;
  allowedAgentSpecVersion: string | null;
  allowedAgentSpecHash: string | null;
  evalEvidenceRef: string | null;
  evalEvidenceHash: string | null;
  updatedByWorkforceMemberId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface UpdateCopilotSettingsInput {
  allowedIntents?: string[];
  knowledgeScope?: Record<string, unknown>;
  agentSpecId?: string | null;
  agentSpecVersion?: string | null;
  agentSpecHash?: string | null;
  evalEvidenceRef?: string | null;
  evalEvidenceHash?: string | null;
}

const DEFAULT_ALLOWED_INTENTS = ["summarize", "draft_reply", "extract_facts", "sales_signal"];

function mapRowToDTO(row: typeof engagementCopilotSettings.$inferSelect): CopilotSettingsDTO {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    enabled: row.enabled,
    allowedIntents: (row.allowedIntents as string[]) || DEFAULT_ALLOWED_INTENTS,
    knowledgeScope: (row.knowledgeScope as Record<string, unknown>) || {},
    allowedAgentSpecId: row.allowedAgentSpecId,
    allowedAgentSpecVersion: row.allowedAgentSpecVersion,
    allowedAgentSpecHash: row.allowedAgentSpecHash,
    evalEvidenceRef: row.evalEvidenceRef,
    evalEvidenceHash: row.evalEvidenceHash,
    updatedByWorkforceMemberId: row.updatedByWorkforceMemberId ? row.updatedByWorkforceMemberId.toString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function getCopilotSettings(ctx: TenantContext): Promise<CopilotSettingsDTO> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(engagementCopilotSettings)
    .where(eq(engagementCopilotSettings.workspaceId, wsId))
    .limit(1);

  if (rows.length > 0) {
    return mapRowToDTO(rows[0]);
  }

  // Row chưa có -> tạo default (fail-closed, enabled = false)
  const newId = generateSnowflake();
  const [created] = await db
    .insert(engagementCopilotSettings)
    .values({
      id: newId,
      workspaceId: wsId,
      enabled: false,
      allowedIntents: DEFAULT_ALLOWED_INTENTS,
      knowledgeScope: {},
    })
    .returning();

  return mapRowToDTO(created);
}

export async function updateCopilotSettings(
  input: UpdateCopilotSettingsInput,
  ctx: TenantContext
): Promise<CopilotSettingsDTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.COPILOT_MANAGE);
  const wsId = BigInt(ctx.workspaceId);
  await getCopilotSettings(ctx); // ensure row exists

  const updateValues: Partial<typeof engagementCopilotSettings.$inferInsert> = {
    updatedAt: new Date(),
  };

  if (ctx.workforceMemberId) {
    updateValues.updatedByWorkforceMemberId = BigInt(ctx.workforceMemberId);
  }
  if (input.allowedIntents !== undefined) {
    updateValues.allowedIntents = input.allowedIntents;
  }
  if (input.knowledgeScope !== undefined) {
    updateValues.knowledgeScope = input.knowledgeScope;
  }
  if (input.agentSpecId !== undefined) {
    updateValues.allowedAgentSpecId = input.agentSpecId;
  }
  if (input.agentSpecVersion !== undefined) {
    updateValues.allowedAgentSpecVersion = input.agentSpecVersion;
  }
  if (input.agentSpecHash !== undefined) {
    updateValues.allowedAgentSpecHash = input.agentSpecHash;
  }
  if (input.evalEvidenceRef !== undefined) {
    updateValues.evalEvidenceRef = input.evalEvidenceRef;
  }
  if (input.evalEvidenceHash !== undefined) {
    updateValues.evalEvidenceHash = input.evalEvidenceHash;
  }

  const [updated] = await db
    .update(engagementCopilotSettings)
    .set(updateValues)
    .where(eq(engagementCopilotSettings.workspaceId, wsId))
    .returning();

  return mapRowToDTO(updated);
}

export async function enableCopilot(ctx: TenantContext): Promise<CopilotSettingsDTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.COPILOT_MANAGE);
  const current = await getCopilotSettings(ctx);

  // Fail-closed gate: bắt buộc pin spec
  if (!current.allowedAgentSpecId || !current.allowedAgentSpecVersion || !current.allowedAgentSpecHash) {
    throw APIError.failedPrecondition("pin an agent spec before enabling copilot");
  }

  // Fail-closed gate: bắt buộc eval evidence khớp hash spec
  if (!current.evalEvidenceRef || current.evalEvidenceHash !== current.allowedAgentSpecHash) {
    throw APIError.failedPrecondition("fresh eval evidence for the pinned spec is required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const [updated] = await db
    .update(engagementCopilotSettings)
    .set({
      enabled: true,
      updatedByWorkforceMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      updatedAt: new Date(),
    })
    .where(eq(engagementCopilotSettings.workspaceId, wsId))
    .returning();

  return mapRowToDTO(updated);
}

export async function disableCopilot(ctx: TenantContext): Promise<CopilotSettingsDTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.COPILOT_MANAGE);
  const wsId = BigInt(ctx.workspaceId);
  await getCopilotSettings(ctx); // ensure exists

  const [updated] = await db
    .update(engagementCopilotSettings)
    .set({
      enabled: false,
      updatedByWorkforceMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      updatedAt: new Date(),
    })
    .where(eq(engagementCopilotSettings.workspaceId, wsId))
    .returning();

  return mapRowToDTO(updated);
}

export async function assertCopilotUsable(
  intent: string,
  ctx: TenantContext
): Promise<CopilotSettingsDTO> {
  const settings = await getCopilotSettings(ctx);

  if (!settings.enabled) {
    throw APIError.failedPrecondition("Customer support copilot is not enabled for this workspace");
  }

  if (!settings.allowedIntents.includes(intent)) {
    throw APIError.invalidArgument(
      `Intent "${intent}" is not in allowed intents: ${settings.allowedIntents.join(", ")}`
    );
  }

  if (!settings.allowedAgentSpecId || !settings.allowedAgentSpecHash) {
    throw APIError.failedPrecondition("Pinned copilot agent spec is missing");
  }

  return settings;
}
