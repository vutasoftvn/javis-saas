import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { insertContractRevision } from "../services/task-outcome-contract.service";
import {
  listOutcomeAnalysisRequests,
  submitTaskResult,
} from "../services/task-result.service";
import {
  pinAnalysisRequestSelection,
  recordOutcomeAssessment,
  loadAssessmentForResult,
} from "../services/task-outcome-analysis.service";

const { tasks, taskOutcomeContracts, outcomeAssessments } = schema;

async function ws(name: string) {
  const user = await createTestSession({
    email: `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: name,
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, ctx };
}

async function seedConfirmedTask(workspaceId: string) {
  const wsId = BigInt(workspaceId);
  const taskId = generateSnowflake();
  await db.insert(tasks).values({
    id: taskId,
    workspaceId: wsId,
    projectId: wsId,
    title: "Result task",
    status: "todo",
    source: "manager_create",
  });
  const contract = await db.transaction((tx) =>
    insertContractRevision(
      tx,
      {
        workspaceId,
        taskId: taskId.toString(),
        outcomeType: "BAU",
        expectedOutcome: "stay green",
        acceptanceCriteria: { ok: true },
        expectedEvidenceRefs: [],
        impactHypothesis: "continuity",
        serviceObjective: "Uptime 99.9%",
      },
      { status: "CONFIRMED", revision: 1 }
    )
  );
  await db
    .update(tasks)
    .set({ activeOutcomeContractId: BigInt(contract.id) })
    .where(eq(tasks.id, taskId));
  return { taskId: taskId.toString(), contractId: contract.id };
}

function resultInput(taskId: string, contractId: string, key = "result-1") {
  return {
    taskId,
    contractId,
    workAttemptIds: ["wa_1"],
    summary: "Did the work",
    artifactRefs: ["artifact://a"],
    evidenceRefs: ["evidence://e"],
    claimedMeasurements: { uptime: 99.95 },
    idempotencyKey: key,
  };
}

describe("Versioned task results + deterministic outcome-analysis dispatch (Task 4A)", () => {
  it("creates one TASK_OUTCOME request per result revision in AUTO_ALL_TASKS", async () => {
    const { workspaceId, ctx } = await ws("Result WS 1");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);

    const first = await submitTaskResult(resultInput(taskId, contractId), ctx);
    const retry = await submitTaskResult(resultInput(taskId, contractId), ctx);
    expect(retry.id).toBe(first.id);
    expect(await listOutcomeAnalysisRequests(first.id, ctx)).toHaveLength(1);
    expect(first.revision).toBe(1);

    const rework = await submitTaskResult(resultInput(taskId, contractId, "result-2"), ctx);
    expect(rework.revision).toBe(2);
    expect(await listOutcomeAnalysisRequests(rework.id, ctx)).toHaveLength(1);
  });

  it("never writes task status or KR actual value on submit", async () => {
    const { workspaceId, ctx } = await ws("Result WS 2");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    await submitTaskResult(resultInput(taskId, contractId), ctx);
    const [taskRow] = await db.select().from(tasks).where(eq(tasks.id, BigInt(taskId)));
    expect(taskRow.status).toBe("todo"); // unchanged
  });

  it("a new result revision supersedes the prior assessment (never deletes it)", async () => {
    const { workspaceId, ctx } = await ws("Result WS 3");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    const r1 = await submitTaskResult(resultInput(taskId, contractId), ctx);
    const [req1] = await listOutcomeAnalysisRequests(r1.id, ctx);

    await pinAnalysisRequestSelection(req1.id, workspaceId, {
      agentInstanceId: "analyst_1",
      assignmentId: "as_analyst",
      runId: "run_analysis_1",
      skillId: "operations/task-outcome-analysis",
      skillVersion: "1.0.0",
      definitionHash: "sha256:skill",
    });
    await recordOutcomeAssessment(
      {
        requestId: req1.id,
        taskResultId: r1.id,
        contractId,
        agentInstanceId: "analyst_1",
        assignmentId: "as_analyst",
        skillId: "operations/task-outcome-analysis",
        skillVersion: "1.0.0",
        definitionHash: "sha256:skill",
        evidenceUsedRefs: ["evidence://e"],
        missingEvidenceRefs: [],
        criterionScores: { correctness: 4 },
        confidence: 0.8,
        recommendation: "ACCEPT",
      },
      {
        workspaceId,
        runId: "run_analysis_1",
        requestId: req1.id,
        capabilityIds: ["operations.outcome-assessment.record"],
      }
    );
    expect((await loadAssessmentForResult(r1.id, workspaceId))?.status).toBe("READY");

    // Rework -> old assessment SUPERSEDED, not deleted.
    await submitTaskResult(resultInput(taskId, contractId, "result-2"), ctx);
    const rows = await db
      .select()
      .from(outcomeAssessments)
      .where(eq(outcomeAssessments.taskResultId, BigInt(r1.id)));
    expect(rows).toHaveLength(1);
    expect(rows[0].status).toBe("SUPERSEDED");
  });

  it("rejects an assessment from a run or delegation not selected by the router", async () => {
    const { workspaceId, ctx } = await ws("Result WS 4");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    const r1 = await submitTaskResult(resultInput(taskId, contractId), ctx);
    const [req1] = await listOutcomeAnalysisRequests(r1.id, ctx);
    await pinAnalysisRequestSelection(req1.id, workspaceId, {
      agentInstanceId: "analyst_1",
      assignmentId: "as_analyst",
      runId: "run_correct",
      skillId: "operations/task-outcome-analysis",
      skillVersion: "1.0.0",
      definitionHash: "sha256:skill",
    });

    const validAssessment = {
      requestId: req1.id,
      taskResultId: r1.id,
      contractId,
      agentInstanceId: "analyst_1",
      assignmentId: "as_analyst",
      skillId: "operations/task-outcome-analysis",
      skillVersion: "1.0.0",
      definitionHash: "sha256:skill",
      evidenceUsedRefs: [],
      missingEvidenceRefs: [],
      criterionScores: { correctness: 3 },
      confidence: 0.5,
      recommendation: "REWORK" as const,
    };

    await expect(
      recordOutcomeAssessment(validAssessment, {
        workspaceId,
        runId: "run_WRONG",
        requestId: req1.id,
        capabilityIds: ["operations.outcome-assessment.record"],
      })
    ).rejects.toThrow(/request attribution/i);

    await expect(
      recordOutcomeAssessment(validAssessment, {
        workspaceId,
        runId: "run_correct",
        requestId: req1.id,
        capabilityIds: ["operations.task.read"],
      })
    ).rejects.toThrow(/capability/i);
  });
});
