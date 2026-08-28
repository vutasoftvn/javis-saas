import { and, eq } from "drizzle-orm";
import { db } from "../../../db";
import { engagementAutomationRules } from "../../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../../shared/types/tenant_context";
import { AutomationRule } from "./rule-model";

export const DEFAULT_ENGAGEMENT_RULES: AutomationRule[] = [
  {
    ruleKey: "sla_first_response_escalation",
    version: 1,
    name: "SLA First Response Escalation",
    trigger: "time_sweep",
    priority: 50,
    condition: {
      all: [
        { fact: "sla.firstResponseBreached", op: "eq", value: true },
        { fact: "thread.firstResponded", op: "eq", value: false },
        { fact: "thread.status", op: "ne", value: "resolved" },
      ],
    },
    actions: [{ type: "escalate" }],
    enabled: true,
    stopOnMatch: false,
  },
  {
    ruleKey: "route_by_locale_vi",
    version: 1,
    name: "Route By Locale Vietnamese",
    trigger: "thread_opened",
    priority: 100,
    condition: {
      fact: "inbox.locale",
      op: "eq",
      value: "vi",
    },
    actions: [{ type: "apply_label", labelKey: "locale_vi" }],
    enabled: false,
    stopOnMatch: false,
  },
];

export async function seedDefaultRules(ctx: TenantContext): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);

  for (const rule of DEFAULT_ENGAGEMENT_RULES) {
    const existing = await db
      .select()
      .from(engagementAutomationRules)
      .where(
        and(
          eq(engagementAutomationRules.workspaceId, wsId),
          eq(engagementAutomationRules.ruleKey, rule.ruleKey),
          eq(engagementAutomationRules.version, rule.version)
        )
      );

    if (existing.length === 0) {
      const id = generateSnowflake();
      await db.insert(engagementAutomationRules).values({
        id,
        workspaceId: wsId,
        ruleKey: rule.ruleKey,
        version: rule.version,
        name: rule.name,
        trigger: rule.trigger,
        priority: rule.priority,
        condition: rule.condition,
        actions: rule.actions,
        enabled: rule.enabled,
        stopOnMatch: rule.stopOnMatch,
        effectiveFrom: new Date(Date.now() - 60000),
        effectiveUntil: null,
      });
    }
  }
}
