import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import {
  recordEvidenceInWorkspace,
  getEvidenceInWorkspace,
  updateEvidenceInWorkspace,
  deleteEvidenceInWorkspace,
} from "../strategy/services/evidence-lifecycle.service";
import { reviewEvidenceInWorkspace } from "../strategy/services/evidence-review.service";

describe("Evidence Lifecycle & Review Services", () => {
  it("creates candidate evidence, isolates cross-workspace lookup, and requires privileged review", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "member" });
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project A",
    });

    const ctxA_Member = makeTenantContext(wsA, { membershipRole: "member" });
    const ctxA_Founder = makeTenantContext(wsA, { membershipRole: "founder" });
    const ctxB_Member = makeTenantContext({ workspaceId: wsB.workspaceId, userId: wsA.userId }, { membershipRole: "member" });

    const evidenceA = await recordEvidenceInWorkspace(ctxA_Member, {
      projectId: projectA.id,
      sourceType: "interview",
      claim: "Customers prefer fast onboarding",
      sampleSize: 10,
    });

    expect(evidenceA.id).toBeDefined();
    expect(evidenceA.status).toBe("candidate");
    expect(evidenceA.workspaceId).toBe(wsA.workspaceId);

    // Same workspace lookup succeeds
    const fetched = await getEvidenceInWorkspace(ctxA_Member, evidenceA.id);
    expect(fetched.id).toBe(evidenceA.id);

    // Cross-workspace lookup throws not_found
    await expect(getEvidenceInWorkspace(ctxB_Member, evidenceA.id)).rejects.toMatchObject({
      code: "not_found",
    });

    // Non-privileged review attempt fails
    await expect(
      reviewEvidenceInWorkspace(ctxA_Member, {
        id: evidenceA.id,
        action: "approve",
        comment: "Looks solid",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // Privileged review succeeds
    const approved = await reviewEvidenceInWorkspace(ctxA_Founder, {
      id: evidenceA.id,
      action: "approve",
      comment: "Approved by founder",
    });
    expect(approved.status).toBe("approved");

    // Updating approved evidence by regular member fails
    await expect(
      updateEvidenceInWorkspace(ctxA_Member, approved.id, {
        claim: "Tampered claim",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // Updating approved evidence by founder succeeds
    const updated = await updateEvidenceInWorkspace(ctxA_Founder, approved.id, {
      claim: "Updated valid claim",
    });
    expect(updated.claim).toBe("Updated valid claim");

    // Soft delete removes from get
    await deleteEvidenceInWorkspace(ctxA_Founder, approved.id);
    await expect(getEvidenceInWorkspace(ctxA_Founder, approved.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });
});
