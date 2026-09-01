import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import {
  createStagePolicyInWorkspace,
  getStagePolicyInWorkspace,
  updateStagePolicyInWorkspace,
  deleteStagePolicyInWorkspace,
} from "../strategy/services/stage-policy.service";
import {
  createStageTransitionInWorkspace,
  getStageTransitionInWorkspace,
  listStageTransitionsInWorkspace,
  deleteStageTransitionInWorkspace,
} from "../strategy/services/stage-transition-config.service";
import {
  runGateEvaluationInWorkspace,
  getGateEvaluationInWorkspace,
  listGateEvaluationsInWorkspace,
} from "../strategy/services/gate-evaluation.service";

describe("Strategy Gate and Stage Policy Services", () => {
  it("governs stage policy creation by role and isolates cross-workspace", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "member" });
    const wsB = await createSecondWorkspace();

    const ctxA_Member = makeTenantContext(wsA, { membershipRole: "member" });
    const ctxA_Founder = makeTenantContext(wsA, { membershipRole: "founder" });
    const ctxB_Founder = makeTenantContext({ workspaceId: wsB.workspaceId, userId: wsA.userId }, { membershipRole: "founder" });

    // Non-privileged member cannot create policy
    await expect(
      createStagePolicyInWorkspace(ctxA_Member, {
        stageKey: "P1_PROBLEM_VALIDATION",
        minimumEvidenceScore: 0.7,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // Founder can create policy
    const policy = await createStagePolicyInWorkspace(ctxA_Founder, {
      stageKey: "P1_PROBLEM_VALIDATION",
      minimumEvidenceScore: 0.7,
    });
    expect(policy.id).toBeDefined();
    expect(policy.workspaceId).toBe(wsA.workspaceId);

    // Cross-workspace query fails
    await expect(getStagePolicyInWorkspace(ctxB_Founder, policy.id)).rejects.toMatchObject({
      code: "not_found",
    });

    // Update policy
    const updated = await updateStagePolicyInWorkspace(ctxA_Founder, policy.id, {
      minimumEvidenceScore: 0.8,
    });
    expect(updated.minimumEvidenceScore).toBe(0.8);

    // Delete policy
    await deleteStagePolicyInWorkspace(ctxA_Founder, policy.id);
    await expect(getStagePolicyInWorkspace(ctxA_Founder, policy.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("handles gate evaluations and stage transition configuration", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project Gate Test",
    });

    const ctxA = makeTenantContext(wsA, { membershipRole: "founder" });

    const policy = await createStagePolicyInWorkspace(ctxA, {
      stageKey: "P2_SOLUTION_VALIDATION",
      minimumEvidenceScore: 0.5,
    });

    const evalRes = await runGateEvaluationInWorkspace(ctxA, {
      projectId: projectA.id,
      stagePolicyId: policy.id,
    });
    expect(evalRes.id).toBeDefined();
    expect(evalRes.workspaceId).toBe(wsA.workspaceId);

    const fetchedEval = await getGateEvaluationInWorkspace(ctxA, evalRes.id);
    expect(fetchedEval.id).toBe(evalRes.id);

    const transition = await createStageTransitionInWorkspace(ctxA, {
      fromStage: "P1_PROBLEM_VALIDATION",
      toStage: "P2_SOLUTION_VALIDATION",
      policyId: policy.id,
      allowed: true,
    });
    expect(transition.id).toBeDefined();

    const fetchedTrans = await getStageTransitionInWorkspace(ctxA, transition.id);
    expect(fetchedTrans.id).toBe(transition.id);

    await deleteStageTransitionInWorkspace(ctxA, transition.id);
    await expect(getStageTransitionInWorkspace(ctxA, transition.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });
});
