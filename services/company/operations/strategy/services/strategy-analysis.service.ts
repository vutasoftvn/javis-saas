import { eq, and } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import {
  strategicObjectives,
  bscFocusScopes,
  pestelSignals,
  resourceCapabilityAssessments,
  swotItems,
} from "../../../shared/db/schema/strategy";
import { identityWorkforceMembers } from "../../../shared/db/schema/identity";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  BscPerspective,
  VALID_BSC_PERSPECTIVES,
  getWorkspaceStrategySettings,
} from "./workspace-strategy-settings.service";

export type PestelDimension =
  | "POLITICAL"
  | "ECONOMIC"
  | "SOCIAL"
  | "TECHNOLOGICAL"
  | "ENVIRONMENTAL"
  | "LEGAL";

export const VALID_PESTEL_DIMENSIONS = [
  "POLITICAL",
  "ECONOMIC",
  "SOCIAL",
  "TECHNOLOGICAL",
  "ENVIRONMENTAL",
  "LEGAL",
] as const;

export type PestelImpact = "HIGH" | "MEDIUM" | "LOW" | "POSITIVE" | "NEGATIVE";
export const VALID_PESTEL_IMPACTS = [
  "HIGH",
  "MEDIUM",
  "LOW",
  "POSITIVE",
  "NEGATIVE",
] as const;

export type PestelCertainty = "HIGH" | "MEDIUM" | "LOW";
export const VALID_PESTEL_CERTAINTIES = ["HIGH", "MEDIUM", "LOW"] as const;

export type ResourceCapabilityCategory =
  | "FINANCIAL_RESOURCE"
  | "HUMAN_ORGANIZATIONAL_CAPABILITY"
  | "INTELLECTUAL_DATA_IP_ASSET"
  | "TECHNOLOGY_OPERATIONAL_ASSET"
  | "MARKET_RELATIONSHIP_ASSET"
  | "GOVERNANCE_LEGAL_RISK_CAPABILITY";

export const VALID_RESOURCE_CATEGORIES = [
  "FINANCIAL_RESOURCE",
  "HUMAN_ORGANIZATIONAL_CAPABILITY",
  "INTELLECTUAL_DATA_IP_ASSET",
  "TECHNOLOGY_OPERATIONAL_ASSET",
  "MARKET_RELATIONSHIP_ASSET",
  "GOVERNANCE_LEGAL_RISK_CAPABILITY",
] as const;

export type StrengthLevel = "STRONG" | "ADEQUATE" | "WEAK";
export const VALID_STRENGTH_LEVELS = ["STRONG", "ADEQUATE", "WEAK"] as const;

export type SwotKind = "STRENGTH" | "WEAKNESS" | "OPPORTUNITY" | "THREAT";
export const VALID_SWOT_KINDS = [
  "STRENGTH",
  "WEAKNESS",
  "OPPORTUNITY",
  "THREAT",
] as const;

export type SwotSourceType = "PESTEL_SIGNAL" | "RESOURCE_CAPABILITY" | "MANUAL";
export const VALID_SWOT_SOURCE_TYPES = [
  "PESTEL_SIGNAL",
  "RESOURCE_CAPABILITY",
  "MANUAL",
] as const;

export type AnalysisStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";

export interface PestelSignal {
  id: string;
  workspaceId: string;
  strategicObjectiveId: string;
  dimension: PestelDimension;
  statement: string;
  impact: PestelImpact;
  certainty: PestelCertainty;
  evidenceRefs: string[];
  bscPerspectives: BscPerspective[];
  status: AnalysisStatus;
  revision: number;
  createdAt: string;
  updatedAt: string;
}

export interface ResourceCapabilityAssessment {
  id: string;
  workspaceId: string;
  strategicObjectiveId: string;
  category: ResourceCapabilityCategory;
  statement: string;
  strengthLevel: StrengthLevel;
  evidenceRefs: string[];
  bscPerspectives: BscPerspective[];
  status: AnalysisStatus;
  revision: number;
  createdAt: string;
  updatedAt: string;
}

export interface SwotItem {
  id: string;
  workspaceId: string;
  strategicObjectiveId: string;
  kind: SwotKind;
  statement: string;
  sourceType: SwotSourceType;
  sourceId?: string | null;
  evidenceRefs: string[];
  bscPerspectives: BscPerspective[];
  status: AnalysisStatus;
  revision: number;
  createdAt: string;
  updatedAt: string;
}

