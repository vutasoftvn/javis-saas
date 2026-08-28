import { APIError } from "encore.dev/api";
import { and, eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  marketingContexts,
  marketingContextRevisions,
  marketingProductMarketing,
  marketingIcpSegments,
  marketingCustomerResearchThemes,
  marketingCustomerLanguage,
  marketingContextEvidence,
} = schema;

export interface ProductMarketingDTO {
  category: string | null;
  positioningStatement: string | null;
  alternatives: any[];
  differentiators: any[];
  brandVoice: Record<string, any>;
}

export interface IcpSegmentDTO {
  id: string;
  segment: string;
  confidence: string;
  evidenceIds: string[];
}

export interface CustomerResearchThemeDTO {
  id: string;
  type: string;
  summary: string;
  confidence: string;
  evidenceIds: string[];
}

export interface CustomerLanguageDTO {
  id: string;
  quote: string;
  sourceId: string | null;
  capturedAt: string | null;
}

export interface MarketingContextEvidenceDTO {
  id: string;
  evidenceId: string;
  kind: string;
  sourceUrl: string | null;
  capturedAt: string | null;
  capturedBy: string | null;
  confidence: string;
  trust: string;
  sensitivity: string;
}

export interface MarketingContextDTO {
  id: string;
  workspaceId: string;
  revision: number;
  status: "draft" | "review_required" | "approved" | string;
  updatedByUserId: string | null;
  reviewedByUserId: string | null;
  reviewedAt: string | null;
  sourceSkillId: string | null;
  sourceSkillVersion: string | null;
  sourceSkillHash: string | null;
  productMarketing: ProductMarketingDTO;
  icpSegments: IcpSegmentDTO[];
  customerResearchThemes: CustomerResearchThemeDTO[];
  customerLanguage: CustomerLanguageDTO[];
  evidence: MarketingContextEvidenceDTO[];
  offerArchitecture: Record<string, any> | null;
  twelveWeekPlan: Record<string, any> | null;
  createdAt: string;
  updatedAt: string;
}

export interface UpdateProductMarketingParams {
  category?: string;
  positioningStatement?: string;
  alternatives?: any[];
  differentiators?: any[];
  brandVoice?: Record<string, any>;
  expectedRevision?: number;
  sourceSkillId?: string;
  sourceSkillVersion?: string;
  sourceSkillHash?: string;
}

export interface UpdateCustomerResearchParams {
  icpSegments?: Array<{
    segment: string;
    confidence?: string;
    evidenceIds?: string[];
  }>;
  themes?: Array<{
    type: string;
    summary: string;
    confidence?: string;
    evidenceIds?: string[];
  }>;
  quotes?: Array<{
    quote: string;
    sourceId?: string;
    capturedAt?: string;
  }>;
  evidence?: Array<{
    evidenceId: string;
    kind: string;
    sourceUrl?: string;
    capturedAt?: string;
    capturedBy?: string;
    confidence?: string;
    trust?: string;
    sensitivity?: string;
  }>;
  expectedRevision?: number;
  sourceSkillId?: string;
  sourceSkillVersion?: string;
  sourceSkillHash?: string;
}

export interface UpdateOfferArchitectureParams {
  offerArchitecture: Record<string, any>;
  expectedRevision?: number;
  sourceSkillId?: string;
  sourceSkillVersion?: string;
  sourceSkillHash?: string;
}

export interface UpdateTwelveWeekPlanParams {
  twelveWeekPlan: Record<string, any>;
  expectedRevision?: number;
  sourceSkillId?: string;
  sourceSkillVersion?: string;
  sourceSkillHash?: string;
}

export interface SubmitForReviewParams {
  expectedRevision?: number;
}

export interface ApproveContextParams {
  expectedRevision?: number;
}

async function getOrCreateContextRow(ctx: TenantContext) {
  const wsId = BigInt(ctx.workspaceId);
  const [existing] = await db
    .select()
    .from(marketingContexts)
    .where(eq(marketingContexts.workspaceId, wsId))
    .limit(1);

  if (existing) {
    return existing;
  }

  // Create initial context row with snowflake id
  const contextId = generateSnowflake();
  const [created] = await db
    .insert(marketingContexts)
    .values({
      id: contextId,
      workspaceId: wsId,
      revision: 1,
      status: "draft",
      updatedByUserId: BigInt(ctx.userId),
      offerArchitecture: {},
      twelveWeekPlan: {},
    })
    .returning();

  // Create empty product marketing record
  await db.insert(marketingProductMarketing).values({
    id: generateSnowflake(),
    contextId,
    workspaceId: wsId,
    category: null,
    positioningStatement: null,
    alternatives: [],
    differentiators: [],
    brandVoice: {},
  });

  return created;
}

