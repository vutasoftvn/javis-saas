import { describe, it, expect, beforeEach } from "vitest";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
} from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  createProductDecisionDossier,
  appendProductDecisionRevision,
  readProductDecisionSnapshot,
} from "../services/product-decision-dossier.service";

describe("Product Decision Dossier Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let agentCtx: TenantContext;
  let foreignCtx: TenantContext;
  let projectId: string;
  let dossierId: string;

  const draft = {
    assumptions: ["users churn due to onboarding friction"],
    evidenceRefs: [
      { sourceRef: "interview://cust-42", classification: "customer_interview", redactedExcerpt: "onboarding was confusing" },
    ],
    reasonCode: "PRODUCT_DECISION_DRAFT",
  };

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    projectId = ws.projectId;
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });

    const member = await addMemberToWorkspace(ws.workspaceId, "member");
    memberCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: member.userId,
      workforceMemberId: member.userId,
      membershipRole: "member",
      isAiAgent: false,
    });

    agentCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: "ai-agent-user",
      workforceMemberId: "ai-workforce-member",
      membershipRole: "member",
      isAiAgent: true,
    });

    const secondWs = await createSecondWorkspace();
    foreignCtx = makeTestTenantContext({
      workspaceId: secondWs.workspaceId,
      userId: "foreign-user",
      membershipRole: "founder",
      isAiAgent: false,
    });

    const created = await createProductDecisionDossier(founderCtx, {
      projectId,
      title: "Pivot onboarding flow",
      assumptions: draft.assumptions,
      evidenceRefs: draft.evidenceRefs,
      reasonCode: "INITIAL_DRAFT",
    });
    dossierId = created.dossierId;
  });

  it("requires project membership and never confirms a model-authored product decision", async () => {
    await expect(readProductDecisionSnapshot(foreignCtx, projectId)).rejects.toMatchObject({
      code: "permission_denied",
    });
    await expect(
      appendProductDecisionRevision(agentCtx, dossierId, 1, draft)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("agent context can never create a dossier either", async () => {
    await expect(
      createProductDecisionDossier(agentCtx, { projectId, title: "Agent attempt", reasonCode: "x" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("creates a dossier as revision 1 in DRAFT status", async () => {
    expect(dossierId).toBeTruthy();
    const snapshot = await readProductDecisionSnapshot(founderCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.revision).toBe(1);
    expect(snapshot.status).toBe("DRAFT");
    expect(snapshot.evidenceRefs).toHaveLength(1);
    expect(snapshot.evidenceRefs[0]).toMatchObject({
      sourceRef: "interview://cust-42",
      classification: "customer_interview",
    });
  });

  it("a human member can append a DRAFT revision with CAS, and stale CAS is rejected", async () => {
    const appended = await appendProductDecisionRevision(memberCtx, dossierId, 1, {
      assumptions: ["revised assumption"],
      evidenceRefs: [],
      reasonCode: "REVISED_AFTER_MORE_INTERVIEWS",
    });
    expect(appended.revision).toBe(2);
    expect(appended.status).toBe("DRAFT");

    await expect(
      appendProductDecisionRevision(memberCtx, dossierId, 1, { reasonCode: "stale" })
    ).rejects.toMatchObject({ code: "aborted" });
  });

  it("only a human founder can confirm a product decision revision", async () => {
    await expect(
      appendProductDecisionRevision(memberCtx, dossierId, 1, {
        status: "CONFIRMED",
        reasonCode: "member cannot confirm",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const confirmed = await appendProductDecisionRevision(founderCtx, dossierId, 1, {
      status: "CONFIRMED",
      reasonCode: "founder confirms after review",
    });
    expect(confirmed.status).toBe("CONFIRMED");
    expect(confirmed.revision).toBe(2);

    const snapshot = await readProductDecisionSnapshot(founderCtx, projectId);
    expect(snapshot.status).toBe("CONFIRMED");
    expect(snapshot.revision).toBe(2);
  });

  it("rejects append to a dossier that does not exist in this workspace", async () => {
    await expect(
      appendProductDecisionRevision(founderCtx, "999999999999999999", 1, { reasonCode: "x" })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects create when title is missing", async () => {
    await expect(
      createProductDecisionDossier(founderCtx, { projectId, title: "" })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("an agent context (non-founder) can still read the redacted snapshot", async () => {
    const snapshot = await readProductDecisionSnapshot(agentCtx, projectId);
    expect(snapshot.dossierId).toBe(dossierId);
    expect(snapshot.evidenceRefs[0]).not.toHaveProperty("rawAttachment");
  });
});