/** Validates that an objective exists in the workspace and is ACTIVE. */
export async function assertActiveStrategicObjective(
  workspaceId: bigint | string,
  strategicObjectiveId: bigint | string
): Promise<void> {
  const wsId = BigInt(workspaceId);
  const objId = BigInt(strategicObjectiveId);

  const [obj] = await db
    .select()
    .from(strategicObjectives)
    .where(
      and(
        eq(strategicObjectives.id, objId),
        eq(strategicObjectives.workspaceId, wsId)
      )
    )
    .limit(1);

  if (!obj) {
    throw APIError.notFound(
      `Strategic objective ${strategicObjectiveId} not found in workspace ${workspaceId}`
    );
  }

  if (obj.status !== "ACTIVE") {
    throw APIError.failedPrecondition(
      `Strategic objective must be ACTIVE before creating or listing analysis artefacts (current: ${obj.status})`
    );
  }

}

/**
 * Validates the active objective and BSC focus intersection for analysis writes.
 * BSC is deliberately a write-time filter: reads and derivation operate on
 * artefacts that have already passed this validation.
 */
export async function assertActiveObjectiveAndBscIntersection(
  workspaceId: bigint | string,
  strategicObjectiveId: bigint | string,
  bscPerspectives: string[] = []
): Promise<void> {
  const wsId = BigInt(workspaceId);
  const objId = BigInt(strategicObjectiveId);

  await assertActiveStrategicObjective(workspaceId, strategicObjectiveId);

  // Validate perspectives syntax
  for (const p of bscPerspectives) {
    if (!VALID_BSC_PERSPECTIVES.includes(p as any)) {
      throw APIError.invalidArgument(`Invalid BSC perspective: '${p}'`);
    }
  }

  const settings = await getWorkspaceStrategySettings(workspaceId);

  if (settings.bscMode === "REQUIRED") {
    // Fetch active focus scopes for objective
    const scopes = await db
      .select({ perspective: bscFocusScopes.perspective })
      .from(bscFocusScopes)
      .where(
        and(
          eq(bscFocusScopes.strategicObjectiveId, objId),
          eq(bscFocusScopes.workspaceId, wsId),
          eq(bscFocusScopes.status, "ACTIVE")
        )
      );

    const activeScopesSet = new Set(scopes.map((s) => s.perspective));
    const hasIntersection = bscPerspectives.some((p) => activeScopesSet.has(p));

    if (!hasIntersection) {
      throw APIError.invalidArgument(
        `When bscMode is REQUIRED, analysis item must have at least one BSC perspective intersecting active focus scopes: [${[...activeScopesSet].join(", ")}]`
      );
    }
  }
}

async function isAgentCaller(ctx: TenantContext): Promise<boolean> {
  if (!ctx.workforceMemberId) return false;
  const [member] = await db
    .select({ memberType: identityWorkforceMembers.memberType })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, BigInt(ctx.workforceMemberId)),
        eq(identityWorkforceMembers.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .limit(1);

  return member?.memberType === "AI_AGENT";
}

// -------------------------------------------------------------
// PESTEL SIGNALS
// -------------------------------------------------------------

