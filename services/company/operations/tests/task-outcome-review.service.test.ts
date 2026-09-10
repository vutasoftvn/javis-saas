import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { insertContractRevision } from "../services/task-outcome-contract.service";
import { submitTaskResult, listOutcomeAnalysisRequests } from "../services/task-result.service";
import {
  pinAnalysisRequestSelection,
  recordOutcomeAssessment,
} from "../services/task-outcome-analysis.service";
import { reviewTaskOutcome, verifyKrContribution } from "../services/task-outcome-review.service";

const { tasks, keyResults, okrObjectives, krContributionAssessments } = schema;

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

async function seedConfirmedTaskWithKr(workspaceId: string) {
  const wsId = BigInt(workspaceId);
  const taskId = generateSnowflake();
  const objectiveId = generateSnowflake();
  const krId = generateSnowflake();
  await db.transaction(async (tx) => {
    await tx.insert(okrObjectives).values({ id: objectiveId, workspaceId: wsId, projectId: wsId, title: "O" });
    await tx.insert(keyResults).values({
      id: krId,
      workspaceId: wsId,
      objectiveId,
      title: "KR",
      currentValue: 10,
    });
    await tx.insert(tasks).values({
      id: taskId,
      workspaceId: wsId,
      projectId: wsId,
      title: "Outcome review task",
      status: "todo",
      source: "manager_create",
    });
  });
  const contract = await db.transaction((tx) =>
    insertContractRevision(
      tx,
      {
        workspaceId,
        taskId: taskId.toString(),
        outcomeType: "BAU",
        expectedOutcome: "steady",
        acceptanceCriteria: { ok: true },
        expectedEvidenceRefs: [],
        impactHypothesis: "keep steady",
        serviceObjective: "SLA 99.9%",
      },
      { status: "CONFIRMED", revision: 1 }
    )
  );
  await db
    .update(tasks)
    .set({ activeOutcomeContractId: BigInt(contract.id) })
    .where(eq(tasks.id, taskId));
  return { taskId: taskId.toString(), contractId: contract.id, krId: krId.toString() };
}

async function submitAndAssess(
  ctx: Awaited<ReturnType<typeof founderWs>>["ctx"],
  workspaceId: string,
  taskId: string,
  contractId: string,
  opts: { withKrContribution?: boolean; recommendation?: "ACCEPT" | "REWORK" } = {}
) {
  const result = await submitTaskResult(
    {
      taskId,
      contractId,
      workAttemptIds: ["wa_1"],
      summary: "done",
      artifactRefs: [],
      evidenceRefs: ["evidence://x"],
      claimedMeasurements: {},
      idempotencyKey: `res-${Math.random().toString(36).slice(2)}`,
    },
    ctx
  );
  const [req] = await listOutcomeAnalysisRequests(result.id, ctx);
  await pinAnalysisRequestSelection(req.id, workspaceId, {
    agentInstanceId: "analyst_1",
    assignmentId: "as_a",
    runId: "run_a",
    skillId: "operations/task-outcome-analysis",
    skillVersion: "1.0.0",
    definitionHash: "sha256:s",
  });
  const assessment = await recordOutcomeAssessment(
    {
      requestId: req.id,
      taskResultId: result.id,
      contractId,
      agentInstanceId: "analyst_1",
      assignmentId: "as_a",
      skillId: "operations/task-outcome-analysis",
      skillVersion: "1.0.0",
      definitionHash: "sha256:s",
      evidenceUsedRefs: ["evidence://x"],
      missingEvidenceRefs: [],
      criterionScores: { correctness: 4 },
      confidence: 0.9,
      recommendation: opts.recommendation ?? "ACCEPT",
      krContribution: opts.withKrContribution
        ? { claimedEffect: { delta: 2 }, evidenceRefs: ["evidence://x"], causalConfidence: 0.6 }
        : undefined,
    },
    {
      workspaceId,
      runId: "run_a",
      requestId: req.id,
      capabilityIds: ["operations.outcome-assessment.record"],
    }
  );
  return { result, assessmentId: assessment.id };
}

describe("task outcome review + KR contribution (Task 5)", () => {
  it("requires a READY assessment before ACCEPT", async () => {
    const { ctx, workspaceId } = await founderWs("Outcome Review WS 1");
    const { taskId, contractId } = await seedConfirmedTaskWithKr(workspaceId);
    const a = await submitAndAssess(ctx, workspaceId, taskId, contractId);

    // Make a second result revision -> the first assessment becomes SUPERSEDED.
    await submitAndAssess(ctx, workspaceId, taskId, contractId);

    await expect(
      reviewTaskOutcome(
        {
          taskResultId: a.result.id,
          assessmentId: a.assessmentId,
          decision: "ACCEPT",
          expectedResultRevision: a.result.revision,
          reasonCode: "looks_good",
        },
        ctx
      )
    ).rejects.toThrow(/assessment must be READY/i);
  });

  it("accepts against the current READY assessment", async () => {
    const { ctx, workspaceId } = await founderWs("Outcome Review WS 2");
    const { taskId, contractId } = await seedConfirmedTaskWithKr(workspaceId);
    const a = await submitAndAssess(ctx, workspaceId, taskId, contractId);
    const review = await reviewTaskOutcome(
      {
        taskResultId: a.result.id,
        assessmentId: a.assessmentId,
        decision: "ACCEPT",
        expectedResultRevision: a.result.revision,
        reasonCode: "looks_good",
      },
      ctx
    );
    expect(review.decision).toBe("ACCEPT");
  });

  it("verifies a KR contribution without mutating the KR value", async () => {
    const { ctx, workspaceId } = await founderWs("Outcome Review WS 3");
    const { taskId, contractId, krId } = await seedConfirmedTaskWithKr(workspaceId);
    await submitAndAssess(ctx, workspaceId, taskId, contractId, { withKrContribution: true });

    const [contribution] = await db
      .select()
      .from(krContributionAssessments)
      .where(eq(krContributionAssessments.workspaceId, BigInt(workspaceId)));
    expect(contribution.state).toBe("PROPOSED");

    const [krBefore] = await db.select().from(keyResults).where(eq(keyResults.id, BigInt(krId)));

    const verified = await verifyKrContribution(
      {
        contributionId: contribution.id.toString(),
        decision: "VERIFIED",
        reason: "source metric verified",
        expectedVersion: contribution.version,
      },
      ctx
    );
    expect(verified.state).toBe("VERIFIED");
    expect(verified.version).toBe(contribution.version + 1);

    const [krAfter] = await db.select().from(keyResults).where(eq(keyResults.id, BigInt(krId)));
    expect(krAfter.currentValue).toBe(krBefore.currentValue);
  });
});
