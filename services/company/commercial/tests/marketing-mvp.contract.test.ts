import { describe, expect, it } from "vitest";
import { MarketingContextDomainModel } from "../domain/marketing/marketing-context";

describe("Marketing MVP Contract Tests", () => {
  it("conforms to marketing context contract shape", () => {
    const sample: MarketingContextDomainModel = {
      id: "ctx_123",
      workspaceId: "ws_456",
      revision: 1,
      status: "draft",
      updatedByUserId: "user_789",
      reviewedByUserId: null,
      reviewedAt: null,
      sourceSkillId: null,
      sourceSkillVersion: null,
      sourceSkillHash: null,
      productMarketing: {
        category: "Enterprise Software",
        positioningStatement: "Operations automation",
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
      createdAt: "2026-08-31T12:00:00.000Z",
      updatedAt: "2026-08-31T12:00:00.000Z",
    };

    expect(typeof sample.id).toBe("string");
    expect(typeof sample.workspaceId).toBe("string");
    expect(typeof sample.revision).toBe("number");
    expect(sample.productMarketing.category).toBe("Enterprise Software");
  });
});
