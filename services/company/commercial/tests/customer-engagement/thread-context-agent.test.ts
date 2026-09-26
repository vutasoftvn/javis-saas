import { describe, expect, it } from "vitest";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
} from "../../../shared/db/schema/customer-engagement";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { mintCompanyDelegation } from "../../../shared/auth/cosa-delegation.service";
import { getThreadContextApi } from "../../handlers/customer-engagement/copilot.handler";

// Agent chăm sóc khách hàng đọc ngữ cảnh hội thoại qua engagement.thread.read.
function delegation(userId: string, workspaceId: string, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${userId}`,
    workspace_id: workspaceId,
    run_id: "run-thread-context",
    capability_ids: capabilityIds,
  })}`;
}

async function seedThread(workspaceId: string): Promise<string> {
  const wsId = BigInt(workspaceId);
  const inboxId = generateSnowflake();
  const threadId = generateSnowflake();
  await db.insert(engagementInboxes).values({
    id: inboxId,
    workspaceId: wsId,
    channelType: "email",
    name: "Support Desk",
    slaPolicy: { firstResponseMinutes: 60 },
  });
  await db.insert(engagementThreads).values({
    id: threadId,
    workspaceId: wsId,
    inboxId,
    status: "open",
    priority: "normal",
    correlationId: `corr-${threadId}`,
  });
  return threadId.toString();
}

describe("thread context for agents", () => {
  it("serves thread context to a delegation carrying engagement.thread.read", async () => {
    const user = await createTestSession({ role: "admin" });
    const threadId = await seedThread(user.workspaceId);

    const context = await getThreadContextApi({
      id: threadId,
      workspaceId: user.workspaceId,
      authorization: delegation(user.userId, user.workspaceId, ["engagement.thread.read"]),
    });
    expect(context.thread.id).toBe(threadId);
  });

  it("rejects a delegation without engagement.thread.read", async () => {
    const user = await createTestSession({ role: "admin" });
    const threadId = await seedThread(user.workspaceId);

    await expect(
      getThreadContextApi({
        id: threadId,
        workspaceId: user.workspaceId,
        authorization: delegation(user.userId, user.workspaceId, ["operations.task.list"]),
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
