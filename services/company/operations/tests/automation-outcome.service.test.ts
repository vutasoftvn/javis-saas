import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  configureAutomationDefinition,
  publishAutomationRevision,
} from "../services/automation-definition.service";
import { createAutomationInvocation } from "../services/automation-invocation.service";
import { getAutomationInvocation } from "../services/automation-invocation.service";
import { projectAutomationOutcome } from "../services/automation-outcome.service";

const KEY = "operating.weekly-review";
const TOKEN = process.env.COSA_WORKER_SERVICE_TOKEN ?? "dev-worker-service-token";

async function anInvocation() {
  const w = await createTestWorkspaceWithMember({ role: "founder" });
  const c = await configureAutomationDefinition({
    workspaceId: w.workspaceId,
    authorization: w.bearerToken,
    automationKey: KEY,
    configuration: { projectId: "p1" },
    triggerContract: { kind: "manual" },
  });
  await publishAutomationRevision({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId: c.data.id! });
  const inv = await createAutomationInvocation({
    workspaceId: w.workspaceId,
    authorization: w.bearerToken,
    definitionId: c.data.id!,
    command: { triggerKind: "manual", clientRequestId: `req-${Math.random()}` },
  });
  return { w, invocationId: inv.data.id };
}

function stateChanged(invocationId: string, workspaceId: string, state: string, seq = 1) {
  return {
    event: {
      eventType: "automation.run.state_changed.v1" as const,
      invocationId,
      runId: `run_auto_${invocationId}`,
      workspaceId,
      state,
      sequence: seq,
      observedAt: new Date().toISOString(),
      manifestHash: "m".repeat(64),
      correlationId: "corr-1",
    },
    serviceToken: TOKEN,
  };
}

function outcome(invocationId: string, workspaceId: string, o: string, seq = 9) {
  return {
    event: {
      eventType: "automation.run.outcome.v1" as const,
      invocationId,
      runId: `run_auto_${invocationId}`,
      workspaceId,
      outcome: o,
      sequence: seq,
      observedAt: new Date().toISOString(),
      manifestHash: "m".repeat(64),
      correlationId: "corr-1",
      evidenceRefs: ["digest_markdown", "source_refs"],
    },
    serviceToken: TOKEN,
  };
}

describe("automation outcome projection — terminal-absorbing, non-authoritative", () => {
  it("projects RUNNING then COMPLETED onto the invocation", async () => {
    const { w, invocationId } = await anInvocation();
    const r1 = await projectAutomationOutcome(stateChanged(invocationId, w.workspaceId, "RUNNING", 1));
    expect(r1).toEqual({ projected: true, state: "RUNNING" });

    const r2 = await projectAutomationOutcome(outcome(invocationId, w.workspaceId, "COMPLETED", 5));
    expect(r2).toEqual({ projected: true, state: "COMPLETED" });

    const got = await getAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, invocationId });
    expect(got.data.state).toBe("COMPLETED");
    expect(got.data.agentRunId).toBe(`run_auto_${invocationId}`);
  });

  it("a replay of the same event is idempotent", async () => {
    const { w, invocationId } = await anInvocation();
    await projectAutomationOutcome(stateChanged(invocationId, w.workspaceId, "RUNNING", 1));
    const replay = await projectAutomationOutcome(stateChanged(invocationId, w.workspaceId, "RUNNING", 1));
    expect(replay.projected).toBe(false);
  });

  it("an out-of-order RUNNING after COMPLETED cannot regress the terminal state", async () => {
    const { w, invocationId } = await anInvocation();
    await projectAutomationOutcome(outcome(invocationId, w.workspaceId, "COMPLETED", 5));
    const late = await projectAutomationOutcome(stateChanged(invocationId, w.workspaceId, "RUNNING", 9));
    expect(late).toEqual({ projected: false, state: "COMPLETED" });
    const got = await getAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, invocationId });
    expect(got.data.state).toBe("COMPLETED");
  });

  it("rejects an invalid service token", async () => {
    const { w, invocationId } = await anInvocation();
    await expect(
      projectAutomationOutcome({ ...stateChanged(invocationId, w.workspaceId, "RUNNING"), serviceToken: "wrong" })
    ).rejects.toThrow(/service token/);
  });

  it("rejects a cross-workspace / unknown invocation without leaking detail", async () => {
    const { w } = await anInvocation();
    await expect(
      projectAutomationOutcome(stateChanged("999999999999", w.workspaceId, "RUNNING"))
    ).rejects.toThrow(/not found/);
  });

  it("rejects an unmapped run state", async () => {
    const { w, invocationId } = await anInvocation();
    const bad = stateChanged(invocationId, w.workspaceId, "WAT");
    await expect(projectAutomationOutcome(bad)).rejects.toThrow(/unmapped/);
  });
});
