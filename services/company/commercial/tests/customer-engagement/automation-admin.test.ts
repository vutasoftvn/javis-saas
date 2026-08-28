import { describe, expect, it, beforeEach } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementAutomationRules,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import {
  createOrVersionRuleApi,
  enableRuleApi,
  disableRuleApi,
  listRulesApi,
  dryRunAutomationApi,
  listThreadAutomationApplicationsApi,
} from "../../handlers/customer-engagement/automation.handler";

describe("Automation Admin & Dry-Run API Tests", () => {
  it("should handle rule creation, versioning, enabling, disabling, and dry-run", async () => {
    const user = await createTestSession({ displayName: "Automation Admin", role: "admin" });
    const authorization = `Bearer ${user.accessToken}`;
    const workspaceId = user.workspaceId;
    const wsId = BigInt(workspaceId);

    const inboxId = generateSnowflake();
    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Admin Rule Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });

    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      priority: "normal",
      correlationId: `corr_${threadId}`,
    });

    // 1. Create Rule Version 1 -> default enabled: false
    const v1 = await createOrVersionRuleApi({
      workspaceId,
      authorization,
      ruleKey: "rule_admin_test_1",
      name: "Admin Rule V1",
      trigger: "thread_opened",
      priority: 10,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "admin_label_v1" }],
    });
    expect(v1.version).toBe(1);
    expect(v1.enabled).toBe(false);

    // 2. Version Rule (Update with same ruleKey) -> Version 2 created
    const v2 = await createOrVersionRuleApi({
      workspaceId,
      authorization,
      ruleKey: "rule_admin_test_1",
      name: "Admin Rule V2",
      trigger: "thread_opened",
      priority: 5,
      condition: { fact: "thread.status", op: "eq", value: "open" },
      actions: [{ type: "apply_label", labelKey: "admin_label_v2" }],
    });
    expect(v2.version).toBe(2);
    expect(v2.enabled).toBe(false);

    // 3. Enable Rule V2
    const enabledV2 = await enableRuleApi({
      key: "rule_admin_test_1",
      workspaceId,
      authorization,
    });
    expect(enabledV2.enabled).toBe(true);
    expect(enabledV2.version).toBe(2);

    // 4. List Rules
    const list = await listRulesApi({ workspaceId, authorization });
    expect(list.rules.length).toBeGreaterThanOrEqual(2);

    // 5. Dry-Run on thread
    const dryRun = await dryRunAutomationApi({
      id: threadId.toString(),
      workspaceId,
      authorization,
      trigger: "thread_opened",
    });
    expect(dryRun.matched.length).toBe(1);
    expect(dryRun.matched[0].ruleKey).toBe("rule_admin_test_1");
    expect(dryRun.matched[0].version).toBe(2);

    // 6. Disable Rule
    const disabled = await disableRuleApi({
      key: "rule_admin_test_1",
      workspaceId,
      authorization,
    });
    expect(disabled.enabled).toBe(false);
  });
});
