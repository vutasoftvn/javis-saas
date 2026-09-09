import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { insertContractRevision } from "../services/task-outcome-contract.service";
import { createAiTaskProposalService } from "../services/task.service";
import {
  confirmAiProposalAndQueue,
  createConfirmedTaskAndQueue,
  createWorkPackage,
  listAttempts,
  listWorkPackagesForTask,
  openAttempt,
  reassignWorkPackage,
} from "../services/work-package.service";

const { tasks, taskOutcomeContracts } = schema;

async function makeWs(name: string, role = "founder") {
  const user = await createTestSession({
    email: `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: name,
    role,
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, authorization, ctx };
}

/** Task 'todo' + contract CONFIRMED rev1 + tasks.active_outcome_contract_id set. */
async function seedConfirmedTask(workspaceId: string): Promise<{ taskId: string; contractId: string }> {
  const wsId = BigInt(workspaceId);
  const taskId = generateSnowflake();
  await db.insert(tasks).values({
    id: taskId,
    workspaceId: wsId,
    title: "Confirmed task",
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
        expectedOutcome: "Keep the lights on",
        acceptanceCriteria: { slaMet: true },
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

describe("Company-owned work packages, attempts and immutable events (Task 2)", () => {
  it("queues one package with one accountable first attempt only after a confirmed contract", async () => {
    const { workspaceId, ctx } = await makeWs("WP WS 1");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);

    const item = await createWorkPackage(
      {
        taskId,
        outcomeContractId: contractId,
        assignedAgentInstanceId: "agent_1",
        requestedPriority: "P1",
        objective: "do the thing",
        outputContract: { evidence: ["artifact"] },
        acceptanceRubric: { correct: 5 },
        idempotencyKey: "wp-1",
      },
      ctx
    );
    expect(item).toMatchObject({ status: "QUEUED", requestedPriority: "P1", effectivePriority: "P1" });
    expect(await listAttempts(item.workPackageId)).toHaveLength(1);

    // duplicate idempotency returns the original
    const again = await createWorkPackage(
      {
        taskId,
        outcomeContractId: contractId,
        assignedAgentInstanceId: "agent_1",
        requestedPriority: "P1",
        objective: "do the thing",
        outputContract: { evidence: ["artifact"] },
        acceptanceRubric: { correct: 5 },
        idempotencyKey: "wp-1",
      },
      ctx
    );
    expect(again.workPackageId).toBe(item.workPackageId);
  });

  it("rejects a work package for a task without a confirmed contract", async () => {
    const { workspaceId, ctx } = await makeWs("WP WS 2");
    const wsId = BigInt(workspaceId);
    const taskId = generateSnowflake();
    await db.insert(tasks).values({ id: taskId, workspaceId: wsId, title: "bare", status: "todo" });
    await expect(
      createWorkPackage(
        {
          taskId: taskId.toString(),
          outcomeContractId: "1",
          assignedAgentInstanceId: "agent_1",
          requestedPriority: "P2",
          objective: "x",
          outputContract: { e: [1] },
          acceptanceRubric: { c: 1 },
          idempotencyKey: "wp-none",
        },
        ctx
      )
    ).rejects.toThrow(/Outcome Contract/i);
  });

  it("does not permit two active attempts for the same package", async () => {
    const { workspaceId, ctx } = await makeWs("WP WS 3");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    const item = await createWorkPackage(
      {
        taskId,
        outcomeContractId: contractId,
        assignedAgentInstanceId: "agent_1",
        requestedPriority: "P1",
        objective: "x",
        outputContract: { e: [1] },
        acceptanceRubric: { c: 1 },
        idempotencyKey: "wp-3",
      },
      ctx
    );
    await expect(
      db.transaction((tx) =>
        openAttempt(tx, {
          workspaceId,
          workPackageId: item.workPackageId,
          assignedAgentInstanceId: "agent_2",
        })
      )
    ).rejects.toThrow(/active attempt/i);
  });

  it("createConfirmedTaskAndQueue creates one confirmed contract + one queued package atomically", async () => {
    const { workspaceId, ctx } = await makeWs("WP WS 4");
    const result = await createConfirmedTaskAndQueue(
      {
        task: { title: "Ship onboarding rework", priority: "high" },
        contract: {
          outcomeType: "BAU",
          expectedOutcome: "Support queue < 2h",
          acceptanceCriteria: { slaMet: true },
          expectedEvidenceRefs: [],
          impactHypothesis: "faster support retains users",
          serviceObjective: "First response < 2h",
        },
        initialPackage: {
          assignedAgentInstanceId: "agent_1",
          objective: "Handle the backlog",
          outputContract: { evidence: ["ticket-export"] },
          acceptanceRubric: { completeness: 5 },
        },
        idempotencyKey: "confirmed-1",
      },
      ctx
    );
    expect(result.contract.status).toBe("CONFIRMED");
    expect(result.workPackage.status).toBe("QUEUED");
    expect(await listWorkPackagesForTask(result.task.id, ctx)).toHaveLength(1);

    const [taskRow] = await db.select().from(tasks).where(eq(tasks.id, BigInt(result.task.id)));
    expect(taskRow.status).toBe("todo");
    expect(taskRow.activeOutcomeContractId?.toString()).toBe(result.contract.id);
  });

  it("queues a manager-confirmed AI proposal without leaving a confirmed task in draft", async () => {
    const { workspaceId, ctx } = await makeWs("WP WS 5");
    const proposal = await createAiTaskProposalService(
      {
        workspaceId,
        title: "Interview 10 users",
        proposedByAgentInstanceId: "agent_seed",
        contract: {
          outcomeType: "BAU",
          expectedOutcome: "10 interviews + a decision",
          acceptanceCriteria: { interviews: 10 },
          expectedEvidenceRefs: [],
          impactHypothesis: "validate assumption",
          serviceObjective: "Discovery cadence weekly",
        },
      },
      ctx
    );

    const result = await confirmAiProposalAndQueue(
      {
        proposalTaskId: proposal.task.id,
        draftContractId: proposal.contract.id,
        contractPatch: {},
        initialPackage: {
          assignedAgentInstanceId: "agent_1",
          objective: "Interview 10 users",
          outputContract: { evidence: ["interview"] },
          acceptanceRubric: { completeness: 5 },
        },
        expectedVersion: 1,
        idempotencyKey: "confirm-proposal-1",
      },
      ctx
    );
    expect(result.contract.status).toBe("CONFIRMED");
    expect(result.workPackage.status).toBe("QUEUED");
    expect(await listWorkPackagesForTask(proposal.task.id, ctx)).toHaveLength(1);

    const [taskRow] = await db.select().from(tasks).where(eq(tasks.id, BigInt(proposal.task.id)));
    expect(taskRow.status).toBe("todo");

    const contracts = await db
      .select()
      .from(taskOutcomeContracts)
      .where(eq(taskOutcomeContracts.taskId, BigInt(proposal.task.id)));
    expect(contracts.find((c) => c.status === "CONFIRMED")).toBeTruthy();
    expect(contracts.find((c) => c.revision === 1)?.status).toBe("SUPERSEDED");
  });

  it("reassign creates a new attempt and bumps version when not leased", async () => {
    const { workspaceId, ctx } = await makeWs("WP WS 6");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    const item = await createWorkPackage(
      {
        taskId,
        outcomeContractId: contractId,
        assignedAgentInstanceId: "agent_1",
        requestedPriority: "P1",
        objective: "x",
        outputContract: { e: [1] },
        acceptanceRubric: { c: 1 },
        idempotencyKey: "wp-6",
      },
      ctx
    );
    const reassigned = await reassignWorkPackage(
      { workPackageId: item.workPackageId, targetAgentInstanceId: "agent_2", expectedVersion: 1 },
      ctx
    );
    expect(reassigned.assignedAgentInstanceId).toBe("agent_2");
    expect(reassigned.version).toBe(2);
    const attempts = await listAttempts(item.workPackageId);
    expect(attempts).toHaveLength(2);
    expect(attempts.filter((a) => a.endedAt === null)).toHaveLength(1);

    // stale version rejected
    await expect(
      reassignWorkPackage(
        { workPackageId: item.workPackageId, targetAgentInstanceId: "agent_3", expectedVersion: 1 },
        ctx
      )
    ).rejects.toThrow(/stale work package version/i);
  });

  it("denies a foreign-workspace caller", async () => {
    const { workspaceId } = await makeWs("WP WS 7 owner");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    const foreign = await makeWs("WP WS 7 foreign");
    await expect(
      createWorkPackage(
        {
          taskId,
          outcomeContractId: contractId,
          assignedAgentInstanceId: "agent_1",
          requestedPriority: "P1",
          objective: "x",
          outputContract: { e: [1] },
          acceptanceRubric: { c: 1 },
          idempotencyKey: "wp-foreign",
        },
        foreign.ctx
      )
    ).rejects.toThrow(/not found in workspace/i);
  });
});
