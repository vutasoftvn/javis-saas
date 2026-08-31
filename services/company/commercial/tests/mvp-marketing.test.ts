import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  createCampaignMvpService,
  createExperimentMvpService,
  createObjectiveService,
  getMarketingContextMvpService,
  getObservedMetricsMvpService,
  listAssetsMvpService,
  listCampaignsMvpService,
  listExperimentsMvpService,
  listObjectivesService,
  updateMarketingContextMvpService,
} from "../services/marketing-mvp.service";
import { TenantContext } from "../../shared/types/tenant_context";

describe("Commercial Marketing MVP Services", () => {
  it("supports context get and update with honest empty state", async () => {
    const wsA = await createTestSession({
      displayName: "Marketing Founder A",
      role: "founder",
    });
    const ctxA: TenantContext = {
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-marketing-a",
    };

    // 1. Initial get is empty
    const initRes = await getMarketingContextMvpService(ctxA);
    expect(initRes.meta.dataState).toBe("empty");

    // 2. Update context
    const updatedRes = await updateMarketingContextMvpService(ctxA, {
      category: "AI Marketing Engine",
      positioningStatement: "Lead gen for SaaS",
    });
    expect(updatedRes.meta.dataState).toBe("populated");
    expect(updatedRes.data.productMarketing.category).toBe("AI Marketing Engine");
    expect(updatedRes.data.productMarketing.positioningStatement).toBe("Lead gen for SaaS");

    // 3. Get context reflects update
    const fetchedRes = await getMarketingContextMvpService(ctxA);
    expect(fetchedRes.meta.dataState).toBe("populated");
    expect(fetchedRes.data.productMarketing.category).toBe("AI Marketing Engine");
  });

  it("supports objectives, campaigns, assets, and experiments lifecycle with tenant isolation", async () => {
    const wsA = await createTestSession({
      displayName: "Marketing WS A",
      role: "founder",
    });
    const wsB = await createTestSession({
      displayName: "Marketing WS B",
      role: "founder",
    });

    const ctxA: TenantContext = {
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-mkt-a",
    };
    const ctxB: TenantContext = {
      workspaceId: wsB.workspaceId,
      userId: wsB.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-mkt-b",
    };

    // 1. Objectives
    const objRes = await createObjectiveService(ctxA, {
      title: "Q4 Lead Generation",
      targetMetric: "qualified_leads",
      targetValue: 500,
    });
    expect(objRes.data.title).toBe("Q4 Lead Generation");
    expect(objRes.data.currentValue).toBeNull();

    const listObjA = await listObjectivesService(ctxA);
    expect(listObjA.data.length).toBe(1);

    const listObjB = await listObjectivesService(ctxB);
    expect(listObjB.data.length).toBe(0);

    // 2. Campaigns
    const campRes = await createCampaignMvpService(ctxA, {
      name: "Product Launch Q4",
      budget: 10000000,
      funnelStage: "discover",
    });
    expect(campRes.data.name).toBe("Product Launch Q4");
    expect(campRes.data.budget).toBe(10000000);

    const listCampA = await listCampaignsMvpService(ctxA);
    expect(listCampA.data.length).toBe(1);
    const listCampB = await listCampaignsMvpService(ctxB);
    expect(listCampB.data.length).toBe(0);

    // 3. Experiments
    const expRes = await createExperimentMvpService(ctxA, {
      campaignId: campRes.data.id,
      name: "Hero Headline A/B Test",
      hypothesis: "Direct value prop increases signups by 20%",
      baselineValue: 5.2,
      targetValue: 6.5,
    });
    expect(expRes.data.name).toBe("Hero Headline A/B Test");

    const listExpA = await listExperimentsMvpService(ctxA);
    expect(listExpA.data.length).toBe(1);
    const listExpB = await listExperimentsMvpService(ctxB);
    expect(listExpB.data.length).toBe(0);

    // 4. Observed metrics
    const obsMetrics = await getObservedMetricsMvpService(ctxA);
    expect(obsMetrics.data).toBeDefined();
    expect(obsMetrics.meta.sources[0].kind).toBe("external_connector");
  });
});
