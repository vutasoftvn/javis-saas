import { describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { requireWorkspaceAccess, requireWorkspaceWrite } from "../../shared/auth/workspace-access";
import { listTasks } from "../../operations/handlers/task.handler";

// Agent (apps/cosa) gọi Company bằng delegation token thay vì phiên đăng nhập.
// Endpoint chỉ nhận delegation khi khai báo capability, và agent không bao giờ có
// quyền rộng hơn chính user đã giao việc.

function delegationFor(userId: string, workspaceId: string, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${userId}`,
    workspace_id: workspaceId,
    run_id: "run-agent-1",
    capability_ids: capabilityIds,
  })}`;
}

describe("agent delegation on workspace guard", () => {
  it("accepts a delegation whose capability the endpoint allows", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, ["operations.task.list"]);

    const ctx = await requireWorkspaceAccess(token, ws.workspaceId, {
      agentCapabilities: ["operations.task.list"],
    });
    expect(ctx.isAiAgent).toBe(true);
    expect(ctx.userId).toBe(ws.userId);
    expect(ctx.workspaceId).toBe(ws.workspaceId);

    const res = await listTasks({ workspaceId: ws.workspaceId, authorization: token });
    expect(Array.isArray(res.tasks)).toBe(true);
  });

  it("rejects a delegation on an endpoint that declares no agent capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, ["operations.task.list"]);

    await expect(requireWorkspaceAccess(token, ws.workspaceId)).rejects.toMatchObject({
      code: "unauthenticated",
    });
  });

  it("rejects a delegation without the endpoint's capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, ["finance.transaction.read"]);

    await expect(
      requireWorkspaceAccess(token, ws.workspaceId, { agentCapabilities: ["operations.task.list"] })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects a delegation minted for another workspace", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const b = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(a.userId, a.workspaceId, ["operations.task.list"]);

    await expect(
      requireWorkspaceAccess(token, b.workspaceId, { agentCapabilities: ["operations.task.list"] })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("never gives the agent more than the delegating user's role", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "auditor" });
    const token = delegationFor(ws.userId, ws.workspaceId, ["operations.task.create_draft"]);

    await expect(
      requireWorkspaceWrite(token, ws.workspaceId, {
        agentCapabilities: ["operations.task.create_draft"],
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("rejects a forged delegation as unauthenticated", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      requireWorkspaceAccess("Bearer forged.token.value", ws.workspaceId, {
        agentCapabilities: ["operations.task.list"],
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });
});
