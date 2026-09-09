import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import {
  createInterviewInWorkspace,
  submitInterviewAsEvidence,
} from "../strategy/services/interview.service";
import { getFounderTrialBoard } from "../strategy/services/founder-trial-board.service";

describe("submit interview as evidence (explicit founder action)", () => {
  it("creates a crm-sourced evidence candidate that shows on the board", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Interview evidence",
    });

    const interview = await createInterviewInWorkspace(ctx, {
      projectId: project.id,
      notes: "Talked to a prospect about the weekly pain.",
    });

    const receipt = await submitInterviewAsEvidence(ctx, interview.id, {
      claim: "Prospect confirmed they feel this pain every week",
    });
    expect(receipt.evidenceCount).toBe(1);
    expect(receipt.isReplay).toBe(false);

    const board = await getFounderTrialBoard(ctx, project.id);
    expect(board.evidence.candidate).toHaveLength(1);
    expect(board.evidence.candidate[0].sourceType).toBe("sales_crm");
    // Not linked to any experiment yet → in the unlinked bucket, out of readiness.
    expect(board.evidence.unlinked).toHaveLength(1);
  });

  it("is idempotent for the same interview + claim (dedupe by payload hash)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Interview evidence dedupe",
    });
    const interview = await createInterviewInWorkspace(ctx, {
      projectId: project.id,
      notes: "notes",
    });
    await submitInterviewAsEvidence(ctx, interview.id, { claim: "same claim" });
    const second = await submitInterviewAsEvidence(ctx, interview.id, { claim: "same claim" });
    expect(second.isReplay).toBe(true);

    const board = await getFounderTrialBoard(ctx, project.id);
    expect(board.evidence.candidate).toHaveLength(1);
  });

  it("rejects an empty claim", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Interview evidence empty",
    });
    const interview = await createInterviewInWorkspace(ctx, {
      projectId: project.id,
      notes: "notes",
    });
    await expect(
      submitInterviewAsEvidence(ctx, interview.id, { claim: "  " })
    ).rejects.toThrow();
  });
});
