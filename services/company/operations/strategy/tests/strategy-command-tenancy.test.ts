import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { db, schema } from "../../db";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import {
  createWeeklyReviewService,
  completeWeeklyReviewService,
  listWeeklyReviewsService,
} from "../services/weekly-review.service";
import {
  createActionProposalService,
  acceptActionProposalService,
  listActionProposalsService,
} from "../services/next-best-action.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { eventOutbox } from "../../../shared/db/schema/integration";

describe("strategy-command-tenancy (F01)", () => {
  it("cannot complete weekly review belonging to another workspace and handles idempotency", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    const reviewA = await createWeeklyReviewService({
      workspaceId: BigInt(wsA.workspaceId),
      weekStartDate: "2026-09-01",
      summary: "Tuần 1 mục tiêu OKR",
    });

    const ctxB: TenantContext = {
      workspaceId: wsB.workspaceId,
      userId: wsB.userId,
      workforceMemberId: "999",
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-b",
    };

    // User in Workspace B attempts to complete review from Workspace A
    await expect(
      completeWeeklyReviewService({
        reviewId: BigInt(reviewA.id),
        completedBy: BigInt(wsB.userId),
        ctx: ctxB,
      })
    ).rejects.toThrow(APIError);

    // Verify outbox was not created by rejected call
    const outboxInitial = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, reviewA.id));
    expect(outboxInitial.length).toBe(0);

    const ctxA: TenantContext = {
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      workforceMemberId: "888",
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-a",
    };

    // User in Workspace A completes review
    const completedA = await completeWeeklyReviewService({
      reviewId: BigInt(reviewA.id),
      completedBy: BigInt(wsA.userId),
      ctx: ctxA,
    });
    expect(completedA.status).toBe("COMPLETED");

    const outboxAfter = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, reviewA.id));
    expect(outboxAfter.length).toBe(1);

    // Idempotent retry: complete again returns existing COMPLETED and does NOT emit another event
    const reCompleted = await completeWeeklyReviewService({
      reviewId: BigInt(reviewA.id),
      completedBy: BigInt(wsA.userId),
      ctx: ctxA,
    });
    expect(reCompleted.status).toBe("COMPLETED");

    const outboxAfterReplay = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, reviewA.id));
    expect(outboxAfterReplay.length).toBe(1);
  });

  it("cannot accept action proposal belonging to another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    const proposalA = await createActionProposalService({
      workspaceId: BigInt(wsA.workspaceId),
      source: "evidence",
      recommendation: "Test pilot execution",
      decisionReason: "Data is ready",
    });

    const ctxB: TenantContext = {
      workspaceId: wsB.workspaceId,
      userId: wsB.userId,
      workforceMemberId: "999",
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-b",
    };

    // User in Workspace B attempts to accept proposal from Workspace A
    await expect(
      acceptActionProposalService({
        proposalId: BigInt(proposalA.id),
        acceptedBy: BigInt(wsB.userId),
        ctx: ctxB,
      })
    ).rejects.toThrow(APIError);

    // Verify outbox was not created by rejected call
    const outboxInitial = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, proposalA.id));
    expect(outboxInitial.length).toBe(0);

    const ctxA: TenantContext = {
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      workforceMemberId: "888",
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "corr-a",
    };

    // User in Workspace A accepts proposal
    const acceptedA = await acceptActionProposalService({
      proposalId: BigInt(proposalA.id),
      acceptedBy: BigInt(wsA.userId),
      ctx: ctxA,
    });
    expect(acceptedA.status).toBe("ACCEPTED");

    const outboxAfter = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, proposalA.id));
    expect(outboxAfter.length).toBe(1);

    // Replay idempotency: accepting again returns existing ACCEPTED and does NOT emit another event
    const reAccepted = await acceptActionProposalService({
      proposalId: BigInt(proposalA.id),
      acceptedBy: BigInt(wsA.userId),
      ctx: ctxA,
    });
    expect(reAccepted.status).toBe("ACCEPTED");

    const outboxAfterReplay = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, proposalA.id));
    expect(outboxAfterReplay.length).toBe(1);
  });
});
