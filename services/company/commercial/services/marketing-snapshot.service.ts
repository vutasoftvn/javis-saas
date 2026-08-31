import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { ProductMarketingDTO } from "./product-marketing.service";
import type {
  CustomerLanguageDTO,
  CustomerResearchThemeDTO,
  IcpSegmentDTO,
  MarketingContextEvidenceDTO,
} from "./customer-research.service";

const {
  marketingContexts,
  marketingContextRevisions,
  marketingProductMarketing,
  marketingIcpSegments,
  marketingCustomerResearchThemes,
  marketingCustomerLanguage,
  marketingContextEvidence,
} = schema;

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

export async function getOrCreateContextRow(ctx: TenantContext) {
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

export async function assembleContextDTO(
  contextRow: typeof marketingContexts.$inferSelect,
  ctx: TenantContext
): Promise<MarketingContextDTO> {
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

export async function recordRevisionSnapshot(
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

export function verifyOptimisticLock(currentRevision: number, expectedRevision?: number) {
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
