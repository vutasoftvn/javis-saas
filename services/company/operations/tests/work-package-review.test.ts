import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { db, schema } from "../models/db";
import { createConfirmedTaskAndQueue } from "../services/work-package.service";
import {
  markValidationPassed,
  overrideWorkPackagePriority,
  reviewWorkPackage,
  runReviewEscalationSweep,
} from "../services/work-package-review.service";

const { taskWorkPackages, workPackagePriorityEvents } = schema;

async function founderWs(name: string) {
  const user = await createTestSession({
    email: `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: name,
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, ctx };
}

async function queuedPackage(ctx: Awaited<ReturnType<typeof founderWs>>["ctx"], key: string) {
  const res = await createConfirmedTaskAndQueue(
    {
      task: { title: "Review task", priority: "high" },
      contract: {
        outcomeType: "BAU",
        expectedOutcome: "stay green",
        acceptanceCriteria: { ok: true },
        expectedEvidenceRefs: [],
        impactHypothesis: "continuity",
        serviceObjective: "Uptime 99.9%",
      },
      initialPackage: {
        assignedAgentInstanceId: "agent_1",
        objective: "run it",
        outputContract: { evidence: ["log"] },
        acceptanceRubric: { completeness: 5 },
      },
      idempotencyKey: key,
    },
    ctx
  );
  return res.workPackage;
}

describe("work package review + priority governance (Task 5)", () => {
  it("counts a business outcome only after an owning review (ACCEPT)", async () => {
    const { ctx } = await founderWs("Review WS 1");
    const wp = await queuedPackage(ctx, "rev-1");
    await markValidationPassed(wp.workPackageId, new Date(Date.now() + 3600_000), ctx);

    const [before] = await db
      .select()
      .from(taskWorkPackages)
      .where(eq(taskWorkPackages.id, BigInt(wp.workPackageId)));
    expect(before.status).toBe("PENDING_MANAGER_REVIEW");

    const review = await reviewWorkPackage(
      {
        workPackageId: wp.workPackageId,
        artifactVersionRef: "artifact://v1",
        decision: "ACCEPT",
        rubricScores: { correctness: 5 },
        reasonCode: "meets_rubric",
        expectedVersion: before.version,
      },
      ctx
    );
    expect(review.decision).toBe("ACCEPT");
    const [after] = await db
      .select()
      .from(taskWorkPackages)
      .where(eq(taskWorkPackages.id, BigInt(wp.workPackageId)));
    expect(after.status).toBe("ACCEPTED");
  });

  it("rejects a review without rubric scores or reason code", async () => {
    const { ctx } = await founderWs("Review WS 2");
    const wp = await queuedPackage(ctx, "rev-2");
    await markValidationPassed(wp.workPackageId, new Date(Date.now() + 3600_000), ctx);
    await expect(
      reviewWorkPackage(
        {
          workPackageId: wp.workPackageId,
          artifactVersionRef: "artifact://v1",
          decision: "ACCEPT",
          rubricScores: {},
          reasonCode: "",
          expectedVersion: 1,
        },
        ctx
      )
    ).rejects.toThrow(/rubric|reason/i);
  });

  it("escalates an overdue review to founder but never auto-accepts", async () => {
    const { ctx, workspaceId } = await founderWs("Review WS 3");
    const wp = await queuedPackage(ctx, "rev-3");
    await markValidationPassed(wp.workPackageId, new Date(Date.now() - 1000), ctx);

    const n = await runReviewEscalationSweep(new Date(), workspaceId);
    expect(n).toBe(1);
    const [row] = await db
      .select()
      .from(taskWorkPackages)
      .where(eq(taskWorkPackages.id, BigInt(wp.workPackageId)));
    expect(row.status).toBe("ESCALATED_TO_FOUNDER");
  });

  it("founder priority override writes an event and keeps requested priority", async () => {
    const { ctx } = await founderWs("Review WS 4");
    const wp = await queuedPackage(ctx, "rev-4");
    const [row0] = await db
      .select()
      .from(taskWorkPackages)
      .where(eq(taskWorkPackages.id, BigInt(wp.workPackageId)));

    const updated = await overrideWorkPackagePriority(
      {
        workPackageId: wp.workPackageId,
        effectivePriority: "P0",
        reason: "incident",
        expectedVersion: row0.version,
      },
      ctx
    );
    expect(updated.effectivePriority).toBe("P0");
    expect(updated.requestedPriority).toBe("P1"); // unchanged

    const events = await db
      .select()
      .from(workPackagePriorityEvents)
      .where(eq(workPackagePriorityEvents.workPackageId, BigInt(wp.workPackageId)));
    expect(events).toHaveLength(1);
    expect(events[0].requestedPriority).toBe("P1");
    expect(events[0].newEffectivePriority).toBe("P0");
  });

  it("stale expectedVersion returns 409", async () => {
    const { ctx } = await founderWs("Review WS 5");
    const wp = await queuedPackage(ctx, "rev-5");
    await markValidationPassed(wp.workPackageId, new Date(Date.now() + 3600_000), ctx);
    await expect(
      reviewWorkPackage(
        {
          workPackageId: wp.workPackageId,
          artifactVersionRef: "artifact://v1",
          decision: "ACCEPT",
          rubricScores: { correctness: 5 },
          reasonCode: "ok",
          expectedVersion: 999,
        },
        ctx
      )
    ).rejects.toThrow(/stale work package version/i);
  });
});
