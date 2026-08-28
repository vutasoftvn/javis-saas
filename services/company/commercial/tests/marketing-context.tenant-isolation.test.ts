import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  getMarketingContext,
  updateProductMarketing,
} from "../handlers/marketing-context.handler";
import { getMarketingContextService } from "../services/marketing-context.service";

describe("Commercial Marketing Context Tenant Isolation", () => {
  it("strictly isolates marketing context across tenants", async () => {
    const wsA = await createTestSession({
      displayName: "Tenant A Founder",
      role: "founder",
    });
    const wsB = await createTestSession({
      displayName: "Tenant B Founder",
      role: "founder",
    });

    // Tenant A populates product marketing
    await updateProductMarketing({
      workspaceId: wsA.workspaceId,
      authorization: `Bearer ${wsA.accessToken}`,
      category: "Secret Platform for Tenant A",
      positioningStatement: "Strictly confidential positioning A",
    });

    // Tenant B populates product marketing with different info
    await updateProductMarketing({
      workspaceId: wsB.workspaceId,
      authorization: `Bearer ${wsB.accessToken}`,
      category: "Public Platform for Tenant B",
      positioningStatement: "Public positioning B",
    });

    // 1. Handler level: User B cannot access Tenant A's workspace
    await expect(
      getMarketingContext({
        workspaceId: wsA.workspaceId,
        authorization: `Bearer ${wsB.accessToken}`,
      })
    ).rejects.toThrow(/không thuộc workspace/i);

    // 2. Service level: ctxB only retrieves Tenant B's data
    const ctxBContext = await getMarketingContextService({
      workspaceId: wsB.workspaceId,
      userId: wsB.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-b",
    });

    expect(ctxBContext.workspaceId).toBe(wsB.workspaceId);
    expect(ctxBContext.productMarketing.category).toBe("Public Platform for Tenant B");
    expect(ctxBContext.productMarketing.positioningStatement).toBe("Public positioning B");
    expect(ctxBContext.productMarketing.category).not.toContain("Tenant A");

    // 3. Service level: ctxA only retrieves Tenant A's data
    const ctxAContext = await getMarketingContextService({
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "test-corr-a",
    });

    expect(ctxAContext.workspaceId).toBe(wsA.workspaceId);
    expect(ctxAContext.productMarketing.category).toBe("Secret Platform for Tenant A");
    expect(ctxAContext.productMarketing.positioningStatement).toBe("Strictly confidential positioning A");
  });
});
