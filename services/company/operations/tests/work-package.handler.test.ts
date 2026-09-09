import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  createConfirmedTaskAndQueueEndpoint,
  getWorkPackageEndpoint,
} from "../handlers/work-package.handler";

async function session(name: string, role = "founder") {
  const user = await createTestSession({
    email: `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: name,
    role,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

const goodBody = {
  task: { title: "Handler task", priority: "high" as const },
  contract: {
    outcomeType: "BAU" as const,
    expectedOutcome: "Stay green",
    acceptanceCriteria: { ok: true },
    expectedEvidenceRefs: [],
    impactHypothesis: "operational",
    serviceObjective: "Uptime 99.9%",
  },
  initialPackage: {
    assignedAgentInstanceId: "agent_1",
    objective: "Run it",
    outputContract: { evidence: ["log"] },
    acceptanceRubric: { completeness: 5 },
  },
};

describe("work-package handlers", () => {
  it("createConfirmedTaskAndQueueEndpoint returns a queued package via workspace auth", async () => {
    const s = await session("WP Handler WS 1");
    const res = await createConfirmedTaskAndQueueEndpoint({
      workspaceId: s.workspaceId,
      authorization: s.authorization,
      idempotencyKey: "handler-1",
      ...goodBody,
    });
    expect(res.contract.status).toBe("CONFIRMED");
    expect(res.workPackage.status).toBe("QUEUED");

    const fetched = await getWorkPackageEndpoint({
      id: res.workPackage.workPackageId,
      workspaceId: s.workspaceId,
      authorization: s.authorization,
    });
    expect(fetched.workPackageId).toBe(res.workPackage.workPackageId);
  });

  it("rejects a caller that is not a member of the workspace", async () => {
    const owner = await session("WP Handler WS 2 owner");
    const created = await createConfirmedTaskAndQueueEndpoint({
      workspaceId: owner.workspaceId,
      authorization: owner.authorization,
      idempotencyKey: "handler-2",
      ...goodBody,
    });
    const foreign = await session("WP Handler WS 2 foreign");
    await expect(
      getWorkPackageEndpoint({
        id: created.workPackage.workPackageId,
        workspaceId: owner.workspaceId,
        authorization: foreign.authorization,
      })
    ).rejects.toThrow();
  });
});
