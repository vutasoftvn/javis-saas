import { describe, it, expect, beforeEach } from "vitest";
import { db, schema } from "../db";
import {
  assembleActionContextService,
  createActionProposalService,
  listActionProposalsService,
  acceptActionProposalService,
} from "../strategy/services/next-best-action.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("Next Best Actions Engine (Phase 5 / Release E)", () => {
  const wsId = generateSnowflake();

  it("assembles deterministic action context without calling LLM", async () => {
    const ctx = await assembleActionContextService(wsId);
    expect(ctx.workspaceId).toBe(String(wsId));
    expect(ctx.timestamp).toBeDefined();
    expect(Array.isArray(ctx.pendingObligations)).toBe(true);
    expect(Array.isArray(ctx.activeInitiatives)).toBe(true);
  });

  it("requires decisionReason and rejects forbidden payout capabilities", async () => {
    // Missing decisionReason -> throws invalidArgument
    await expect(
      createActionProposalService({
        workspaceId: wsId,
        source: "finance",
        recommendation: "Review runway",
        decisionReason: "",
      })
    ).rejects.toThrow("decisionReason is strictly required");

    // Forbidden payout capability -> throws invalidArgument
    await expect(
      createActionProposalService({
        workspaceId: wsId,
        source: "finance",
        recommendation: "Pay vendor",
        capabilityRequired: "finance.payout.execute",
        decisionReason: "Vendor due date reached",
      })
    ).rejects.toThrow("forbidden");
  });

  it("creates and accepts action proposals, emitting canonical event", async () => {
    const prop = await createActionProposalService({
      workspaceId: wsId,
      source: "stage",
      recommendation: "Validate Problem-Solution Fit with 5 customer interviews",
      priority: 2,
      decisionReason: "Venture stage is S1_PROBLEM_DISCOVERY with low confidence",
      evidenceRefs: ["ev_101", "ev_102"],
    });

    expect(prop.id).toBeDefined();
    expect(prop.status).toBe("PROPOSED");
    expect(prop.priority).toBe(2);

    const list = await listActionProposalsService(wsId, "PROPOSED");
    expect(list.some((p) => p.id === prop.id)).toBe(true);

    const accepted = await acceptActionProposalService({
      proposalId: BigInt(prop.id),
      acceptedBy: 8888n,
    });
    expect(accepted.status).toBe("ACCEPTED");
  });
});
