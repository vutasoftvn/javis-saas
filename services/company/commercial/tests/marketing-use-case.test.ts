import { describe, expect, it } from "vitest";
import { MarketingContextQuery } from "../application/marketing/context-query";
import { DrizzleMarketingRepository } from "../infrastructure/marketing/drizzle-marketing.repository";
import { MarketingContextDomainModel } from "../domain/marketing/marketing-context";

class FakeMarketingRepo extends DrizzleMarketingRepository {
  private store: MarketingContextDomainModel[] = [];

  override async getContext(workspaceId: string): Promise<MarketingContextDomainModel | null> {
    return this.store.find((c) => c.workspaceId === workspaceId) || null;
  }

  override async getOrCreateContext(workspaceId: string, actorUserId: string): Promise<MarketingContextDomainModel> {
    const existing = await this.getContext(workspaceId);
    if (existing) return existing;

    const ctx: MarketingContextDomainModel = {
      id: "ctx_101",
      workspaceId,
      revision: 1,
      status: "draft",
      updatedByUserId: actorUserId,
      reviewedByUserId: null,
      reviewedAt: null,
      sourceSkillId: null,
      sourceSkillVersion: null,
      sourceSkillHash: null,
      productMarketing: {
        category: "B2B SaaS",
        positioningStatement: "AI-first operations",
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
    };
    this.store.push(ctx);
    return ctx;
  }
}

describe("Marketing Context Application Use Cases", () => {
  it("returns null when workspace has no marketing context", async () => {
    const fakeRepo = new FakeMarketingRepo();
    const query = new MarketingContextQuery(fakeRepo);

    const ctx = await query.getContext("ws_empty");
    expect(ctx).toBeNull();
  });

  it("retrieves populated marketing context truthfully", async () => {
    const fakeRepo = new FakeMarketingRepo();
    await fakeRepo.getOrCreateContext("ws_active", "user_1");

    const query = new MarketingContextQuery(fakeRepo);
    const ctx = await query.getContext("ws_active");

    expect(ctx).not.toBeNull();
    expect(ctx?.productMarketing.category).toBe("B2B SaaS");
    expect(ctx?.productMarketing.positioningStatement).toBe("AI-first operations");
  });
});
