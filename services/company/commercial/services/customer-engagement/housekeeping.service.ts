import { and, eq, isNull, lt, sql } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementOutboundDeliveries,
  engagementMessages,
  engagementAutomationSchedules,
  engagementAutomationRules,
  engagementThreads,
} from "../../../shared/db/schema/customer-engagement";
import { getChannelAdapter } from "./channel-adapters/registry";
import { AutomationFacts, buildAutomationFacts } from "./automation/facts";
import { Predicate, evaluatePredicate } from "./automation/predicate";
import { AutomationAction, applyAction } from "./automation/actions";
import { evaluateRulesSafe } from "./automation/evaluator";

export interface HousekeepingTickStats {
  reconciled: number;
  delivered: number;
  failed: number;
  assumedDelivered: number;
  slaEscalated?: number;
  automationDelayed?: {
    claimed: number;
    executed: number;
    skipped: number;
  };
}

export async function runHousekeepingTick(limit = 20): Promise<HousekeepingTickStats> {
  const stats: HousekeepingTickStats = {
    reconciled: 0,
    delivered: 0,
    failed: 0,
    assumedDelivered: 0,
    slaEscalated: 0,
    automationDelayed: {
      claimed: 0,
      executed: 0,
      skipped: 0,
    },
  };

  // 1. Reconcile sent deliveries
  const rows = await db.execute(sql`
    SELECT * FROM engagement.engagement_outbound_deliveries
    WHERE status = 'sent'
      AND delivered_at IS NULL
      AND created_at < now() - interval '10 minutes'
    ORDER BY created_at ASC
    LIMIT ${limit};
  `);

  const deliveries = rows.rows as any[];
  stats.reconciled = deliveries.length;

  for (const delivery of deliveries) {
    const deliveryId = BigInt(delivery.id);
    const messageId = BigInt(delivery.message_id);
    const externalMessageId = delivery.external_message_id;
    const createdAt = new Date(delivery.created_at);

    if (!externalMessageId) continue;

    try {
      const adapter = getChannelAdapter(delivery.channel_type);
      const status = await adapter.getDeliveryStatus(externalMessageId);

      if (status === "delivered") {
        await db
          .update(engagementOutboundDeliveries)
          .set({ status: "delivered", deliveredAt: new Date() })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        await db
          .update(engagementMessages)
          .set({ deliveryState: "delivered" })
          .where(eq(engagementMessages.id, messageId));

        stats.delivered++;
      } else if (status === "failed") {
        await db
          .update(engagementOutboundDeliveries)
          .set({
            status: "failed",
            deadLetterReason: "provider_reported_failure",
            lastError: "provider reported failure during reconcile",
          })
          .where(eq(engagementOutboundDeliveries.id, deliveryId));

        await db
          .update(engagementMessages)
          .set({ deliveryState: "failed" })
          .where(eq(engagementMessages.id, messageId));

        stats.failed++;
      } else {
        const ageHours = (Date.now() - createdAt.getTime()) / (1000 * 3600);
        if (ageHours >= 24) {
          await db
            .update(engagementOutboundDeliveries)
            .set({
              status: "delivered",
              deliveredAt: new Date(),
              lastError: "assumed_delivered",
            })
            .where(eq(engagementOutboundDeliveries.id, deliveryId));

          await db
            .update(engagementMessages)
            .set({ deliveryState: "delivered" })
            .where(eq(engagementMessages.id, messageId));

          stats.assumedDelivered++;
        }
      }
    } catch {
      // Ignore provider query failure during housekeeping tick
    }
  }

  // 2. Process delayed automation schedules
  const schedRows = await db.execute(sql`
    SELECT * FROM engagement.engagement_automation_schedules
    WHERE status = 'pending'
      AND due_at <= now()
    ORDER BY due_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT ${limit};
  `);

  const schedules = schedRows.rows as any[];
  stats.automationDelayed!.claimed = schedules.length;

  for (const sched of schedules) {
    const schedId = BigInt(sched.id);
    const wsId = BigInt(sched.workspace_id);

    const ctx = {
      workspaceId: sched.workspace_id.toString(),
      userId: "system",
      membershipRole: "system",
      permissions: ["*"],
      correlationId: `corr_sched_${sched.id}`,
    };

    // 2.1 Re-check rule enabled and valid
    const rules = await db
      .select()
      .from(engagementAutomationRules)
      .where(
        and(
          eq(engagementAutomationRules.workspaceId, wsId),
          eq(engagementAutomationRules.ruleKey, sched.rule_key),
          eq(engagementAutomationRules.version, Number(sched.rule_version)),
          eq(engagementAutomationRules.enabled, true)
        )
      );

    if (rules.length === 0) {
      await db
        .update(engagementAutomationSchedules)
        .set({ status: "skipped", skipReason: "rule_disabled" })
        .where(eq(engagementAutomationSchedules.id, schedId));
      stats.automationDelayed!.skipped++;
      continue;
    }

    // 2.2 Build current facts
    let facts: AutomationFacts;
    try {
      facts = await buildAutomationFacts(sched.thread_id.toString(), ctx);
    } catch {
      await db
        .update(engagementAutomationSchedules)
        .set({ status: "skipped", skipReason: "thread_not_found" })
        .where(eq(engagementAutomationSchedules.id, schedId));
      stats.automationDelayed!.skipped++;
      continue;
    }

    // 2.3 Re-evaluate condition
    const stillMatches = evaluatePredicate(sched.condition as Predicate, facts);
    if (!stillMatches) {
      await db
        .update(engagementAutomationSchedules)
        .set({ status: "skipped", skipReason: "condition_changed" })
        .where(eq(engagementAutomationSchedules.id, schedId));
      stats.automationDelayed!.skipped++;
      continue;
    }

    // 2.4 Re-check ownership / human takeover
    if (facts.thread.activeMode === "human_assigned") {
      await db
        .update(engagementAutomationSchedules)
        .set({ status: "skipped", skipReason: "ownership_changed" })
        .where(eq(engagementAutomationSchedules.id, schedId));
      stats.automationDelayed!.skipped++;
      continue;
    }

    // 2.5 Apply action
    const res = await applyAction(
      sched.action as AutomationAction,
      {
        threadId: sched.thread_id.toString(),
        ruleKey: sched.rule_key,
        ruleVersion: Number(sched.rule_version),
        trigger: "delayed_schedule",
        actionIndex: Number(sched.action_index),
        dedupeKey: `sched:${sched.id}`,
      },
      ctx
    );

    if (res.outcome === "applied" || res.outcome === "already_applied") {
      await db
        .update(engagementAutomationSchedules)
        .set({ status: "done" })
        .where(eq(engagementAutomationSchedules.id, schedId));
      stats.automationDelayed!.executed++;
    } else {
      await db
        .update(engagementAutomationSchedules)
        .set({ status: "error", skipReason: res.outcome })
        .where(eq(engagementAutomationSchedules.id, schedId));
      stats.automationDelayed!.skipped++;
    }
  }

  // 3. Time sweep for open threads (SLA escalation & recurring time-based rules)
  const openThreads = await db.execute(sql`
    SELECT id, workspace_id FROM engagement.engagement_threads
    WHERE status IN ('open', 'in_progress')
    ORDER BY created_at DESC
    LIMIT 200;
  `);

  for (const t of openThreads.rows as any[]) {
    const threadCtx = {
      workspaceId: t.workspace_id.toString(),
      userId: "system",
      membershipRole: "system",
      permissions: ["*"],
      correlationId: `corr_sweep_${t.id}`,
    };
    await evaluateRulesSafe({ trigger: "time_sweep", threadId: t.id.toString() }, threadCtx);
  }

  return stats;
}
