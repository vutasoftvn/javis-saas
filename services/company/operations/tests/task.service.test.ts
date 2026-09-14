import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { createTaskService, getTaskService, deleteTaskService } from "../services/task.service";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-task-delete",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("deleteTaskService (soft delete)", () => {
  it("marks the task deletedAt and excludes it from subsequent getTaskService", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Delete Task Test" });
    const task = await createTaskService(
      { workspaceId: ws.workspaceId, title: "To be deleted", projectId: project.id },
      ws.bearerToken
    );

    const result = await deleteTaskService(task.id, ctx);
    expect(result.id).toBe(task.id);
    expect(result.deletedAt).toBeTruthy();

    await expect(getTaskService(task.id, ctx)).rejects.toThrow();
  });
});
