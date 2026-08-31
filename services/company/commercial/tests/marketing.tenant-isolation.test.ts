import { describe, expect, it } from "vitest";
import { MarketingContextQuery } from "../application/marketing/context-query";
import { DrizzleMarketingRepository } from "../infrastructure/marketing/drizzle-marketing.repository";
import { MarketingContextDomainModel } from "../domain/marketing/marketing-context";

class MultiTenantMarketingRepo extends DrizzleMarketingRepository {
  private store: MarketingContextDomainModel[] = [];

  override async getContext(workspaceId: string): Promise<MarketingContextDomainModel | null> {
    return this.store.find((c) => c.workspaceId === workspaceId) || null;
  }

  addContext(ctx: MarketingContextDomainModel) {
    this.store.push(ctx);
  }
}

describe("Marketing Tenant Isolation Tests", () => {
  it("strictly scopes marketing context by workspace ID", async () => {
    const repo = new MultiTenantMarketingRepo();
    const query = new MarketingContextQuery(repo);

    repo.addContext({
      id: "ctx_ws1",
      workspaceId: "ws_alpha",
      revision: 1,
      status: "draft",
      updatedByUserId: "u1",
      reviewedByUserId: null,
      reviewedAt: null,
      sourceSkillId: null,
      sourceSkillVersion: null,
      sourceSkillHash: null,
      productMarketing: {
        category: "Alpha Category",
        positioningStatement: "Alpha Positioning",
        alternatives: [],
        differentiators: [],
        brandVoice: {},
      },
      icpSegments: [],
      customerResearchThemes: [],
      customerLanguage: [],
      evidence: [],
      offerArchitecture: null,
      twelveWeekPlan: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });

    const ctxAlpha = await query.getContext("ws_alpha");
    expect(ctxAlpha).not.toBeNull();
    expect(ctxAlpha?.workspaceId).toBe("ws_alpha");
    expect(ctxAlpha?.productMarketing.category).toBe("Alpha Category");

    const ctxBeta = await query.getContext("ws_beta");
    expect(ctxBeta).toBeNull();
  });
});
