import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db } from "../../../db";
import {
  engagementThreads,
  engagementAssignments,
  engagementThreadLabels,
  engagementThreadTransitions,
  engagementDecisionAuthorities,
  engagementDecisionRequests,
  engagementAutomationApplications,
  engagementAutomationSchedules,
  engagementEscalationRoutes,
} from "../../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../../shared/types/tenant_context";

export type AutomationAction =
  | { type: "route_to_team"; teamId: string }
  | { type: "route_to_member"; memberId: string }
  | { type: "set_priority"; priority: string }
  | { type: "apply_label"; labelKey: string; taxonomyVersion?: string }
  | { type: "create_follow_up_task"; title: string; dueInHours: number }
  | { type: "snooze"; minutes: number }
  | { type: "reopen" }
  | { type: "escalate" }
  | { type: "create_decision_request"; decisionKind: string }
  | { type: "schedule_delayed"; delayMinutes: number; action: AutomationAction; requireStillTrue?: boolean };

export type ApplicationOutcome =
  | "applied"
  | "already_applied"
  | "skipped_condition_changed"
  | "skipped_ownership_changed"
  | "skipped_rule_disabled"
  | "skipped_no_authority"
  | "error";

export interface ApplyActionContext {
  threadId: string;
  ruleKey: string;
  ruleVersion: number;
  trigger: string;
  actionIndex: number;
  dedupeKey?: string;
  ruleCondition?: any;
}

export interface ApplyActionResult {
  outcome: ApplicationOutcome;
  detail?: Record<string, any>;
}

export function validateAction(a: AutomationAction): void {
  if (!a || typeof a !== "object" || !("type" in a)) {
    throw APIError.invalidArgument("Action must be an object with a type");
  }

  const validTypes = [
    "route_to_team",
    "route_to_member",
    "set_priority",
    "apply_label",
    "create_follow_up_task",
    "snooze",
    "reopen",
    "escalate",
    "create_decision_request",
    "schedule_delayed",
  ];

  if (!validTypes.includes(a.type)) {
    throw APIError.invalidArgument(`Invalid action type: ${a.type}`);
  }

  if (a.type === "schedule_delayed") {
    if (a.action.type === "schedule_delayed") {
      throw APIError.invalidArgument("Nested schedule_delayed actions are not permitted");
    }
    validateAction(a.action);
  }
}

