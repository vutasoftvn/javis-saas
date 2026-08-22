import { describe, it, expect } from "vitest";
import { createCampaign, listCampaigns, createAsset, createMarketingForm } from "../handlers/marketing.handler";

describe("Marketing Service", () => {
  const workspaceId = 400;

  it("creates a marketing campaign and lists it", async () => {
    const campaign = await createCampaign({
      workspaceId,
      name: "Q3 AI SaaS Launch Campaign",
      funnelStage: "discover",
      channels: ["facebook", "linkedin", "google_ads"],
      budget: 50000000,
    });

    expect(campaign.id).toBeDefined();
    expect(campaign.workspaceId).toBe(workspaceId);
    expect(campaign.name).toBe("Q3 AI SaaS Launch Campaign");
    expect(campaign.budget).toBe(50000000);

    const list = await listCampaigns({ workspaceId });
    expect(list.campaigns.some((c) => c.id === campaign.id)).toBe(true);
  });

  it("creates a campaign asset and marketing form", async () => {
    const campaign = await createCampaign({
      workspaceId,
      name: "Lead Magnet Campaign",
    });

    const asset = await createAsset({
      workspaceId,
      campaignId: campaign.id,
      assetType: "ad_copy",
      title: "Hero Banner Copy V1",
      content: "Transform your business with Autonomous AI Agents",
    });

    expect(asset.id).toBeDefined();
    expect(asset.campaignId).toBe(campaign.id);
    expect(asset.title).toBe("Hero Banner Copy V1");

    const form = await createMarketingForm({
      workspaceId,
      title: "Early Access Signup",
      slug: "early-access",
      isPublished: true,
    });

    expect(form.id).toBeDefined();
    expect(form.slug).toBe("early-access");
    expect(form.isPublished).toBe(true);
  });
});
