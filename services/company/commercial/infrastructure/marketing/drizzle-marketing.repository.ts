import { and, eq } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  MarketingContextDomainModel,
  ProductMarketingDomain,
  IcpSegmentDomain,
  CustomerResearchThemeDomain,
  CustomerLanguageDomain,
  MarketingEvidenceDomain,
} from "../../domain/marketing/marketing-context";

const {
  marketingContexts,
  marketingProductMarketing,
  marketingIcpSegments,
  marketingCustomerResearchThemes,
  marketingCustomerLanguage,
  marketingContextEvidence,
} = schema;

export class DrizzleMarketingRepository {
  async getContext(workspaceId: string): Promise<MarketingContextDomainModel | null> {
    const wsId = BigInt(workspaceId);
    const [contextRow] = await db
      .select()
      .from(marketingContexts)
      .where(eq(marketingContexts.workspaceId, wsId))
      .limit(1);

    if (!contextRow) {
      return null;
    }

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

    const productMarketing: ProductMarketingDomain = {
      category: pmRow?.category ?? null,
      positioningStatement: pmRow?.positioningStatement ?? null,
      alternatives: (pmRow?.alternatives as readonly Record<string, unknown>[]) ?? [],
      differentiators: (pmRow?.differentiators as readonly Record<string, unknown>[]) ?? [],
      brandVoice: (pmRow?.brandVoice as Record<string, unknown>) ?? {},
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

    const icpSegments: readonly IcpSegmentDomain[] = icpRows.map((r) => ({
      id: String(r.id),
      segment: r.segment,
      confidence: r.confidence,
      evidenceIds: (r.evidenceIds as readonly string[]) ?? [],
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

    const customerResearchThemes: readonly CustomerResearchThemeDomain[] = themeRows.map((r) => ({
      id: String(r.id),
      type: r.type,
      summary: r.summary,
      confidence: r.confidence,
      evidenceIds: (r.evidenceIds as readonly string[]) ?? [],
    }));

    // 4. Customer Language
    const langRows = await db
      .select()
      .from(marketingCustomerLanguage)
      .where(
        and(
          eq(marketingCustomerLanguage.workspaceId, wsId),
          eq(marketingCustomerLanguage.contextId, contextId)
        )
      );

    const customerLanguage: readonly CustomerLanguageDomain[] = langRows.map((r) => ({
      id: String(r.id),
      quote: r.quote,
      sourceId: r.sourceId ? String(r.sourceId) : null,
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

    const evidence: readonly MarketingEvidenceDomain[] = evidenceRows.map((r) => ({
      id: String(r.id),
      evidenceId: r.evidenceId,
      kind: r.kind,
      sourceUrl: r.sourceUrl,
      capturedAt: r.capturedAt ? r.capturedAt.toISOString() : null,
      capturedBy: r.capturedBy ? String(r.capturedBy) : null,
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
      offerArchitecture: (contextRow.offerArchitecture as Record<string, unknown>) ?? null,
      twelveWeekPlan: (contextRow.twelveWeekPlan as Record<string, unknown>) ?? null,
      createdAt: contextRow.createdAt.toISOString(),
      updatedAt: contextRow.updatedAt.toISOString(),
    };
  }

  async getOrCreateContext(workspaceId: string, actorUserId: string): Promise<MarketingContextDomainModel> {
    const existing = await this.getContext(workspaceId);
    if (existing) return existing;

    const wsId = BigInt(workspaceId);
    const contextId = generateSnowflake();
    const now = new Date();

    await db.insert(marketingContexts).values({
      id: contextId,
      workspaceId: wsId,
      revision: 1,
      status: "draft",
      updatedByUserId: actorUserId ? BigInt(actorUserId) : null,
      offerArchitecture: {},
      twelveWeekPlan: {},
      createdAt: now,
      updatedAt: now,
    });

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

    const created = await this.getContext(workspaceId);
    if (!created) throw new Error("Failed to create marketing context");
    return created;
  }
}
