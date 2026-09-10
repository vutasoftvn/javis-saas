// COSA Automation MVP — Run Inspector + Needs You projection (Task 8 backend).
// docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
//
// Tenant-scoped Company projection built from automation_invocations +
// automation_invocation_events (the accepted Agent outcome stream). It returns
// identity, pinned revision/hash, lifecycle, timing, the capability/step
// timeline, evidence refs and an actionable failure reason — never raw content,
// tokens or a foreign workspace's events. An unknown / new run state maps to
// "unavailable", never "completed".

import { APIError, Header } from "encore.dev/api";
import { and, asc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { mvpItem, mvpList, MvpSuccess } from "../../shared/contracts/mvp-response";

const { automationInvocations, automationInvocationEvents } = schema;

const SOURCE_REF = { kind: "company_db" as const, ref: "operating.automation_invocations" };

// Invocation state -> a UI-safe run state. Anything unmapped is "unavailable".
const RUN_STATE_UI: Record<string, string> = {
  REQUESTED: "PENDING",
  QUEUED: "PENDING",
  LEASED: "RUNNING",
  RUNNING: "RUNNING",
  WAITING_APPROVAL: "WAITING_APPROVAL",
  CANCEL_REQUESTED: "RUNNING",
  BLOCKED: "BLOCKED",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  CANCELLED: "CANCELLED",
};

interface WsHeaders {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface AutomationRunStepView {
  name: string;
  state: string;
  retryCount: number;
  policyDecision: string | null;
  failureReason: string | null;
  evidenceRef: string | null;
}

export interface AutomationRunInspectorView {
  invocationId: string;
  automationKey: string;
  revisionNo: number;
  revisionHash: string;
  state: string;
  createdAt: string;
  updatedAt: string;
  steps: AutomationRunStepView[];
  evidenceRefs: string[];
  sourceHealth: string;
  failureReason: string | null;
  agentRunId: string | null;
}

export interface NeedsYouItemView {
  invocationId: string;
  automationKey: string;
  kind: string;
  observedAt: string;
}

export async function getAutomationRunInspector(
  params: WsHeaders & { invocationId: string }
): Promise<MvpSuccess<AutomationRunInspectorView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const wsId = BigInt(ctx.workspaceId);

  const [inv] = await db
    .select()
    .from(automationInvocations)
    .where(
      and(
        eq(automationInvocations.id, BigInt(params.invocationId)),
        eq(automationInvocations.workspaceId, wsId)
      )
    )
    .limit(1);
  if (!inv) throw APIError.notFound("automation invocation not found");

  const events = await db
    .select()
    .from(automationInvocationEvents)
    .where(
      and(
        eq(automationInvocationEvents.invocationId, inv.id),
        eq(automationInvocationEvents.workspaceId, wsId)
      )
    )
    .orderBy(asc(automationInvocationEvents.seq));

  const uiState = RUN_STATE_UI[inv.state] ?? "UNAVAILABLE";

  // Steps come from accepted outcome events; a forged runtime signal without a
  // matching invocation is simply never in this list.
  const steps: AutomationRunStepView[] = [];
  const evidenceRefs: string[] = [];
  let failureReason: string | null = inv.blockedReason ?? null;
  for (const ev of events) {
    const p = (ev.payloadJson ?? {}) as Record<string, unknown>;
    if (ev.eventType === "automation.run.outcome.v1") {
      const refs = (p.evidenceRefs as string[] | undefined) ?? [];
      evidenceRefs.push(...refs);
      if (p.failureReason) failureReason = String(p.failureReason);
    }
    if (ev.eventType === "automation.run.state_changed.v1" || ev.eventType.startsWith("invocation.")) {
      steps.push({
        name: ev.eventType.replace(/^automation\.run\.|^invocation\./, ""),
        state: String((p.state as string | undefined) ?? inv.state),
        retryCount: 0,
        policyDecision: null,
        failureReason: null,
        evidenceRef: null,
      });
    }
  }

  const view: AutomationRunInspectorView = {
    invocationId: inv.id.toString(),
    automationKey: inv.automationKey,
    revisionNo: inv.revisionNo,
    revisionHash: inv.revisionHash,
    state: uiState,
    createdAt: inv.createdAt.toISOString(),
    updatedAt: inv.updatedAt.toISOString(),
    steps,
    evidenceRefs: [...new Set(evidenceRefs)],
    sourceHealth: inv.state === "BLOCKED" ? "degraded" : "ok",
    failureReason,
    agentRunId: inv.agentRunId,
  };
  return mvpItem(view, [SOURCE_REF]);
}

export async function listAutomationNeedsYou(
  params: WsHeaders
): Promise<MvpSuccess<readonly NeedsYouItemView[]>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const wsId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(automationInvocations)
    .where(eq(automationInvocations.workspaceId, wsId));

  const NEEDS: Record<string, string> = {
    WAITING_APPROVAL: "APPROVAL_REQUIRED",
    BLOCKED: "BLOCKED",
    FAILED: "FAILED",
  };
  const items: NeedsYouItemView[] = rows
    .filter((r) => NEEDS[r.state] != null)
    .map((r) => ({
      invocationId: r.id.toString(),
      automationKey: r.automationKey,
      kind: r.state === "BLOCKED" && r.blockedReason === "LOCAL_RUNTIME_UNAVAILABLE"
        ? "LOCAL_RUNTIME_UNAVAILABLE"
        : NEEDS[r.state],
      observedAt: r.updatedAt.toISOString(),
    }));
  return mvpList(items, [SOURCE_REF]);
}