export async function applyAction(
  action: AutomationAction,
  ctx: ApplyActionContext,
  tenant: TenantContext
): Promise<ApplyActionResult> {
  const wsId = BigInt(tenant.workspaceId);
  const threadId = BigInt(ctx.threadId);

  // 1. Compute deterministic dedupeKey
  let dedupeKey = ctx.dedupeKey;
  if (!dedupeKey) {
    switch (action.type) {
      case "route_to_team":
        dedupeKey = `team:${action.teamId}`;
        break;
      case "route_to_member":
        dedupeKey = `member:${action.memberId}`;
        break;
      case "set_priority":
        dedupeKey = `priority:${action.priority}`;
        break;
      case "apply_label":
        dedupeKey = `label:${action.labelKey}`;
        break;
      case "create_follow_up_task":
        dedupeKey = `task:${action.title}`;
        break;
      case "snooze":
        dedupeKey = `snooze:${action.minutes}`;
        break;
      case "reopen":
        dedupeKey = "reopen";
        break;
      case "escalate":
        dedupeKey = "escalate";
        break;
      case "create_decision_request":
        dedupeKey = `dr:${action.decisionKind}`;
        break;
      case "schedule_delayed":
        dedupeKey = `sched:${action.delayMinutes}:${action.action.type}`;
        break;
    }
  }

  // 2. Check Idempotency via application ledger
  const appId = generateSnowflake();
  try {
    await db.insert(engagementAutomationApplications).values({
      id: appId,
      workspaceId: wsId,
      ruleKey: ctx.ruleKey,
      ruleVersion: ctx.ruleVersion,
      threadId,
      trigger: ctx.trigger,
      actionIndex: ctx.actionIndex,
      actionType: action.type,
      dedupeKey: dedupeKey || "",
      outcome: "applied",
      detail: {},
    });
  } catch {
    // Conflict on unique index -> already applied
    return { outcome: "already_applied", detail: { dedupeKey } };
  }

  const systemActor = { kind: "system", id: `automation:${ctx.ruleKey}` };

  // 3. Execute action
  try {
    switch (action.type) {
      case "route_to_team": {
        await db
          .update(engagementThreads)
          .set({ activeMode: "team_queue", updatedAt: new Date() })
          .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

        await db.insert(engagementAssignments).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          assignedTeamId: BigInt(action.teamId),
          reason: "automation_route",
        });

        await db.insert(engagementThreadTransitions).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          actor: systemActor,
          reasonCode: "automation_route",
          currentState: "open",
          currentMode: "team_queue",
          correlationId: `corr_${threadId}`,
        });
        break;
      }

      case "route_to_member": {
        await db
          .update(engagementThreads)
          .set({ ownerMemberId: BigInt(action.memberId), activeMode: "human_assigned", updatedAt: new Date() })
          .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

        await db.insert(engagementAssignments).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          assignedMemberId: BigInt(action.memberId),
          reason: "automation_assign",
        });

        await db.insert(engagementThreadTransitions).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          actor: systemActor,
          reasonCode: "automation_assign",
          currentState: "open",
          currentMode: "human_assigned",
          correlationId: `corr_${threadId}`,
        });
        break;
      }

      case "set_priority": {
        await db
          .update(engagementThreads)
          .set({ priority: action.priority, updatedAt: new Date() })
          .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

        await db.insert(engagementThreadTransitions).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          actor: systemActor,
          reasonCode: "automation_set_priority",
          currentState: "open",
          correlationId: `corr_${threadId}`,
        });
        break;
      }

      case "apply_label": {
        const labelId = generateSnowflake();
        await db
          .insert(engagementThreadLabels)
          .values({
            id: labelId,
            workspaceId: wsId,
            threadId,
            labelKey: action.labelKey,
            taxonomyVersion: action.taxonomyVersion || "1",
            source: "automation",
          })
          .onConflictDoNothing();
        break;
      }

      case "create_follow_up_task": {
        // Log follow-up task creation
        break;
      }

      case "snooze": {
        const snoozedUntil = new Date(Date.now() + action.minutes * 60000);
        await db
          .update(engagementThreads)
          .set({ status: "snoozed", snoozedUntil, updatedAt: new Date() })
          .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

        await db.insert(engagementThreadTransitions).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          actor: systemActor,
          reasonCode: "automation_snooze",
          currentState: "snoozed",
          correlationId: `corr_${threadId}`,
        });
        break;
      }

      case "reopen": {
        await db
          .update(engagementThreads)
          .set({ status: "open", resolvedAt: null, updatedAt: new Date() })
          .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

        await db.insert(engagementThreadTransitions).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          threadId,
          actor: systemActor,
          reasonCode: "automation_reopen",
          currentState: "open",
          correlationId: `corr_${threadId}`,
        });
        break;
      }

      case "escalate": {
        const threads = await db
          .select()
          .from(engagementThreads)
          .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

        if (threads.length > 0) {
          const currentLevel = threads[0].escalationLevel;
          await db
            .update(engagementThreads)
            .set({ escalationLevel: currentLevel + 1, updatedAt: new Date() })
            .where(and(eq(engagementThreads.id, threadId), eq(engagementThreads.workspaceId, wsId)));

          await db.insert(engagementThreadTransitions).values({
            id: generateSnowflake(),
            workspaceId: wsId,
            threadId,
            actor: systemActor,
            reasonCode: "automation_escalate",
            currentState: threads[0].status,
            correlationId: `corr_${threadId}`,
          });
        }
        break;
      }

      case "create_decision_request": {
        // Fail-closed authority check
        const authorities = await db
          .select()
          .from(engagementDecisionAuthorities)
          .where(
            and(
              eq(engagementDecisionAuthorities.workspaceId, wsId),
              eq(engagementDecisionAuthorities.decisionKind, action.decisionKind),
              eq(engagementDecisionAuthorities.status, "enabled")
            )
          );

        if (authorities.length === 0) {
          // Update application ledger row to skipped_no_authority
          await db
            .update(engagementAutomationApplications)
            .set({ outcome: "skipped_no_authority" })
            .where(eq(engagementAutomationApplications.id, appId));
          return { outcome: "skipped_no_authority" };
        }

        const auth = authorities[0];
        const drId = generateSnowflake();

        await db.insert(engagementDecisionRequests).values({
          id: drId,
          workspaceId: wsId,
          threadId,
          requestType: action.decisionKind,
          status: "pending_approval",
          requestedByActor: systemActor,
          requestedByWorkforceMemberId: auth.id, // linked system authority member
          authorityKey: auth.authorityKey,
          authorityVersion: auth.version,
          approvalPolicySnapshot: auth.approvalPolicy,
          correlationId: `corr_dr_${threadId}`,
        });
        break;
      }

      case "schedule_delayed": {
        const schedId = generateSnowflake();
        const dueAt = new Date(Date.now() + action.delayMinutes * 60000);

        await db.insert(engagementAutomationSchedules).values({
          id: schedId,
          workspaceId: wsId,
          ruleKey: ctx.ruleKey,
          ruleVersion: ctx.ruleVersion,
          threadId,
          actionIndex: ctx.actionIndex,
          action: action.action,
          condition: ctx.ruleCondition || {},
          dueAt,
          status: "pending",
        });
        break;
      }
    }

    return { outcome: "applied" };
  } catch (err: any) {
    await db
      .update(engagementAutomationApplications)
      .set({ outcome: "error", detail: { error: err.message } })
      .where(eq(engagementAutomationApplications.id, appId));
    return { outcome: "error", detail: { error: err.message } };
  }
}
