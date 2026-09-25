import { mintTestWorkerToken } from "../../shared/auth/worker-service-auth";
import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  configureAutomationDefinition,
  publishAutomationRevision,
} from "../services/automation-definition.service";
import { createAutomationInvocation } from "../services/automation-invocation.service";
import { projectAutomationOutcome } from "../services/automation-outcome.service";
import {
  getAutomationRunInspector,
  listAutomationNeedsYou,
} from "../services/automation-inspector.service";

const KEY = "operating.weekly-review";
const TOKEN = mintTestWorkerToken("automation-inspector");

async function anInvocation(role = "founder") {
  const w = await createTestWorkspaceWithMember({ role });
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

function evt(invocationId: string, workspaceId: string, body: Record<string, unknown>) {
  return { event: { ...body, invocationId, workspaceId, runId: `run_auto_${invocationId}` } as never, serviceToken: TOKEN };
}

describe("automation run inspector — projection from persisted facts", () => {
  it("projects a completed run with pinned revision + evidence", async () => {
    const { w, invocationId } = await anInvocation();
    await projectAutomationOutcome(evt(invocationId, w.workspaceId, {
      eventType: "automation.run.state_changed.v1", state: "RUNNING", sequence: 1,
      observedAt: new Date().toISOString(), manifestHash: "m".repeat(64), correlationId: "c",
    }));
    await projectAutomationOutcome(evt(invocationId, w.workspaceId, {
      eventType: "automation.run.outcome.v1", outcome: "COMPLETED", sequence: 5,
      observedAt: new Date().toISOString(), manifestHash: "m".repeat(64), correlationId: "c",
      evidenceRefs: ["digest_markdown", "source_refs"],
    }));

    const ins = await getAutomationRunInspector({
      workspaceId: w.workspaceId, authorization: w.bearerToken, invocationId,
    });
    expect(ins.data.state).toBe("COMPLETED");
    expect(ins.data.revisionHash).toMatch(/^[0-9a-f]{64}$/);
    expect(ins.data.evidenceRefs.sort()).toEqual(["digest_markdown", "source_refs"]);
    expect(ins.data.sourceHealth).toBe("ok");
  });

  it("a blocked run reports degraded source health and a failure reason", async () => {
    const { w, invocationId } = await anInvocation();
    await projectAutomationOutcome(evt(invocationId, w.workspaceId, {
      eventType: "automation.run.outcome.v1", outcome: "BLOCKED", sequence: 3,
      observedAt: new Date().toISOString(), manifestHash: "m".repeat(64), correlationId: "c",
      blockedCause: "LOCAL_RUNTIME_UNAVAILABLE",
    }));
    const ins = await getAutomationRunInspector({
      workspaceId: w.workspaceId, authorization: w.bearerToken, invocationId,
    });
    expect(ins.data.state).toBe("BLOCKED");
    expect(ins.data.sourceHealth).toBe("degraded");
    expect(ins.data.failureReason).toBe("LOCAL_RUNTIME_UNAVAILABLE");
  });

  it("a foreign workspace cannot read the inspector", async () => {
    const { w, invocationId } = await anInvocation();
    const other = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      getAutomationRunInspector({ workspaceId: w.workspaceId, authorization: other.bearerToken, invocationId })
    ).rejects.toThrow();
  });

  it("Needs You lists approval / blocked / failed runs with a stable deep link", async () => {
    const { w, invocationId } = await anInvocation();
    await projectAutomationOutcome(evt(invocationId, w.workspaceId, {
      eventType: "automation.run.outcome.v1", outcome: "BLOCKED", sequence: 2,
      observedAt: new Date().toISOString(), manifestHash: "m".repeat(64), correlationId: "c",
      blockedCause: "LOCAL_RUNTIME_UNAVAILABLE",
    }));
    const needs = await listAutomationNeedsYou({ workspaceId: w.workspaceId, authorization: w.bearerToken });
    const item = needs.data.find((n) => n.invocationId === invocationId);
    expect(item).toBeDefined();
    expect(item!.kind).toBe("LOCAL_RUNTIME_UNAVAILABLE");
  });

  it("an unknown invocation state never maps to COMPLETED", async () => {
    const { w, invocationId } = await anInvocation();
    // fresh invocation is REQUESTED -> PENDING, not COMPLETED
    const ins = await getAutomationRunInspector({
      workspaceId: w.workspaceId, authorization: w.bearerToken, invocationId,
    });
    expect(ins.data.state).toBe("PENDING");
    expect(ins.data.state).not.toBe("COMPLETED");
  });
});
