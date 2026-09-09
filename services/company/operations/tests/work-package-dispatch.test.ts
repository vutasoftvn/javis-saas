import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { insertContractRevision } from "../services/task-outcome-contract.service";
import {
  createWorkPackage,
  listAttempts,
} from "../services/work-package.service";
import {
  EligibilityTransport,
  setEligibilityTransport,
} from "../services/workforce-eligibility.client";
import { OPERATING_WORK_PACKAGE_QUEUED_V1 } from "../../shared/events/event-types";

const { tasks, eventOutbox, workPackageAttempts } = schema;

async function makeWs(name: string) {
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
    title: "Dispatch task",
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
  await db.update(tasks).set({ activeOutcomeContractId: BigInt(contract.id) }).where(eq(tasks.id, taskId));
  return { taskId: taskId.toString(), contractId: contract.id };
}

const okTransport: EligibilityTransport = async (q) => ({
  status: 200,
  body: {
    data: {
      agent_instance_id: q.agentInstanceId,
      assignment_id: "as_1",
      status: "ACTIVE",
      spec_snapshot: { spec_id: "cosa.agents.operations", spec_version: "1.0.0", definition_hash: "sha256:x" },
      capability_refs: [],
      capacity_available: true,
    },
  },
});

describe("signed Company→Agent work-package dispatch (Task 3)", () => {
  beforeEach(() => {
    process.env.AI_WORKFORCE_V2_ENABLED = "true";
  });
  afterEach(() => {
    delete process.env.AI_WORKFORCE_V2_ENABLED;
    setEligibilityTransport(null);
  });

  it("fails closed and writes no attempt when the control plane is unreachable", async () => {
    const { workspaceId, ctx } = await makeWs("Dispatch WS 1");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    setEligibilityTransport(async () => {
      throw new Error("ECONNREFUSED");
    });

    await expect(
      createWorkPackage(
        {
          taskId,
          outcomeContractId: contractId,
          assignedAgentInstanceId: "emp_1",
          requestedPriority: "P1",
          objective: "x",
          outputContract: { e: [1] },
          acceptanceRubric: { c: 1 },
          idempotencyKey: "disp-1",
        },
        ctx
      )
    ).rejects.toThrow(/eligibility lookup failed/i);
  });

  it("rejects a non-ACTIVE / foreign employee (typed 409) with no attempt", async () => {
    const { workspaceId, ctx } = await makeWs("Dispatch WS 2");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    setEligibilityTransport(async () => ({ status: 404, body: {} }));

    await expect(
      createWorkPackage(
        {
          taskId,
          outcomeContractId: contractId,
          assignedAgentInstanceId: "emp_ghost",
          requestedPriority: "P1",
          objective: "x",
          outputContract: { e: [1] },
          acceptanceRubric: { c: 1 },
          idempotencyKey: "disp-2",
        },
        ctx
      )
    ).rejects.toThrow(/foreign or unknown|not found/i);
  });

  it("on success: queues package, persists spec snapshot on attempt, emits signed outbox event", async () => {
    const { workspaceId, ctx } = await makeWs("Dispatch WS 3");
    const { taskId, contractId } = await seedConfirmedTask(workspaceId);
    setEligibilityTransport(okTransport);

    const wp = await createWorkPackage(
      {
        taskId,
        outcomeContractId: contractId,
        assignedAgentInstanceId: "emp_1",
        requestedPriority: "P1",
        objective: "x",
        outputContract: { e: [1] },
        acceptanceRubric: { c: 1 },
        idempotencyKey: "disp-3",
      },
      ctx
    );
    expect(wp.status).toBe("QUEUED");

    const [attempt] = await db
      .select()
      .from(workPackageAttempts)
      .where(eq(workPackageAttempts.workPackageId, BigInt(wp.workPackageId)));
    expect((attempt.specSnapshot as Record<string, unknown>).specId).toBe("cosa.agents.operations");

    const events = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, wp.workPackageId));
    const queued = events.find((e) => e.eventType === OPERATING_WORK_PACKAGE_QUEUED_V1);
    expect(queued).toBeTruthy();
    const payload = (queued!.envelope as { payload: Record<string, unknown> }).payload;
    expect(payload.workAttemptId).toBe((await listAttempts(wp.workPackageId))[0].attemptId);
    expect(payload.agentInstanceId).toBe("emp_1");
    // Không lộ credential/prompt trong payload.
    expect(JSON.stringify(payload)).not.toMatch(/secret|token|password|prompt/i);
  });
});
