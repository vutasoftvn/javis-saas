import { describe, it, expect } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createCampaign, listCampaigns, createAsset, createMarketingForm } from "../handlers/marketing.handler";

describe("Marketing Service", () => {
  it("creates a marketing campaign and lists it", async () => {
    const user = await createTestSession({
      email: `marketing-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Marketing Test",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const campaign = await createCampaign({
      workspaceId: user.workspaceId,
      name: "Q3 AI SaaS Launch Campaign",
      funnelStage: "discover",
      channels: ["facebook", "linkedin", "google_ads"],
      budget: 50000000,
      authorization,
    });

    expect(campaign.id).toBeDefined();
    expect(campaign.workspaceId).toBe(user.workspaceId);
    expect(campaign.name).toBe("Q3 AI SaaS Launch Campaign");
    expect(campaign.budget).toBe(50000000);

    const list = await listCampaigns({ workspaceId: user.workspaceId, authorization });
    expect(list.campaigns.some((c) => c.id === campaign.id)).toBe(true);
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const owner = await createTestSession({
      email: `marketing-owner-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Marketing Owner",
    });
    const outsider = await createTestSession({
      email: `marketing-outsider-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Marketing Outsider",
    });

    await expect(
      createCampaign({
        workspaceId: owner.workspaceId,
        name: "Should be blocked",
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("creates a campaign asset and marketing form", async () => {
    const user = await createTestSession({
      email: `marketing-asset-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Marketing Asset Test",
    });
    const authorization = `Bearer ${user.accessToken}`;
    const slug = `early-access-${Date.now()}`;

    const campaign = await createCampaign({
      workspaceId: user.workspaceId,
      name: "Lead Magnet Campaign",
      authorization,
    });

    const asset = await createAsset({
      workspaceId: user.workspaceId,
      campaignId: campaign.id,
      assetType: "ad_copy",
      title: "Hero Banner Copy V1",
      content: "Transform your business with Autonomous AI Agents",
      authorization,
    });

    expect(asset.id).toBeDefined();
    expect(asset.campaignId).toBe(campaign.id);
    expect(asset.title).toBe("Hero Banner Copy V1");

    const form = await createMarketingForm({
      workspaceId: user.workspaceId,
      title: "Early Access Signup",
      slug,
      isPublished: true,
      authorization,
    });

    expect(form.id).toBeDefined();
    expect(form.slug).toBe(slug);
    expect(form.isPublished).toBe(true);
  });
});