async function assembleContextDTO(contextRow: typeof marketingContexts.$inferSelect, ctx: TenantContext): Promise<MarketingContextDTO> {
  const wsId = BigInt(ctx.workspaceId);
  const contextId = contextRow.id;

  // 1. Product Marketing
  const [pmRow] = await db
    .select()
    .from(marketingProductMarketing)
    .where(
      and(
        eq(marketingProductMarketing.workspaceId, wsId),
        eq(marketingProductMarketing.contextId, contextId)
      )
    )
    .limit(1);

  const productMarketing: ProductMarketingDTO = {
    category: pmRow?.category ?? null,
    positioningStatement: pmRow?.positioningStatement ?? null,
    alternatives: (pmRow?.alternatives as any[]) ?? [],
    differentiators: (pmRow?.differentiators as any[]) ?? [],
    brandVoice: (pmRow?.brandVoice as Record<string, any>) ?? {},
  };

  // 2. ICP Segments
  const icpRows = await db
    .select()
    .from(marketingIcpSegments)
    .where(
      and(
        eq(marketingIcpSegments.workspaceId, wsId),
        eq(marketingIcpSegments.contextId, contextId)
      )
    );

  const icpSegments: IcpSegmentDTO[] = icpRows.map((r) => ({
    id: String(r.id),
    segment: r.segment,
    confidence: r.confidence,
    evidenceIds: (r.evidenceIds as string[]) ?? [],
  }));

  // 3. Customer Research Themes
  const themeRows = await db
    .select()
    .from(marketingCustomerResearchThemes)
    .where(
      and(
        eq(marketingCustomerResearchThemes.workspaceId, wsId),
        eq(marketingCustomerResearchThemes.contextId, contextId)
      )
    );

  const customerResearchThemes: CustomerResearchThemeDTO[] = themeRows.map((r) => ({
    id: String(r.id),
    type: r.type,
    summary: r.summary,
    confidence: r.confidence,
    evidenceIds: (r.evidenceIds as string[]) ?? [],
  }));

  // 4. Customer Language
  const quoteRows = await db
    .select()
    .from(marketingCustomerLanguage)
    .where(
      and(
        eq(marketingCustomerLanguage.workspaceId, wsId),
        eq(marketingCustomerLanguage.contextId, contextId)
      )
    );

  const customerLanguage: CustomerLanguageDTO[] = quoteRows.map((r) => ({
    id: String(r.id),
    quote: r.quote,
    sourceId: r.sourceId,
    capturedAt: r.capturedAt ? r.capturedAt.toISOString() : null,
  }));

  // 5. Evidence
  const evidenceRows = await db
    .select()
    .from(marketingContextEvidence)
    .where(
      and(
        eq(marketingContextEvidence.workspaceId, wsId),
        eq(marketingContextEvidence.contextId, contextId)
      )
    );

  const evidence: MarketingContextEvidenceDTO[] = evidenceRows.map((r) => ({
    id: String(r.id),
    evidenceId: r.evidenceId,
    kind: r.kind,
    sourceUrl: r.sourceUrl,
    capturedAt: r.capturedAt ? r.capturedAt.toISOString() : null,
    capturedBy: r.capturedBy,
    confidence: r.confidence,
    trust: r.trust,
    sensitivity: r.sensitivity,
  }));

  return {
    id: String(contextRow.id),
    workspaceId: String(contextRow.workspaceId),
    revision: contextRow.revision,
    status: contextRow.status,
    updatedByUserId: contextRow.updatedByUserId ? String(contextRow.updatedByUserId) : null,
    reviewedByUserId: contextRow.reviewedByUserId ? String(contextRow.reviewedByUserId) : null,
    reviewedAt: contextRow.reviewedAt ? contextRow.reviewedAt.toISOString() : null,
    sourceSkillId: contextRow.sourceSkillId,
    sourceSkillVersion: contextRow.sourceSkillVersion,
    sourceSkillHash: contextRow.sourceSkillHash,
    productMarketing,
    icpSegments,
    customerResearchThemes,
    customerLanguage,
    evidence,
    offerArchitecture: (contextRow.offerArchitecture as Record<string, any>) ?? null,
    twelveWeekPlan: (contextRow.twelveWeekPlan as Record<string, any>) ?? null,
    createdAt: contextRow.createdAt.toISOString(),
    updatedAt: contextRow.updatedAt.toISOString(),
  };
}

async function recordRevisionSnapshot(
  contextId: bigint,
  workspaceId: bigint,
  revision: number,
  snapshot: MarketingContextDTO,
  userId: bigint,
  sourceSkill?: { id?: string; version?: string; hash?: string }
) {
  await db.insert(marketingContextRevisions).values({
    id: generateSnowflake(),
    contextId,
    workspaceId,
    revision,
    snapshot,
    createdByUserId: userId,
    sourceSkillId: sourceSkill?.id ?? null,
    sourceSkillVersion: sourceSkill?.version ?? null,
    sourceSkillHash: sourceSkill?.hash ?? null,
  });
}

