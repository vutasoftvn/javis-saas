import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  assembleContextDTO,
  getOrCreateContextRow,
  MarketingContextDTO,
  recordRevisionSnapshot,
  verifyOptimisticLock,
} from "./marketing-snapshot.service";

const {
  marketingContexts,
  marketingIcpSegments,
  marketingCustomerResearchThemes,
  marketingCustomerLanguage,
  marketingContextEvidence,
} = schema;

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