export async function createPestelSignal(
  ctx: TenantContext,
  params: {
    strategicObjectiveId: string;
    dimension: PestelDimension;
    statement: string;
    impact: PestelImpact;
    certainty: PestelCertainty;
    evidenceRefs?: string[];
    bscPerspectives?: BscPerspective[];
    status?: AnalysisStatus;
  }
): Promise<PestelSignal> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(params.strategicObjectiveId);

  if (!VALID_PESTEL_DIMENSIONS.includes(params.dimension)) {
    throw APIError.invalidArgument(`Invalid PESTEL dimension: '${params.dimension}'`);
  }
  if (!VALID_PESTEL_IMPACTS.includes(params.impact)) {
    throw APIError.invalidArgument(`Invalid PESTEL impact: '${params.impact}'`);
  }
  if (!VALID_PESTEL_CERTAINTIES.includes(params.certainty)) {
    throw APIError.invalidArgument(`Invalid PESTEL certainty: '${params.certainty}'`);
  }
  if (!params.statement || params.statement.trim().length === 0) {
    throw APIError.invalidArgument("PESTEL statement cannot be empty");
  }

  const bscPerspectives = params.bscPerspectives || [];
  await assertActiveObjectiveAndBscIntersection(
    ctx.workspaceId,
    params.strategicObjectiveId,
    bscPerspectives
  );

  const id = generateSnowflake();
  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [row] = await db
    .insert(pestelSignals)
    .values({
      id,
      workspaceId: wsId,
      strategicObjectiveId: objId,
      dimension: params.dimension,
      statement: params.statement.trim(),
      impact: params.impact,
      certainty: params.certainty,
      evidenceRefs: params.evidenceRefs || [],
      bscPerspectives,
      status: params.status || "DRAFT",
      createdByMemberId: actorId,
      updatedByMemberId: actorId,
      revision: 1,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    strategicObjectiveId: row.strategicObjectiveId.toString(),
    dimension: row.dimension as PestelDimension,
    statement: row.statement,
    impact: row.impact as PestelImpact,
    certainty: row.certainty as PestelCertainty,
    evidenceRefs: row.evidenceRefs as string[],
    bscPerspectives: row.bscPerspectives as BscPerspective[],
    status: row.status as AnalysisStatus,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function listPestelSignals(
  ctx: TenantContext,
  strategicObjectiveId: string,
  status?: AnalysisStatus
): Promise<{ items: PestelSignal[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(strategicObjectiveId);

  await assertActiveStrategicObjective(ctx.workspaceId, strategicObjectiveId);

  const conditions = [
    eq(pestelSignals.workspaceId, wsId),
    eq(pestelSignals.strategicObjectiveId, objId),
  ];
  if (status) {
    conditions.push(eq(pestelSignals.status, status));
  }

  const rows = await db
    .select()
    .from(pestelSignals)
    .where(and(...conditions));

  return {
    items: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      strategicObjectiveId: r.strategicObjectiveId.toString(),
      dimension: r.dimension as PestelDimension,
      statement: r.statement,
      impact: r.impact as PestelImpact,
      certainty: r.certainty as PestelCertainty,
      evidenceRefs: r.evidenceRefs as string[],
      bscPerspectives: r.bscPerspectives as BscPerspective[],
      status: r.status as AnalysisStatus,
      revision: r.revision,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    })),
  };
}

export async function updatePestelSignal(
  ctx: TenantContext,
  params: {
    id: string;
    dimension?: PestelDimension;
    statement?: string;
    impact?: PestelImpact;
    certainty?: PestelCertainty;
    evidenceRefs?: string[];
    bscPerspectives?: BscPerspective[];
    status?: AnalysisStatus;
  }
): Promise<PestelSignal> {
  const wsId = BigInt(ctx.workspaceId);
  const signalId = BigInt(params.id);

  const [existing] = await db
    .select()
    .from(pestelSignals)
    .where(and(eq(pestelSignals.id, signalId), eq(pestelSignals.workspaceId, wsId)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`PESTEL signal ${params.id} not found`);
  }

  const bscPerspectives = params.bscPerspectives ?? (existing.bscPerspectives as BscPerspective[]);
  await assertActiveObjectiveAndBscIntersection(
    ctx.workspaceId,
    existing.strategicObjectiveId.toString(),
    bscPerspectives
  );

  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [updated] = await db
    .update(pestelSignals)
    .set({
      dimension: params.dimension ?? existing.dimension,
      statement: params.statement ?? existing.statement,
      impact: params.impact ?? existing.impact,
      certainty: params.certainty ?? existing.certainty,
      evidenceRefs: params.evidenceRefs ?? existing.evidenceRefs,
      bscPerspectives,
      status: params.status ?? existing.status,
      updatedByMemberId: actorId,
      revision: existing.revision + 1,
      updatedAt: now,
    })
    .where(eq(pestelSignals.id, signalId))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    strategicObjectiveId: updated.strategicObjectiveId.toString(),
    dimension: updated.dimension as PestelDimension,
    statement: updated.statement,
    impact: updated.impact as PestelImpact,
    certainty: updated.certainty as PestelCertainty,
    evidenceRefs: updated.evidenceRefs as string[],
    bscPerspectives: updated.bscPerspectives as BscPerspective[],
    status: updated.status as AnalysisStatus,
    revision: updated.revision,
    createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
  };
}