function verifyOptimisticLock(currentRevision: number, expectedRevision?: number) {
  if (expectedRevision !== undefined && expectedRevision !== currentRevision) {
    throw APIError.aborted(
      `revision conflict: expected revision ${expectedRevision} but current revision is ${currentRevision}`
    );
  }
}

export async function getMarketingContextService(ctx: TenantContext): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  return assembleContextDTO(contextRow, ctx);
}

export async function updateProductMarketingService(
  ctx: TenantContext,
  params: UpdateProductMarketingParams
): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  // Update or insert product marketing
  const [existingPm] = await db
    .select({ id: marketingProductMarketing.id })
    .from(marketingProductMarketing)
    .where(
      and(
        eq(marketingProductMarketing.workspaceId, wsId),
        eq(marketingProductMarketing.contextId, contextRow.id)
      )
    )
    .limit(1);

  if (existingPm) {
    await db
      .update(marketingProductMarketing)
      .set({
        category: params.category !== undefined ? params.category : undefined,
        positioningStatement: params.positioningStatement !== undefined ? params.positioningStatement : undefined,
        alternatives: params.alternatives !== undefined ? params.alternatives : undefined,
        differentiators: params.differentiators !== undefined ? params.differentiators : undefined,
        brandVoice: params.brandVoice !== undefined ? params.brandVoice : undefined,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(marketingProductMarketing.workspaceId, wsId),
          eq(marketingProductMarketing.contextId, contextRow.id)
        )
      );
  } else {
    await db.insert(marketingProductMarketing).values({
      id: generateSnowflake(),
      contextId: contextRow.id,
      workspaceId: wsId,
      category: params.category ?? null,
      positioningStatement: params.positioningStatement ?? null,
      alternatives: params.alternatives ?? [],
      differentiators: params.differentiators ?? [],
      brandVoice: params.brandVoice ?? {},
    });
  }

  // Update context root revision & provenance
  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      revision: nextRevision,
      status: "draft",
      updatedByUserId: userId,
      sourceSkillId: params.sourceSkillId !== undefined ? params.sourceSkillId : contextRow.sourceSkillId,
      sourceSkillVersion: params.sourceSkillVersion !== undefined ? params.sourceSkillVersion : contextRow.sourceSkillVersion,
      sourceSkillHash: params.sourceSkillHash !== undefined ? params.sourceSkillHash : contextRow.sourceSkillHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId,
    {
      id: params.sourceSkillId,
      version: params.sourceSkillVersion,
      hash: params.sourceSkillHash,
    }
  );

  return dto;
}

