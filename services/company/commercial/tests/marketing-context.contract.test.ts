import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  getMarketingContext,
  updateProductMarketing,
  updateCustomerResearch,
  updateOfferArchitecture,
  updateTwelveWeekPlan,
  submitMarketingContextForReview,
  approveMarketingContext,
} from "../handlers/marketing-context.handler";

describe("Commercial Marketing Context API Contract", () => {
  it("rejects when caller lacks authorization or workspace access", async () => {
    const user = await createTestSession({
      email: `mctx-unauth-${Date.now()}@example.com`,
      displayName: "Unauth User",
    });

    // Missing authorization header
    await expect(
      getMarketingContext({
        workspaceId: user.workspaceId,
      })
    ).rejects.toThrow();

    const outsider = await createTestSession({
      email: `mctx-outsider-${Date.now()}@example.com`,
      displayName: "Outsider User",
    });

    // Cross-workspace membership rejection
    await expect(
      getMarketingContext({
        workspaceId: user.workspaceId,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow(/không thuộc workspace/i);
  });

  it("initializes and retrieves default canonical marketing context", async () => {
    const user = await createTestSession({
      displayName: "Founder User",
      role: "founder",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const context = await getMarketingContext({
      workspaceId: user.workspaceId,
      authorization,
    });

    expect(context).toBeDefined();
    expect(context.id).toBeDefined();
    expect(context.workspaceId).toBe(user.workspaceId);
    expect(context.revision).toBe(1);
    expect(context.status).toBe("draft");
    expect(context.productMarketing).toBeDefined();
    expect(context.icpSegments).toEqual([]);
    expect(context.customerResearchThemes).toEqual([]);
    expect(context.customerLanguage).toEqual([]);
    expect(context.evidence).toEqual([]);
  });

  it("updates product marketing, increments revision and captures snapshot", async () => {
    const user = await createTestSession({
      displayName: "PM User",
      role: "admin",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const updated = await updateProductMarketing({
      workspaceId: user.workspaceId,
      authorization,
      category: "AI SaaS Automation",
      positioningStatement: "The all-in-one AI operating system for modern founders.",
      alternatives: ["Manual spreadsheets", "Agency retainer"],
      differentiators: ["Closed-loop execution", "Deterministic finance guards"],
      brandVoice: { tone: "Bold & Confident", traits: ["Precise", "Analytical"] },
      expectedRevision: 1,
      sourceSkillId: "marketing.positioning",
      sourceSkillVersion: "1.1.0",
      sourceSkillHash: "b1aaa3619e747f4a836c61e03084c4a531de1262",
    });

    expect(updated.revision).toBe(2);
    expect(updated.status).toBe("draft");
    expect(updated.productMarketing.category).toBe("AI SaaS Automation");
    expect(updated.productMarketing.positioningStatement).toContain("all-in-one AI operating system");
    expect(updated.productMarketing.alternatives).toHaveLength(2);
    expect(updated.productMarketing.differentiators).toHaveLength(2);
    expect(updated.sourceSkillId).toBe("marketing.positioning");
    expect(updated.sourceSkillVersion).toBe("1.1.0");
  });

  it("updates customer research with structured taxonomy evidence, icp, themes, and quotes", async () => {
    const user = await createTestSession({
      displayName: "Research User",
      role: "admin",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const updated = await updateCustomerResearch({
      workspaceId: user.workspaceId,
      authorization,
      icpSegments: [
        { segment: "Early-stage B2B SaaS Founders", confidence: "high", evidenceIds: ["ev-001"] },
      ],
      themes: [
        { type: "pain", summary: "Marketing workflows are fragmented across 10+ tabs", confidence: "high", evidenceIds: ["ev-001"] },
        { type: "jtbd", summary: "Automate inbound lead qualification without hiring SDRs", confidence: "medium", evidenceIds: [] },
      ],
      quotes: [
        { quote: "I spend 3 hours a day just copying data between CRM and email tools.", sourceId: "interview-12" },
      ],
      evidence: [
        {
          evidenceId: "ev-001",
          kind: "customer_interview",
          sourceUrl: "https://notes.internal/interview-12",
          capturedBy: "user:founder",
          confidence: "high",
          trust: "verified",
          sensitivity: "internal",
        },
      ],
      expectedRevision: 1,
    });

    expect(updated.revision).toBe(2);
    expect(updated.icpSegments).toHaveLength(1);
    expect(updated.icpSegments[0].segment).toBe("Early-stage B2B SaaS Founders");
    expect(updated.customerResearchThemes).toHaveLength(2);
    expect(updated.customerLanguage).toHaveLength(1);
    expect(updated.customerLanguage[0].quote).toContain("3 hours a day");
    expect(updated.evidence).toHaveLength(1);
    expect(updated.evidence[0].evidenceId).toBe("ev-001");
    expect(updated.evidence[0].trust).toBe("verified");
  });

  it("updates offer architecture and twelve-week plan jsonb blobs", async () => {
    const user = await createTestSession({
      displayName: "Offer User",
      role: "admin",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const step1 = await updateOfferArchitecture({
      workspaceId: user.workspaceId,
      authorization,
      offerArchitecture: {
        coreOffer: "Growth Accelerator Plan",
        pricingModel: "Per-seat monthly subscription with usage tier",
        guarantee: "30-day money-back guarantee",
      },
      expectedRevision: 1,
    });
    expect(step1.revision).toBe(2);
    expect(step1.offerArchitecture?.coreOffer).toBe("Growth Accelerator Plan");

    const step2 = await updateTwelveWeekPlan({
      workspaceId: user.workspaceId,
      authorization,
      twelveWeekPlan: {
        theme: "Launch Q3 Commercial Engine",
        weeklyGoals: [
          { week: 1, objective: "Finalize positioning and setup tracking" },
          { week: 2, objective: "Launch cold outreach and validate messaging" },
        ],
      },
      expectedRevision: 2,
    });
    expect(step2.revision).toBe(3);
    expect(step2.twelveWeekPlan?.weeklyGoals).toHaveLength(2);
  });

  it("aborts when expectedRevision encounters a conflict", async () => {
    const user = await createTestSession({
      displayName: "Conflict User",
      role: "admin",
    });
    const authorization = `Bearer ${user.accessToken}`;

    // First write: rev 1 -> 2
    await updateProductMarketing({
      workspaceId: user.workspaceId,
      authorization,
      category: "First Write",
      expectedRevision: 1,
    });

    // Stale write attempting expectedRevision 1 again -> must abort
    await expect(
      updateProductMarketing({
        workspaceId: user.workspaceId,
        authorization,
        category: "Stale Write",
        expectedRevision: 1,
      })
    ).rejects.toThrow(/revision conflict/i);
  });

  it("submits for review and enforces founder/co-founder approval gate", async () => {
    const member = await createTestSession({
      displayName: "Team Member",
      role: "member",
    });
    const authorizationMember = `Bearer ${member.accessToken}`;

    // Member submits for review
    const underReview = await submitMarketingContextForReview({
      workspaceId: member.workspaceId,
      authorization: authorizationMember,
      expectedRevision: 1,
    });

    expect(underReview.status).toBe("review_required");
    expect(underReview.revision).toBe(2);

    // Member attempts to approve -> permission denied
    await expect(
      approveMarketingContext({
        workspaceId: member.workspaceId,
        authorization: authorizationMember,
        expectedRevision: 2,
      })
    ).rejects.toThrow(/founder/i);

    // Founder approves
    const founder = await createTestSession({
      displayName: "Company Founder",
      role: "founder",
    });
    const authorizationFounder = `Bearer ${founder.accessToken}`;

    const approved = await approveMarketingContext({
      workspaceId: founder.workspaceId,
      authorization: authorizationFounder,
      expectedRevision: 1,
    });

    expect(approved.status).toBe("approved");
    expect(approved.reviewedByUserId).toBe(founder.userId);
    expect(approved.reviewedAt).toBeDefined();
    expect(approved.revision).toBe(2);
  });
});