// -------------------------------------------------------------
// RESOURCE & CAPABILITY ASSESSMENTS
// -------------------------------------------------------------

export async function createResourceCapabilityAssessment(
  ctx: TenantContext,
  params: {
    strategicObjectiveId: string;
    category: ResourceCapabilityCategory;
    statement: string;
    strengthLevel: StrengthLevel;
    evidenceRefs?: string[];
    bscPerspectives?: BscPerspective[];
    status?: AnalysisStatus;
  }
): Promise<ResourceCapabilityAssessment> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(params.strategicObjectiveId);

  if (!VALID_RESOURCE_CATEGORIES.includes(params.category)) {
    throw APIError.invalidArgument(`Invalid resource category: '${params.category}'`);
  }
  if (!VALID_STRENGTH_LEVELS.includes(params.strengthLevel)) {
    throw APIError.invalidArgument(`Invalid strength level: '${params.strengthLevel}'`);
  }
  if (!params.statement || params.statement.trim().length === 0) {
    throw APIError.invalidArgument("Assessment statement cannot be empty");
  }

  const bscPerspectives = params.bscPerspectives || [];
  await assertActiveObjectiveAndBscIntersection(
    ctx.workspaceId,
    params.strategicObjectiveId,
    bscPerspectives
  );

  const id = generateSnowflake();
  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [row] = await db
    .insert(resourceCapabilityAssessments)
    .values({
      id,
      workspaceId: wsId,
      strategicObjectiveId: objId,
      category: params.category,
      statement: params.statement.trim(),
      strengthLevel: params.strengthLevel,
      evidenceRefs: params.evidenceRefs || [],
      bscPerspectives,
      status: params.status || "DRAFT",
      createdByMemberId: actorId,
      updatedByMemberId: actorId,
      revision: 1,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    strategicObjectiveId: row.strategicObjectiveId.toString(),
    category: row.category as ResourceCapabilityCategory,
    statement: row.statement,
    strengthLevel: row.strengthLevel as StrengthLevel,
    evidenceRefs: row.evidenceRefs as string[],
    bscPerspectives: row.bscPerspectives as BscPerspective[],
    status: row.status as AnalysisStatus,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function listResourceCapabilityAssessments(
  ctx: TenantContext,
  strategicObjectiveId: string,
  status?: AnalysisStatus
): Promise<{ items: ResourceCapabilityAssessment[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(strategicObjectiveId);

  await assertActiveStrategicObjective(ctx.workspaceId, strategicObjectiveId);

  const conditions = [
    eq(resourceCapabilityAssessments.workspaceId, wsId),
    eq(resourceCapabilityAssessments.strategicObjectiveId, objId),
  ];
  if (status) {
    conditions.push(eq(resourceCapabilityAssessments.status, status));
  }

  const rows = await db
    .select()
    .from(resourceCapabilityAssessments)
    .where(and(...conditions));

  return {
    items: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      strategicObjectiveId: r.strategicObjectiveId.toString(),
      category: r.category as ResourceCapabilityCategory,
      statement: r.statement,
      strengthLevel: r.strengthLevel as StrengthLevel,
      evidenceRefs: r.evidenceRefs as string[],
      bscPerspectives: r.bscPerspectives as BscPerspective[],
      status: r.status as AnalysisStatus,
      revision: r.revision,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    })),
  };
}

