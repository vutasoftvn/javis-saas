import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  createTaskOutcomeProposal,
  validateTaskOutcomeContractForQueue,
  assertTaskCanEnterQueue,
  insertContractRevision,
} from "../services/task-outcome-contract.service";
import { createAiTaskProposalService } from "../services/task.service";

const { tasks, taskOutcomeContracts, initiatives, initiativeKeyResults, keyResults, okrObjectives } =
  schema;

async function makeWorkspace(name: string) {
  const user = await createTestSession({
    email: `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: name,
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, authorization, ctx };
}

async function seedApprovedInitiativeWithKr(workspaceId: string) {
  const wsId = BigInt(workspaceId);
  const objectiveId = generateSnowflake();
  const krId = generateSnowflake();
  const initiativeId = generateSnowflake();

  await db.transaction(async (tx) => {
    await tx
      .insert(okrObjectives)
      .values({ id: objectiveId, workspaceId: wsId, projectId: wsId, title: "Objective A" });
    await tx
      .insert(keyResults)
      .values({ id: krId, workspaceId: wsId, objectiveId, title: "KR A" });
    await tx.insert(initiatives).values({
      id: initiativeId,
      workspaceId: wsId,
      projectId: wsId,
      keyResultId: krId,
      title: "Initiative A",
      approvalStatus: "APPROVED",
    });
    await tx
      .insert(initiativeKeyResults)
      .values({ workspaceId: wsId, initiativeId, keyResultId: krId });
  });

  return { initiativeId: initiativeId.toString(), krId: krId.toString() };
}

async function seedBareTask(workspaceId: string, status = "draft"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(tasks).values({
    id,
    workspaceId: BigInt(workspaceId),
    projectId: BigInt(workspaceId),
    title: "Proposal task",
    status,
    source: "ai_agent_proposal",
  });
  return id.toString();
}

describe("Task Outcome Contract — atomic creation with every task (Task 1A)", () => {
  it("stores an AI suggestion as a draft proposal with no queue entry", async () => {
    const { workspaceId, ctx } = await makeWorkspace("Outcome WS 1");
    const { krId, initiativeId } = await seedApprovedInitiativeWithKr(workspaceId);
    const taskId = await seedBareTask(workspaceId);

    const proposal = await createTaskOutcomeProposal(
      {
        workspaceId,
        taskId,
        outcomeType: "VALIDATION",
        expectedOutcome: "Ten interview records and one evidence-backed decision",
        acceptanceCriteria: { interviews: 10, decision: true },
        expectedEvidenceRefs: [],
        impactHypothesis: "Validate the highest-risk onboarding assumption",
        primaryKrId: krId,
        initiativeId,
        proposedByAgentInstanceId: "agent_1",
      },
      ctx
    );

    expect(proposal).toMatchObject({
      status: "DRAFT",
      outcomeType: "VALIDATION",
      primaryKrId: krId,
    });

    // Không có queue gate nào cho task này (contract vẫn DRAFT, task chưa có
    // active_outcome_contract_id).
    await expect(assertTaskCanEnterQueue(taskId, ctx)).rejects.toThrow(/Outcome Contract/i);
  });

  it("validates a strategic contract but does not confirm it (confirmation lands in Task 2)", async () => {
    const { workspaceId, ctx } = await makeWorkspace("Outcome WS 2");
    const { krId, initiativeId } = await seedApprovedInitiativeWithKr(workspaceId);
    const taskId = await seedBareTask(workspaceId);

    const proposal = await createTaskOutcomeProposal(
      {
        workspaceId,
        taskId,
        outcomeType: "DIRECT_KR",
        expectedOutcome: "Move activation rate baseline to target",
        acceptanceCriteria: { metricMoved: true },
        expectedEvidenceRefs: ["dashboard://activation"],
        impactHypothesis: "Onboarding rework raises activation",
        primaryKrId: krId,
        initiativeId,
        proposedByAgentInstanceId: "agent_2",
      },
      ctx
    );

    const validated = await validateTaskOutcomeContractForQueue(proposal.id, ctx);
    expect(validated).toMatchObject({ initiativeId, primaryKrId: krId, status: "DRAFT" });

    // Vẫn chưa CONFIRMED -> queue gate từ chối.
    await expect(assertTaskCanEnterQueue(proposal.taskId, ctx)).rejects.toThrow(/Outcome Contract/i);
  });

  it("requires a service objective for BAU and never invents one for legacy tasks", async () => {
    const { workspaceId, ctx } = await makeWorkspace("Outcome WS 3");
    const taskId = await seedBareTask(workspaceId);

    await expect(
      createTaskOutcomeProposal(
        {
          workspaceId,
          taskId,
          outcomeType: "BAU",
          expectedOutcome: "Keep payroll runs on time",
          acceptanceCriteria: {},
          expectedEvidenceRefs: [],
          impactHypothesis: "Operational continuity",
          proposedByAgentInstanceId: "agent_3",
        },
        ctx
      )
    ).rejects.toThrow(/service objective/i);

    // Legacy task (không có proposal) -> không có contract, không bị bịa ra.
    const legacyId = generateSnowflake();
    await db.insert(tasks).values({
      id: legacyId,
      workspaceId: BigInt(workspaceId),
      projectId: BigInt(workspaceId),
      title: "Legacy task",
      status: "todo",
    });
    const [c] = await db
      .select()
      .from(taskOutcomeContracts)
      .where(eq(taskOutcomeContracts.taskId, legacyId))
      .limit(1);
    expect(c).toBeUndefined();
    await expect(assertTaskCanEnterQueue(legacyId.toString(), ctx)).rejects.toThrow(
      /no confirmed Outcome Contract/i
    );
  });

  it("rejects a KR that is not linked to the initiative", async () => {
    const { workspaceId, ctx } = await makeWorkspace("Outcome WS 4");
    const { initiativeId } = await seedApprovedInitiativeWithKr(workspaceId);
    // A second, unlinked KR.
    const wsId = BigInt(workspaceId);
    const objectiveId = generateSnowflake();
    const strayKrId = generateSnowflake();
    await db.transaction(async (tx) => {
      await tx
        .insert(okrObjectives)
        .values({ id: objectiveId, workspaceId: wsId, projectId: wsId, title: "Objective B" });
      await tx
        .insert(keyResults)
        .values({ id: strayKrId, workspaceId: wsId, objectiveId, title: "Stray KR" });
    });
    const taskId = await seedBareTask(workspaceId);

    await expect(
      createTaskOutcomeProposal(
        {
          workspaceId,
          taskId,
          outcomeType: "ENABLING_KR",
          expectedOutcome: "Ship the enabling deliverable",
          acceptanceCriteria: {},
          expectedEvidenceRefs: [],
          impactHypothesis: "Prerequisite for the KR",
          primaryKrId: strayKrId.toString(),
          initiativeId,
          proposedByAgentInstanceId: "agent_4",
        },
        ctx
      )
    ).rejects.toThrow(/not linked to Initiative/i);
  });

  it("appends a new revision instead of mutating a confirmed contract", async () => {
    const { workspaceId, ctx } = await makeWorkspace("Outcome WS 5");
    const taskId = await seedBareTask(workspaceId, "todo");

    // Simulate a confirmed rev 1 (Task 2 territory) then append rev 2.
    const rev1 = await db.transaction((tx) =>
      insertContractRevision(
        tx,
        {
          workspaceId,
          taskId,
          outcomeType: "BAU",
          expectedOutcome: "SLA 99.9%",
          acceptanceCriteria: {},
          expectedEvidenceRefs: [],
          impactHypothesis: "keep service healthy",
          serviceObjective: "Uptime 99.9% monthly",
        },
        { status: "CONFIRMED", revision: 1 }
      )
    );
    const rev2 = await db.transaction((tx) =>
      insertContractRevision(
        tx,
        {
          workspaceId,
          taskId,
          outcomeType: "BAU",
          expectedOutcome: "SLA 99.95%",
          acceptanceCriteria: {},
          expectedEvidenceRefs: [],
          impactHypothesis: "raise the bar",
          serviceObjective: "Uptime 99.95% monthly",
        },
        { status: "DRAFT", revision: 2, supersedesContractId: rev1.id, changeReason: "tighten SLA" }
      )
    );
    expect(rev2.revision).toBe(2);
    expect(rev2.supersedesContractId).toBe(rev1.id);

    const all = await db
      .select()
      .from(taskOutcomeContracts)
      .where(eq(taskOutcomeContracts.taskId, BigInt(taskId)));
    expect(all).toHaveLength(2);
    expect(all.find((r) => r.revision === 1)?.expectedOutcome).toBe("SLA 99.9%");
  });

  it("createAiTaskProposalService creates task(draft) + DRAFT contract and no queue", async () => {
    const { workspaceId, ctx } = await makeWorkspace("Outcome WS 6");

    const result = await createAiTaskProposalService(
      {
        workspaceId,
        projectId: workspaceId,
        title: "Interview 10 users",
        proposedByAgentInstanceId: "agent_x",
        contract: {
          outcomeType: "VALIDATION",
          expectedOutcome: "10 interviews + a decision",
          acceptanceCriteria: { interviews: 10 },
          expectedEvidenceRefs: [],
          impactHypothesis: "validate assumption",
        },
      },
      ctx
    );

    expect(result.task.status).toBe("draft");
    expect(result.contract.status).toBe("DRAFT");
    await expect(assertTaskCanEnterQueue(result.task.id, ctx)).rejects.toThrow(/Outcome Contract/i);
  });
});
