// COSA Automation MVP — Company-owned outcome projection (Task 6).
// docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
//
// The Agent Platform signs compact reference events; Company verifies the
// service token, then projects only allowed run state onto the invocation with a
// terminal-absorbing state machine. Event data is NON-authoritative for any
// business mutation. Replays and out-of-order events cannot regress a terminal
// state. A cross-workspace or unknown invocation is rejected without leaking
// metadata.

import { APIError, Header } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { automationInvocations, automationInvocationEvents } = schema;

const TERMINAL = new Set(["COMPLETED", "FAILED", "CANCELLED"]);

// Agent run state -> invocation state. Anything unmapped is refused.
const RUN_STATE_TO_INVOCATION: Record<string, string> = {
  QUEUED: "QUEUED",
  LEASED: "LEASED",
  RUNNING: "RUNNING",
  WAITING_APPROVAL: "WAITING_APPROVAL",
  BLOCKED: "BLOCKED",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  CANCELLED: "CANCELLED",
};

// A conservative forward-only ordering so an out-of-order RUNNING after a
// COMPLETED (or a WAITING_APPROVAL after BLOCKED) never rewinds the projection.
const STATE_RANK: Record<string, number> = {
  REQUESTED: 0,
  QUEUED: 1,
  LEASED: 2,
  RUNNING: 3,
  WAITING_APPROVAL: 4,
  CANCEL_REQUESTED: 4,
  BLOCKED: 5,
  COMPLETED: 9,
  FAILED: 9,
  CANCELLED: 9,
};

export interface AutomationRunStateChangedEvent {
  eventType: "automation.run.state_changed.v1";
  invocationId: string;
  runId: string;
  workspaceId: string;
  state: string;
  sequence: number;
  observedAt: string;
  manifestHash: string;
  correlationId: string;
}

export interface AutomationRunOutcomeEvent {
  eventType: "automation.run.outcome.v1";
  invocationId: string;
  runId: string;
  workspaceId: string;
  outcome: string;
  blockedCause?: string;
  failureReason?: string;
  evidenceRefs?: string[];
  sequence: number;
  observedAt: string;
  manifestHash: string;
  correlationId: string;
}

export type AutomationOutcomeEvent = AutomationRunStateChangedEvent | AutomationRunOutcomeEvent;

export interface ProjectAutomationOutcomeRequest {
  event: AutomationOutcomeEvent;
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
}

export interface ProjectAutomationOutcomeResult {
  projected: boolean;
  state: string;
}

function requireServiceToken(req: ProjectAutomationOutcomeRequest): void {
  const expected = process.env.COSA_WORKER_SERVICE_TOKEN ?? "dev-worker-service-token";
  const token =
    req.serviceToken || (req.authorization ? req.authorization.replace(/^Bearer\s+/i, "") : "");
  if (!token || token !== expected) {
    throw APIError.unauthenticated("invalid or missing service token");
  }
}

export async function projectAutomationOutcome(
  req: ProjectAutomationOutcomeRequest
): Promise<ProjectAutomationOutcomeResult> {
  requireServiceToken(req);
  const ev = req.event;
  if (!ev || !ev.invocationId || !ev.workspaceId || !ev.runId) {
    throw APIError.invalidArgument("missing required event fields");
  }

  const targetState =
    ev.eventType === "automation.run.outcome.v1"
      ? RUN_STATE_TO_INVOCATION[ev.outcome]
      : RUN_STATE_TO_INVOCATION[ev.state];
  if (!targetState) {
    throw APIError.invalidArgument("unmapped run state");
  }

  const wsId = BigInt(ev.workspaceId);

  return db.transaction(async (tx) => {
    const [inv] = await tx
      .select()
      .from(automationInvocations)
      .where(
        and(eq(automationInvocations.id, BigInt(ev.invocationId)), eq(automationInvocations.workspaceId, wsId))
      )
      .limit(1);

    // Unknown / cross-workspace: 404 with no detail.
    if (!inv) throw APIError.notFound("automation invocation not found");

    // Terminal is absorbing.
    if (TERMINAL.has(inv.state)) {
      return { projected: false, state: inv.state };
    }
    // Never rewind.
    if ((STATE_RANK[targetState] ?? 0) < (STATE_RANK[inv.state] ?? 0)) {
      return { projected: false, state: inv.state };
    }
    // No-op if unchanged (idempotent replay).
    if (targetState === inv.state && inv.agentRunId === ev.runId) {
      return { projected: false, state: inv.state };
    }

    await tx
      .update(automationInvocations)
      .set({
        state: targetState,
        agentRunId: ev.runId,
        blockedReason:
          ev.eventType === "automation.run.outcome.v1" ? ev.blockedCause ?? null : null,
        version: inv.version + 1,
        updatedAt: new Date(),
      })
      .where(and(eq(automationInvocations.id, inv.id), eq(automationInvocations.workspaceId, wsId)));

    await tx.insert(automationInvocationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      invocationId: inv.id,
      seq: inv.version + 1,
      eventType: ev.eventType,
      payloadJson: {
        state: targetState,
        runId: ev.runId,
        manifestHash: ev.manifestHash,
        ...(ev.eventType === "automation.run.outcome.v1"
          ? { evidenceRefs: ev.evidenceRefs ?? [], failureReason: ev.failureReason ?? null }
          : {}),
      },
    });

    return { projected: true, state: targetState };
  });
}
