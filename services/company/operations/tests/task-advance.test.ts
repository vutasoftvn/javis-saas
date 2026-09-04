import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember } from "./_helpers";
import { readOutbox } from "./helpers/outbox";
import { advanceTaskByAgentService } from "../services/task.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { tasks } = schema;

function ctxFor(workspaceId: string): TenantContext {
  return Object.freeze({
    workspaceId,
    userId: "1",
    workforceMemberId: undefined,
    membershipRole: "admin",
    permissions: [],
    correlationId: "test",
    platformUserId: null,
  }) as unknown as TenantContext;
}

async function seedTask(opts: { assignee: "ai" | "human" | "none"; status: string }) {
  const ws = await createTestWorkspaceWithMember();
  let assigneeMemberId: bigint | null = null;
  if (opts.assignee === "ai") {
    const id = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "AI_AGENT",
      agentSpecId: "cosa.agents.operations",
      agentSpecVersion: "1.1.0",
      roleTitle: "AI operations",
      status: "active",
    });
    assigneeMemberId = id;
  } else if (opts.assignee === "human") {
    const id = generateSnowflake();
    await db.insert(identityWorkforceMembers).values({
      id,
      workspaceId: BigInt(ws.workspaceId),
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });
    assigneeMemberId = id;
  }
  const taskId = generateSnowflake();
  await db.insert(tasks).values({
    id: taskId,
    workspaceId: BigInt(ws.workspaceId),
    title: "WGA advance task",
    status: opts.status,
    source: "ai_agent_proposal",
    assigneeMemberId,
    executionMode: opts.assignee === "human" ? "HUMAN" : "AGENT",
  });
  return { workspaceId: ws.workspaceId, taskId: taskId.toString() };
}

describe("advanceTaskByAgentService", () => {
  it("advances an AI-assigned task in_progress -> done and emits task.completed", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "ai", status: "in_progress" });
    const r = await advanceTaskByAgentService(
      { taskId, toStatus: "done", runId: "run_1" },
      ctxFor(workspaceId)
    );
    expect(r.status).toBe("done");
    const events = await readOutbox(workspaceId, "task", taskId);
    expect(events.some((e) => e.eventType === "operations.task.completed.v1")).toBe(true);
  });

  it("allows in_progress and blocked transitions for an AI task", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "ai", status: "todo" });
    const p = await advanceTaskByAgentService(
      { taskId, toStatus: "in_progress", runId: "run_2" },
      ctxFor(workspaceId)
    );
    expect(p.status).toBe("in_progress");
    const b = await advanceTaskByAgentService(
      { taskId, toStatus: "blocked", runId: "run_2", note: "cần founder xử lý" },
      ctxFor(workspaceId)
    );
    expect(b.status).toBe("blocked");
  });

  it("rejects advancing a human-assigned task", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "human", status: "in_progress" });
    await expect(
      advanceTaskByAgentService({ taskId, toStatus: "done", runId: "r" }, ctxFor(workspaceId))
    ).rejects.toThrow(/AI member/);
  });

  it("rejects advancing a task with no assignee", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "none", status: "in_progress" });
    await expect(
      advanceTaskByAgentService({ taskId, toStatus: "done", runId: "r" }, ctxFor(workspaceId))
    ).rejects.toThrow(/AI member/);
  });

  it("rejects done from todo", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "ai", status: "todo" });
    await expect(
      advanceTaskByAgentService({ taskId, toStatus: "done", runId: "r" }, ctxFor(workspaceId))
    ).rejects.toThrow();
  });

  it("rejects an out-of-range status", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "ai", status: "in_progress" });
    await expect(
      advanceTaskByAgentService(
        // @ts-expect-error runtime guard test
        { taskId, toStatus: "cancelled", runId: "r" },
        ctxFor(workspaceId)
      )
    ).rejects.toThrow();
  });

  it("rejects a missing runId", async () => {
    const { workspaceId, taskId } = await seedTask({ assignee: "ai", status: "in_progress" });
    await expect(
      advanceTaskByAgentService({ taskId, toStatus: "done", runId: "" }, ctxFor(workspaceId))
    ).rejects.toThrow();
  });
});
