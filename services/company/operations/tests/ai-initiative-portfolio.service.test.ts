import { describe, it, expect } from "vitest";
import { sql, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import { createAiInitiativeInWorkspace } from "../services/initiative.service";
import { recordValueContract, setBudgetPolicy } from "../services/ai-initiative-evidence.service";
import { getAiInitiativePortfolio } from "../services/ai-initiative-portfolio.service";
import type { TenantContext } from "../../shared/types/tenant_context";

async function seedHumanMember(wsId: string, userId: string): Promise<string> {
  const memberId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO core.workforce_members (id, workspace_id, member_type, human_user_id, role_title, status)
    VALUES (${memberId}, ${BigInt(wsId)}, 'HUMAN', ${BigInt(userId)}, 'Founder', 'active')
  `);
  return memberId.toString();
}

function makeTenantContext(wsId: string, userId: string, memberId?: string): TenantContext {
  return {
    workspaceId: wsId,
    userId,
    workforceMemberId: memberId,
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "test-corr-portfolio",
  };
}

describe("AI Initiative Portfolio Service", () => {
  it("returns truthful baseline null and nextRequiredGate without cross-project leakage", async () => {
    const ws = await createTestWorkspaceWithMember();
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);

    // Create an AI initiative without baseline
    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Portfolio Test Initiative",
      businessOwnerMemberId: memberId,
      keyResultIds: [okr.keyResultId],
      riskTier: "LOW",
      autonomyTier: "A1",
    });

    const portfolio = await getAiInitiativePortfolio(ctx, ws.projectId);
    expect(portfolio.projectId).toBe(ws.projectId);
    expect(portfolio.workspaceId).toBe(ws.workspaceId);
    expect(portfolio.items.length).toBe(1);

    const item = portfolio.items[0];
    expect(item.initiativeId).toBe(init.id);
    expect(item.title).toBe("Portfolio Test Initiative");
    expect(item.baselineMetricValue).toBeNull(); // Truthful null, not 0
    expect(item.authorizedActions).not.toContain("scale_initiative");
    expect(item.nextRequiredGate).toBe("PILOT_PROMOTION_APPROVAL");

    // Record value contract with baseline
    await recordValueContract(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "csat-metric",
      unit: "points",
      baselineValue: "72.5",
      targetValue: "85.0",
      baselineSourceRef: "audit_ref_123",
      measurementOwnerMemberId: memberId,
    });

    // Record budget policy
    await setBudgetPolicy(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      softCostThreshold: "400.00",
      hardCostThreshold: "500.00",
    });

    const updatedPortfolio = await getAiInitiativePortfolio(ctx, ws.projectId);
    const updatedItem = updatedPortfolio.items[0];
    expect(updatedItem.baselineMetricValue).toBe("72.5");
    expect(updatedItem.targetMetricValue).toBe("85");
    expect(updatedItem.costBudgetStatus).toBe("OK");

    // Scoped containment: another project has 0 items
    const otherProjectId = generateSnowflake().toString();
    const otherPortfolio = await getAiInitiativePortfolio(ctx, otherProjectId);
    expect(otherPortfolio.items.length).toBe(0);
  });
});