export async function updateResourceCapabilityAssessment(
  ctx: TenantContext,
  params: {
    id: string;
    category?: ResourceCapabilityCategory;
    statement?: string;
    strengthLevel?: StrengthLevel;
    evidenceRefs?: string[];
    bscPerspectives?: BscPerspective[];
    status?: AnalysisStatus;
  }
): Promise<ResourceCapabilityAssessment> {
  const wsId = BigInt(ctx.workspaceId);
  const assessmentId = BigInt(params.id);

  const [existing] = await db
    .select()
    .from(resourceCapabilityAssessments)
    .where(
      and(
        eq(resourceCapabilityAssessments.id, assessmentId),
        eq(resourceCapabilityAssessments.workspaceId, wsId)
      )
    )
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`Resource assessment ${params.id} not found`);
  }

  const bscPerspectives =
    params.bscPerspectives ?? (existing.bscPerspectives as BscPerspective[]);
  await assertActiveObjectiveAndBscIntersection(
    ctx.workspaceId,
    existing.strategicObjectiveId.toString(),
    bscPerspectives
  );

  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [updated] = await db
    .update(resourceCapabilityAssessments)
    .set({
      category: params.category ?? existing.category,
      statement: params.statement ?? existing.statement,
      strengthLevel: params.strengthLevel ?? existing.strengthLevel,
      evidenceRefs: params.evidenceRefs ?? existing.evidenceRefs,
      bscPerspectives,
      status: params.status ?? existing.status,
      updatedByMemberId: actorId,
      revision: existing.revision + 1,
      updatedAt: now,
    })
    .where(eq(resourceCapabilityAssessments.id, assessmentId))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    strategicObjectiveId: updated.strategicObjectiveId.toString(),
    category: updated.category as ResourceCapabilityCategory,
    statement: updated.statement,
    strengthLevel: updated.strengthLevel as StrengthLevel,
    evidenceRefs: updated.evidenceRefs as string[],
    bscPerspectives: updated.bscPerspectives as BscPerspective[],
    status: updated.status as AnalysisStatus,
    revision: updated.revision,
    createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
  };
}

// -------------------------------------------------------------
// SWOT ITEMS
// -------------------------------------------------------------

export async function createSwotItem(
  ctx: TenantContext,
  params: {
    strategicObjectiveId: string;
    kind: SwotKind;
    statement: string;
    sourceType: SwotSourceType;
    sourceId?: string | null;
    evidenceRefs?: string[];
    bscPerspectives?: BscPerspective[];
    status?: AnalysisStatus;
  }
): Promise<SwotItem> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(params.strategicObjectiveId);

  if (!VALID_SWOT_KINDS.includes(params.kind)) {
    throw APIError.invalidArgument(`Invalid SWOT kind: '${params.kind}'`);
  }
  if (!VALID_SWOT_SOURCE_TYPES.includes(params.sourceType)) {
    throw APIError.invalidArgument(`Invalid SWOT source type: '${params.sourceType}'`);
  }
  if (!params.statement || params.statement.trim().length === 0) {
    throw APIError.invalidArgument("SWOT statement cannot be empty");
  }

  // AI agents cannot create or make a SWOT item ACTIVE directly without human write
  const targetStatus = params.status || "DRAFT";
  if (targetStatus === "ACTIVE") {
    const isAgent = await isAgentCaller(ctx);
    if (isAgent) {
      throw APIError.permissionDenied(
        "AI agents cannot activate SWOT items; activation requires a human write action"
      );
    }
  }

  const bscPerspectives = params.bscPerspectives || [];
  await assertActiveObjectiveAndBscIntersection(
    ctx.workspaceId,
    params.strategicObjectiveId,
    bscPerspectives
  );

  // Validate source provenance
  if (params.sourceType === "PESTEL_SIGNAL") {
    if (!params.sourceId) {
      throw APIError.invalidArgument("sourceId is required when sourceType is PESTEL_SIGNAL");
    }
    const [signal] = await db
      .select({ id: pestelSignals.id, status: pestelSignals.status })
      .from(pestelSignals)
      .where(
        and(
          eq(pestelSignals.id, BigInt(params.sourceId)),
          eq(pestelSignals.workspaceId, wsId),
          eq(pestelSignals.strategicObjectiveId, objId)
        )
      )
      .limit(1);

    if (!signal) {
      throw APIError.invalidArgument(
        `Source PESTEL signal ${params.sourceId} not found in this workspace and objective`
      );
    }
  } else if (params.sourceType === "RESOURCE_CAPABILITY") {
    if (!params.sourceId) {
      throw APIError.invalidArgument(
        "sourceId is required when sourceType is RESOURCE_CAPABILITY"
      );
    }
    const [assessment] = await db
      .select({
        id: resourceCapabilityAssessments.id,
        status: resourceCapabilityAssessments.status,
      })
      .from(resourceCapabilityAssessments)
      .where(
        and(
          eq(resourceCapabilityAssessments.id, BigInt(params.sourceId)),
          eq(resourceCapabilityAssessments.workspaceId, wsId),
          eq(resourceCapabilityAssessments.strategicObjectiveId, objId)
        )
      )
      .limit(1);

    if (!assessment) {
      throw APIError.invalidArgument(
        `Source resource assessment ${params.sourceId} not found in this workspace and objective`
      );
    }
  }

  const id = generateSnowflake();
  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [row] = await db
    .insert(swotItems)
    .values({
      id,
      workspaceId: wsId,
      strategicObjectiveId: objId,
      kind: params.kind,
      statement: params.statement.trim(),
      sourceType: params.sourceType,
      sourceId: params.sourceId ? BigInt(params.sourceId) : null,
      evidenceRefs: params.evidenceRefs || [],
      bscPerspectives,
      status: targetStatus,
      createdByMemberId: actorId,
      updatedByMemberId: actorId,
      revision: 1,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    strategicObjectiveId: row.strategicObjectiveId.toString(),
    kind: row.kind as SwotKind,
    statement: row.statement,
    sourceType: row.sourceType as SwotSourceType,
    sourceId: row.sourceId ? row.sourceId.toString() : null,
    evidenceRefs: row.evidenceRefs as string[],
    bscPerspectives: row.bscPerspectives as BscPerspective[],
    status: row.status as AnalysisStatus,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function listSwotItems(
  ctx: TenantContext,
  strategicObjectiveId: string,
  status?: AnalysisStatus
): Promise<{ items: SwotItem[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(strategicObjectiveId);

  await assertActiveStrategicObjective(ctx.workspaceId, strategicObjectiveId);

  const conditions = [
    eq(swotItems.workspaceId, wsId),
    eq(swotItems.strategicObjectiveId, objId),
  ];
  if (status) {
    conditions.push(eq(swotItems.status, status));
  }

  const rows = await db
    .select()
    .from(swotItems)
    .where(and(...conditions));

  return {
    items: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      strategicObjectiveId: r.strategicObjectiveId.toString(),
      kind: r.kind as SwotKind,
      statement: r.statement,
      sourceType: r.sourceType as SwotSourceType,
      sourceId: r.sourceId ? r.sourceId.toString() : null,
      evidenceRefs: r.evidenceRefs as string[],
      bscPerspectives: r.bscPerspectives as BscPerspective[],
      status: r.status as AnalysisStatus,
      revision: r.revision,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    })),
  };
}