export async function updateCustomerResearchService(
  ctx: TenantContext,
  params: UpdateCustomerResearchParams
): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  // 1. Update ICP segments if provided
  if (params.icpSegments !== undefined) {
    await db
      .delete(marketingIcpSegments)
      .where(
        and(
          eq(marketingIcpSegments.workspaceId, wsId),
          eq(marketingIcpSegments.contextId, contextRow.id)
        )
      );

    if (params.icpSegments.length > 0) {
      await db.insert(marketingIcpSegments).values(
        params.icpSegments.map((s) => ({
          id: generateSnowflake(),
          contextId: contextRow.id,
          workspaceId: wsId,
          segment: s.segment,
          confidence: s.confidence ?? "medium",
          evidenceIds: s.evidenceIds ?? [],
        }))
      );
    }
  }

  // 2. Update Customer Research Themes if provided
  if (params.themes !== undefined) {
    await db
      .delete(marketingCustomerResearchThemes)
      .where(
        and(
          eq(marketingCustomerResearchThemes.workspaceId, wsId),
          eq(marketingCustomerResearchThemes.contextId, contextRow.id)
        )
      );

    if (params.themes.length > 0) {
      await db.insert(marketingCustomerResearchThemes).values(
        params.themes.map((t) => ({
          id: generateSnowflake(),
          contextId: contextRow.id,
          workspaceId: wsId,
          type: t.type,
          summary: t.summary,
          confidence: t.confidence ?? "medium",
          evidenceIds: t.evidenceIds ?? [],
        }))
      );
    }
  }

  // 3. Update Customer Language Quotes if provided
  if (params.quotes !== undefined) {
    await db
      .delete(marketingCustomerLanguage)
      .where(
        and(
          eq(marketingCustomerLanguage.workspaceId, wsId),
          eq(marketingCustomerLanguage.contextId, contextRow.id)
        )
      );

    if (params.quotes.length > 0) {
      await db.insert(marketingCustomerLanguage).values(
        params.quotes.map((q) => ({
          id: generateSnowflake(),
          contextId: contextRow.id,
          workspaceId: wsId,
          quote: q.quote,
          sourceId: q.sourceId ?? null,
          capturedAt: q.capturedAt ? new Date(q.capturedAt) : null,
        }))
      );
    }
  }

  // 4. Update Evidence if provided
  if (params.evidence !== undefined) {
    await db
      .delete(marketingContextEvidence)
      .where(
        and(
          eq(marketingContextEvidence.workspaceId, wsId),
          eq(marketingContextEvidence.contextId, contextRow.id)
        )
      );

    if (params.evidence.length > 0) {
      await db.insert(marketingContextEvidence).values(
        params.evidence.map((e) => ({
          id: generateSnowflake(),
          contextId: contextRow.id,
          workspaceId: wsId,
          evidenceId: e.evidenceId,
          kind: e.kind,
          sourceUrl: e.sourceUrl ?? null,
          capturedAt: e.capturedAt ? new Date(e.capturedAt) : null,
          capturedBy: e.capturedBy ?? null,
          confidence: e.confidence ?? "medium",
          trust: e.trust ?? "unreviewed",
          sensitivity: e.sensitivity ?? "internal",
        }))
      );
    }
  }

  // Update context root revision & provenance
  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      revision: nextRevision,
      status: "draft",
      updatedByUserId: userId,
      sourceSkillId: params.sourceSkillId !== undefined ? params.sourceSkillId : contextRow.sourceSkillId,
      sourceSkillVersion: params.sourceSkillVersion !== undefined ? params.sourceSkillVersion : contextRow.sourceSkillVersion,
      sourceSkillHash: params.sourceSkillHash !== undefined ? params.sourceSkillHash : contextRow.sourceSkillHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId,
    {
      id: params.sourceSkillId,
      version: params.sourceSkillVersion,
      hash: params.sourceSkillHash,
    }
  );

  return dto;
}

export async function updateOfferArchitectureService(
  ctx: TenantContext,
  params: UpdateOfferArchitectureParams
): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      offerArchitecture: params.offerArchitecture,
      revision: nextRevision,
      status: "draft",
      updatedByUserId: userId,
      sourceSkillId: params.sourceSkillId !== undefined ? params.sourceSkillId : contextRow.sourceSkillId,
      sourceSkillVersion: params.sourceSkillVersion !== undefined ? params.sourceSkillVersion : contextRow.sourceSkillVersion,
      sourceSkillHash: params.sourceSkillHash !== undefined ? params.sourceSkillHash : contextRow.sourceSkillHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId,
    {
      id: params.sourceSkillId,
      version: params.sourceSkillVersion,
      hash: params.sourceSkillHash,
    }
  );

  return dto;
}

export async function updateTwelveWeekPlanService(
  ctx: TenantContext,
  params: UpdateTwelveWeekPlanParams
): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      twelveWeekPlan: params.twelveWeekPlan,
      revision: nextRevision,
      status: "draft",
      updatedByUserId: userId,
      sourceSkillId: params.sourceSkillId !== undefined ? params.sourceSkillId : contextRow.sourceSkillId,
      sourceSkillVersion: params.sourceSkillVersion !== undefined ? params.sourceSkillVersion : contextRow.sourceSkillVersion,
      sourceSkillHash: params.sourceSkillHash !== undefined ? params.sourceSkillHash : contextRow.sourceSkillHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId,
    {
      id: params.sourceSkillId,
      version: params.sourceSkillVersion,
      hash: params.sourceSkillHash,
    }
  );

  return dto;
}

export async function submitForReviewService(
  ctx: TenantContext,
  params?: SubmitForReviewParams
): Promise<MarketingContextDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params?.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      status: "review_required",
      revision: nextRevision,
      updatedByUserId: userId,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId
  );

  return dto;
}

export async function approveContextService(
  ctx: TenantContext,
  params?: ApproveContextParams
): Promise<MarketingContextDTO> {
  const isFounder =
    ctx.permissions.includes("*") ||
    ctx.membershipRole === "founder" ||
    ctx.membershipRole === "co-founder";

  if (!isFounder) {
    throw APIError.permissionDenied(
      "chỉ founder/co-founder mới có quyền duyệt marketing context"
    );
  }

  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params?.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);
  const now = new Date();

  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      status: "approved",
      reviewedByUserId: userId,
      reviewedAt: now,
      revision: nextRevision,
      updatedByUserId: userId,
      updatedAt: now,
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const dto = await assembleContextDTO(updatedContext, ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    dto,
    userId
  );

  return dto;
}
