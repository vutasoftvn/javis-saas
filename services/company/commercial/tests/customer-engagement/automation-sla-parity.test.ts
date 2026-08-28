import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { runHousekeepingTick } from "../../services/customer-engagement/housekeeping.service";
import { seedDefaultRules } from "../../services/customer-engagement/automation/default-rules";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("Automation SLA Parity Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_parity_test",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_parity_1",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "SLA Parity Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    // Seed default automation rules including sla_first_response_escalation
    await seedDefaultRules(ctx);
  });

  it("should escalate thread during housekeeping time_sweep when firstResponseDueAt is breached", async () => {
    const threadId = generateSnowflake();
    // First response due 30m ago, not yet responded
    const firstResponseDueAt = new Date(Date.now() - 30 * 60 * 1000);

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      priority: "urgent",
      firstResponseDueAt,
      firstResponseAt: null,
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    await runHousekeepingTick(10);

    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.escalationLevel).toBe(1);
  });

  it("should not escalate thread if first response was already recorded", async () => {
    const threadId = generateSnowflake();
    const firstResponseDueAt = new Date(Date.now() - 30 * 60 * 1000);

    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      priority: "urgent",
      firstResponseDueAt,
      firstResponseAt: new Date(Date.now() - 40 * 60 * 1000), // Responded in time
      escalationLevel: 0,
      correlationId: `corr_${threadId}`,
    });

    await runHousekeepingTick(10);

    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.escalationLevel).toBe(0);
  });
});