export async function updateSwotItem(
  ctx: TenantContext,
  params: {
    id: string;
    kind?: SwotKind;
    statement?: string;
    status?: AnalysisStatus;
    evidenceRefs?: string[];
    bscPerspectives?: BscPerspective[];
  }
): Promise<SwotItem> {
  const wsId = BigInt(ctx.workspaceId);
  const itemId = BigInt(params.id);

  const [existing] = await db
    .select()
    .from(swotItems)
    .where(and(eq(swotItems.id, itemId), eq(swotItems.workspaceId, wsId)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`SWOT item ${params.id} not found`);
  }

  if (params.status === "ACTIVE") {
    const isAgent = await isAgentCaller(ctx);
    if (isAgent) {
      throw APIError.permissionDenied(
        "AI agents cannot activate SWOT items; activation requires a human write action"
      );
    }
  }

  const bscPerspectives =
    params.bscPerspectives ?? (existing.bscPerspectives as BscPerspective[]);
  await assertActiveObjectiveAndBscIntersection(
    ctx.workspaceId,
    existing.strategicObjectiveId.toString(),
    bscPerspectives
  );

  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [updated] = await db
    .update(swotItems)
    .set({
      kind: params.kind ?? existing.kind,
      statement: params.statement ?? existing.statement,
      status: params.status ?? existing.status,
      evidenceRefs: params.evidenceRefs ?? existing.evidenceRefs,
      bscPerspectives,
      updatedByMemberId: actorId,
      revision: existing.revision + 1,
      updatedAt: now,
    })
    .where(eq(swotItems.id, itemId))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    strategicObjectiveId: updated.strategicObjectiveId.toString(),
    kind: updated.kind as SwotKind,
    statement: updated.statement,
    sourceType: updated.sourceType as SwotSourceType,
    sourceId: updated.sourceId ? updated.sourceId.toString() : null,
    evidenceRefs: updated.evidenceRefs as string[],
    bscPerspectives: updated.bscPerspectives as BscPerspective[],
    status: updated.status as AnalysisStatus,
    revision: updated.revision,
    createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
  };
}

