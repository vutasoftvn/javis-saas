// COSA Automation MVP — Control Plane dispatch projection + fencing (Task 4).
// docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
//
// The durable queue stays `control_plane.scheduled_tasks` (claim token +
// visibility timeout fencing already proven). This module keeps a thin
// per-invocation projection in `control_plane.automation_dispatches` so the
// Control Plane can answer "what happened to invocation X" with opaque
// references only — no business content, prompt, credential or grant.

import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { scheduleTask } from "./control-plane-scheduler.service";

const AUTOMATION_TARGET_SPEC = "cosa.agents.operations";
const AUTOMATION_TASK_TYPE = "automation_run";

export interface AutomationDispatchEnvelope {
  schema_version: number;
  invocation_id: string;
  workspace_id: string;
  automation_key: string;
  revision: number;
  revision_hash: string;
  trigger_kind: string;
  trigger_identity: string;
  correlation_id: string;
  requested_at: string;
}

export interface AutomationDispatchRow {
  invocationId: string;
  workspaceId: string;
  automationKey: string;
  revision: number;
  revisionHash: string;
  triggerKind: string;
  triggerIdentity: string;
  correlationId: string;
  taskId: string | null;
  claimToken: string | null;
  state: string;
  lastError: string | null;
}

const FORBIDDEN_ENVELOPE_KEYS = [
  "input",
  "input_payload",
  "prompt",
  "credential",
  "secret",
  "authorization",
  "connector_grant",
  "document",
];

export function assertOpaqueEnvelope(envelope: Record<string, unknown>): void {
  for (const k of FORBIDDEN_ENVELOPE_KEYS) {
    if (k in envelope) {
      throw new Error(`automation dispatch envelope must not carry '${k}'`);
    }
  }
  const required = [
    "schema_version", "invocation_id", "workspace_id", "automation_key",
    "revision", "revision_hash", "trigger_kind", "trigger_identity",
    "correlation_id", "requested_at",
  ];
  for (const k of required) {
    if (envelope[k] === undefined || envelope[k] === null) {
      throw new Error(`automation dispatch envelope missing '${k}'`);
    }
  }
}

function rowFrom(r: Record<string, unknown>): AutomationDispatchRow {
  return {
    invocationId: String(r.invocation_id),
    workspaceId: String(r.workspace_id),
    automationKey: String(r.automation_key),
    revision: Number(r.revision),
    revisionHash: String(r.revision_hash),
    triggerKind: String(r.trigger_kind),
    triggerIdentity: String(r.trigger_identity),
    correlationId: String(r.correlation_id),
    taskId: r.task_id == null ? null : String(r.task_id),
    claimToken: r.claim_token == null ? null : String(r.claim_token),
    state: String(r.state),
    lastError: r.last_error == null ? null : String(r.last_error),
  };
}

/** Idempotent on invocation_id. Returns the existing row untouched on a
 *  duplicate delivery so the caller can reuse its task_id. */
export async function recordAutomationDispatch(
  envelope: AutomationDispatchEnvelope
): Promise<AutomationDispatchRow> {
  assertOpaqueEnvelope(envelope as unknown as Record<string, unknown>);
  const res = await db.execute(sql`
    INSERT INTO control_plane.automation_dispatches
      (invocation_id, workspace_id, automation_key, revision, revision_hash,
       trigger_kind, trigger_identity, correlation_id, state)
    VALUES
      (${envelope.invocation_id}, ${envelope.workspace_id}, ${envelope.automation_key},
       ${envelope.revision}, ${envelope.revision_hash}, ${envelope.trigger_kind},
       ${envelope.trigger_identity}, ${envelope.correlation_id}, 'received')
    ON CONFLICT (invocation_id) DO UPDATE SET updated_at = now()
    RETURNING *;
  `);
  return rowFrom((res as unknown as { rows: Record<string, unknown>[] }).rows[0]);
}

export async function markAutomationDispatchScheduled(
  invocationId: string,
  taskId: string
): Promise<void> {
  await db.execute(sql`
    UPDATE control_plane.automation_dispatches
    SET task_id = ${taskId}, state = 'scheduled', scheduled_at = now(), updated_at = now()
    WHERE invocation_id = ${invocationId} AND state IN ('received', 'scheduled');
  `);
}

export async function markAutomationDispatchClaimed(
  invocationId: string,
  taskId: string,
  claimToken: string
): Promise<void> {
  await db.execute(sql`
    UPDATE control_plane.automation_dispatches
    SET claim_token = ${claimToken}, state = 'claimed', updated_at = now()
    WHERE invocation_id = ${invocationId} AND task_id = ${taskId};
  `);
}

/** Fenced terminal transition. A completion whose (taskId, claimToken) does not
 *  match the current dispatch row is rejected — a stale worker cannot overwrite
 *  a newer attempt's terminal state. */
export async function completeAutomationDispatch(params: {
  invocationId: string;
  taskId: string;
  claimToken: string;
  success: boolean;
  error?: string;
}): Promise<{ ok: boolean }> {
  const res = await db.execute(sql`
    UPDATE control_plane.automation_dispatches
    SET state = ${params.success ? "completed" : "failed"},
        last_error = ${params.error ?? null},
        completed_at = now(),
        updated_at = now()
    WHERE invocation_id = ${params.invocationId}
      AND task_id = ${params.taskId}
      AND claim_token = ${params.claimToken}
      AND state NOT IN ('completed', 'failed')
    RETURNING invocation_id;
  `);
  const rows = (res as unknown as { rows: unknown[] }).rows;
  return { ok: rows.length === 1 };
}

function deterministicRunId(invocationId: string): string {
  // Stable per invocation so a duplicate delivery reuses the same run.
  return `run_auto_${invocationId}`;
}

/** Idempotent on invocation_id. Records the opaque dispatch projection, then
 *  enqueues one `automation_run` task into the durable scheduler with an
 *  `evt:`-prefixed coalescing key (strictly idempotent across every status). */
export async function scheduleAutomationDispatch(
  envelope: AutomationDispatchEnvelope
): Promise<AutomationDispatchRow> {
  const existing = await getAutomationDispatch(envelope.invocation_id);
  if (existing?.taskId) return existing;

  await recordAutomationDispatch(envelope);
  const runId = deterministicRunId(envelope.invocation_id);
  const task = await scheduleTask({
    targetSpecId: AUTOMATION_TARGET_SPEC,
    targetSpecKind: "agent",
    coalescingKey: `evt:automation:${envelope.invocation_id}`,
    inputPayload: {
      task_type: AUTOMATION_TASK_TYPE,
      run_id: runId,
      invocation_id: envelope.invocation_id,
      workspace_id: envelope.workspace_id,
      automation_key: envelope.automation_key,
      revision: envelope.revision,
      revision_hash: envelope.revision_hash,
      trigger_kind: envelope.trigger_kind,
      trigger_identity: envelope.trigger_identity,
      correlation_id: envelope.correlation_id,
      agent_profile: "operations",
    },
  });
  await markAutomationDispatchScheduled(envelope.invocation_id, task.id);
  const row = await getAutomationDispatch(envelope.invocation_id);
  return row!;
}

export async function getAutomationDispatch(
  invocationId: string
): Promise<AutomationDispatchRow | null> {
  const res = await db.execute(sql`
    SELECT * FROM control_plane.automation_dispatches WHERE invocation_id = ${invocationId};
  `);
  const rows = (res as unknown as { rows: Record<string, unknown>[] }).rows;
  return rows.length ? rowFrom(rows[0]) : null;
}
