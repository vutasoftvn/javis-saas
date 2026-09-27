import { describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import { listObjectives, listKeyResults } from "../../operations/handlers/okr.handler";
import { createGoal, triageProject } from "../../operations/handlers/goals.handler";
import { listPilots } from "../../operations/strategy/handlers/pilot-run.handler";
import { listMetricContracts } from "../../operations/strategy/handlers/metric-contract.handler";

// Spec 2026-09-27-chat-business-actions: endpoint OKR/goals/pilot/metric-contract chỉ nhận
// token agent mang đúng capability đã khai báo (access matrix ở apps/cosa); capability khác
// bị từ chối. Hành động ghi (T2) chỉ được agent chat gọi sau khi founder duyệt — việc duyệt
// nằm ở apps/cosa, ở đây chỉ chứng minh cổng capability của company.

function delegationFor(userId: string, workspaceId: string, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${userId}`,
    workspace_id: workspaceId,
    run_id: "run-chat-actions-1",
    capability_ids: capabilityIds,
  })}`;
}

describe("agent chat business actions — company capability gate", () => {
  it("okr.objective.list reads objectives and key results", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, [AGENT_CAP.OKR_OBJECTIVE_LIST]);

    const objectives = await listObjectives({ authorization: token, workspaceId: ws.workspaceId });
    expect(Array.isArray(objectives.data)).toBe(true);
    const keyResults = await listKeyResults({ authorization: token, workspaceId: ws.workspaceId });
    expect(Array.isArray(keyResults.data)).toBe(true);
  });

  it("rejects OKR reads with an unrelated capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, [AGENT_CAP.FINANCE_TRANSACTION_READ]);

    await expect(
      listObjectives({ authorization: token, workspaceId: ws.workspaceId })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("goal.create and project.triage refuse a token without their capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, [AGENT_CAP.OKR_OBJECTIVE_LIST]);

    await expect(
      createGoal({ authorization: token, workspaceId: ws.workspaceId, title: "G", goalType: "tactical" })
    ).rejects.toMatchObject({ code: "permission_denied" });
    await expect(
      triageProject({
        authorization: token,
        workspaceId: ws.workspaceId,
        projectId: "1",
        action: "archive",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("goal.create never exceeds the delegating user's role", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "auditor" });
    const token = delegationFor(ws.userId, ws.workspaceId, [AGENT_CAP.STARTUP_OS_GOAL_CREATE]);

    await expect(
      createGoal({ authorization: token, workspaceId: ws.workspaceId, title: "G", goalType: "tactical" })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("strategy.pilot.get and analytics.metric_contract.get read with their capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const pilotToken = delegationFor(ws.userId, ws.workspaceId, [AGENT_CAP.STRATEGY_PILOT_GET]);
    const pilots = await listPilots({ authorization: pilotToken, workspaceId: ws.workspaceId });
    expect(Array.isArray(pilots.items)).toBe(true);

    const metricToken = delegationFor(ws.userId, ws.workspaceId, [
      AGENT_CAP.ANALYTICS_METRIC_CONTRACT_GET,
    ]);
    await expect(
      listMetricContracts({ authorization: metricToken, workspaceId: ws.workspaceId })
    ).resolves.toBeDefined();
  });
});