/**
 * Derives SWOT draft candidates with explicit source provenance from active PESTEL signals
 * and active Resource & Capability assessments.
 * All derived candidates are strictly in DRAFT status.
 */
export async function deriveSwotDrafts(
  ctx: TenantContext,
  strategicObjectiveId: string
): Promise<{ items: SwotItem[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(strategicObjectiveId);

  await assertActiveStrategicObjective(ctx.workspaceId, strategicObjectiveId);

  // Fetch active PESTEL signals
  const signals = await db
    .select()
    .from(pestelSignals)
    .where(
      and(
        eq(pestelSignals.workspaceId, wsId),
        eq(pestelSignals.strategicObjectiveId, objId),
        eq(pestelSignals.status, "ACTIVE")
      )
    );

  // Fetch active Resource & Capability assessments
  const assessments = await db
    .select()
    .from(resourceCapabilityAssessments)
    .where(
      and(
        eq(resourceCapabilityAssessments.workspaceId, wsId),
        eq(resourceCapabilityAssessments.strategicObjectiveId, objId),
        eq(resourceCapabilityAssessments.status, "ACTIVE")
      )
    );

  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const now = new Date();
  const draftsToInsert: Array<typeof swotItems.$inferInsert> = [];

  // External signals -> OPPORTUNITY or THREAT
  for (const sig of signals) {
    const isPositive =
      sig.impact === "POSITIVE" || sig.impact === "HIGH";
    const kind: SwotKind = isPositive ? "OPPORTUNITY" : "THREAT";

    draftsToInsert.push({
      id: generateSnowflake(),
      workspaceId: wsId,
      strategicObjectiveId: objId,
      kind,
      statement: `[Dự thảo từ tín hiệu ${sig.dimension}] ${sig.statement}`,
      sourceType: "PESTEL_SIGNAL",
      sourceId: sig.id,
      evidenceRefs: sig.evidenceRefs,
      bscPerspectives: sig.bscPerspectives,
      status: "DRAFT", // AI derivation can ONLY produce DRAFT
      createdByMemberId: actorId,
      updatedByMemberId: actorId,
      revision: 1,
      createdAt: now,
      updatedAt: now,
    });
  }

  // Internal resources & capabilities -> STRENGTH or WEAKNESS
  for (const asmt of assessments) {
    const isStrength =
      asmt.strengthLevel === "STRONG" || asmt.strengthLevel === "ADEQUATE";
    const kind: SwotKind = isStrength ? "STRENGTH" : "WEAKNESS";

    draftsToInsert.push({
      id: generateSnowflake(),
      workspaceId: wsId,
      strategicObjectiveId: objId,
      kind,
      statement: `[Dự thảo từ năng lực] ${asmt.statement}`,
      sourceType: "RESOURCE_CAPABILITY",
      sourceId: asmt.id,
      evidenceRefs: asmt.evidenceRefs,
      bscPerspectives: asmt.bscPerspectives,
      status: "DRAFT", // AI derivation can ONLY produce DRAFT
      createdByMemberId: actorId,
      updatedByMemberId: actorId,
      revision: 1,
      createdAt: now,
      updatedAt: now,
    });
  }

  if (draftsToInsert.length === 0) {
    return { items: [] };
  }

  const inserted = await db
    .insert(swotItems)
    .values(draftsToInsert)
    .returning();

  return {
    items: inserted.map((row) => ({
      id: row.id.toString(),
      workspaceId: row.workspaceId.toString(),
      strategicObjectiveId: row.strategicObjectiveId.toString(),
      kind: row.kind as SwotKind,
      statement: row.statement,
      sourceType: row.sourceType as SwotSourceType,
      sourceId: row.sourceId ? row.sourceId.toString() : null,
      evidenceRefs: row.evidenceRefs as string[],
      bscPerspectives: row.bscPerspectives as BscPerspective[],
      status: row.status as AnalysisStatus,
      revision: row.revision,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    })),
  };
}
