// COSA Automation MVP — idempotent invocations + outbox-only Company→Agent
// handoff (Task 3). docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
//
// createAutomationInvocation runs in ONE transaction: read the published
// revision, derive the idempotency key, insert a REQUESTED invocation and append
// a signed outbox event. It never calls Control or Agent synchronously. The
// outbox event payload is exactly AutomationDispatchEnvelopeV1 — reference-only,
// no business content, prompt, secret, grant or document.

import { APIError } from "encore.dev/api";
import { createHash } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mvpItem, MvpSuccess } from "../../shared/contracts/mvp-response";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { getCuratedBlueprint } from "./automation-blueprint-registry";
import type { AutomationTriggerContract } from "./automation-definition.service";

const { automationDefinitions, automationRevisions, automationInvocations, automationInvocationEvents } =
  schema;

const SOURCE_REF = { kind: "company_db" as const, ref: "operating.automation_invocations" };
const REQUESTED_EVENT_TYPE = "automation.invocation.requested.v1";
const CANCEL_EVENT_TYPE = "automation.invocation.cancel_requested.v1";

export type AutomationTriggerKind = "manual" | "schedule" | "business_event";

export interface CreateAutomationInvocationCommand {
  triggerKind: AutomationTriggerKind;
  /** manual */
  clientRequestId?: string;
  /** schedule */
  scheduleId?: string;
  scheduledFor?: string;
  /** business_event */
  triggerId?: string;
  eventId?: string;
  businessScope?: Record<string, unknown>;
  validatedInputRef?: string;
}

export interface CreateAutomationInvocationParams {
  workspaceId: string;
  authorization?: string;
  definitionId: string;
  command: CreateAutomationInvocationCommand;
}

export interface GetAutomationInvocationParams {
  workspaceId: string;
  authorization?: string;
  invocationId: string;
}

export interface CancelAutomationInvocationParams {
  workspaceId: string;
  authorization?: string;
  invocationId: string;
  expectedVersion: number;
}

export interface AutomationInvocationView {
  readonly id: string;
  readonly workspaceId: string;
  readonly definitionId: string;
  readonly revisionId: string;
  readonly automationKey: string;
  readonly revisionNo: number;
  readonly revisionHash: string;
  readonly idempotencyKey: string;
  readonly triggerKind: AutomationTriggerKind;
  readonly triggerIdentity: string;
  readonly state: string;
  readonly agentRunId: string | null;
  readonly correlationId: string;
  readonly version: number;
  readonly createdAt: string;
  readonly deduplicated: boolean;
}

function canonicalJson(value: unknown): string {
  const norm = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(norm);
    if (v && typeof v === "object") {
      return Object.keys(v as Record<string, unknown>)
        .sort()
        .reduce<Record<string, unknown>>((a, k) => ((a[k] = norm((v as Record<string, unknown>)[k])), a), {});
    }
    return v;
  };
  return JSON.stringify(norm(value));
}

function deriveTriggerIdentity(workspaceId: string, revisionId: string, cmd: CreateAutomationInvocationCommand): string {
  switch (cmd.triggerKind) {
    case "manual":
      if (!cmd.clientRequestId) throw APIError.invalidArgument("manual invocation requires clientRequestId");
      return `${cmd.clientRequestId}`;
    case "schedule":
      if (!cmd.scheduleId || !cmd.scheduledFor) {
        throw APIError.invalidArgument("schedule invocation requires scheduleId and scheduledFor");
      }
      return `${cmd.scheduleId}:${cmd.scheduledFor}`;
    case "business_event":
      if (!cmd.triggerId || !cmd.eventId) {
        throw APIError.invalidArgument("business_event invocation requires triggerId and eventId");
      }
      return `${cmd.triggerId}:${cmd.eventId}`;
    default:
      throw APIError.invalidArgument(`unknown triggerKind ${(cmd as { triggerKind: string }).triggerKind}`);
  }
}

function idempotencyKey(workspaceId: string, revisionId: string, cmd: CreateAutomationInvocationCommand): string {
  const scope = cmd.triggerKind;
  return `${scope}:${workspaceId}:${revisionId}:${deriveTriggerIdentity(workspaceId, revisionId, cmd)}`;
}

interface InvocationRow {
  id: bigint;
  workspaceId: bigint;
  definitionId: bigint;
  revisionId: bigint;
  automationKey: string;
  revisionNo: number;
  revisionHash: string;
  idempotencyKey: string;
  triggerKind: string;
  triggerIdentity: string;
  fingerprintHash: string;
  state: string;
  agentRunId: string | null;
  correlationId: string;
  version: number;
  createdAt: Date;
}

function toView(row: InvocationRow, deduplicated: boolean): AutomationInvocationView {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    definitionId: row.definitionId.toString(),
    revisionId: row.revisionId.toString(),
    automationKey: row.automationKey,
    revisionNo: row.revisionNo,
    revisionHash: row.revisionHash,
    idempotencyKey: row.idempotencyKey,
    triggerKind: row.triggerKind as AutomationTriggerKind,
    triggerIdentity: row.triggerIdentity,
    state: row.state,
    agentRunId: row.agentRunId,
    correlationId: row.correlationId,
    version: row.version,
    createdAt: row.createdAt.toISOString(),
    deduplicated,
  };
}

export async function createAutomationInvocation(
  params: CreateAutomationInvocationParams
): Promise<MvpSuccess<AutomationInvocationView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  if ((ctx.membershipRole || "").toLowerCase() === "agent") {
    throw APIError.permissionDenied("an agent cannot invoke an automation");
  }
  const wsId = BigInt(ctx.workspaceId);
  const cmd = params.command;

  return db.transaction(async (tx) => {
    const [defRow] = await tx
      .select()
      .from(automationDefinitions)
      .where(and(eq(automationDefinitions.id, BigInt(params.definitionId)), eq(automationDefinitions.workspaceId, wsId)))
      .limit(1);
    if (!defRow) throw APIError.notFound("automation definition not found");
    if (defRow.lifecycleState !== "PUBLISHED") {
      throw APIError.failedPrecondition(`automation is ${defRow.lifecycleState}, not PUBLISHED`);
    }
    if (defRow.currentRevisionId == null) {
      throw APIError.failedPrecondition("automation has no published revision");
    }
    const blueprint = getCuratedBlueprint(defRow.automationKey);
    if (!blueprint) throw APIError.internal(`unknown blueprint ${defRow.automationKey}`);

    const [revision] = await tx
      .select()
      .from(automationRevisions)
      .where(
        and(
          eq(automationRevisions.id, defRow.currentRevisionId as bigint),
          eq(automationRevisions.workspaceId, wsId)
        )
      )
      .limit(1);
    if (!revision || revision.publishedAt == null) {
      throw APIError.failedPrecondition("current revision is not published");
    }

    const revisionId = (revision.id as bigint).toString();
    const triggerContract = (revision.triggerContractJson ?? { kind: "manual" }) as AutomationTriggerContract;
    if (triggerContract.kind !== cmd.triggerKind) {
      throw APIError.failedPrecondition(
        `published revision trigger kind is '${triggerContract.kind}', not '${cmd.triggerKind}'`
      );
    }

    const key = idempotencyKey(ctx.workspaceId, revisionId, cmd);
    const triggerIdentity = deriveTriggerIdentity(ctx.workspaceId, revisionId, cmd);
    const fingerprint = createHash("sha256")
      .update(
        canonicalJson({
          definitionId: params.definitionId,
          revisionId,
          revisionHash: revision.revisionHash,
          businessScope: cmd.businessScope ?? {},
          validatedInputRef: cmd.validatedInputRef ?? null,
        })
      )
      .digest("hex");

    const [existing] = (await tx
      .select()
      .from(automationInvocations)
      .where(
        and(
          eq(automationInvocations.workspaceId, wsId),
          eq(automationInvocations.revisionId, revision.id as bigint),
          eq(automationInvocations.idempotencyKey, key)
        )
      )
      .limit(1)) as unknown as InvocationRow[];

    if (existing) {
      if (existing.fingerprintHash !== fingerprint) {
        throw APIError.alreadyExists(
          "an invocation with this idempotency key already exists with a different fingerprint"
        );
      }
      return mvpItem(toView(existing, true), [SOURCE_REF]);
    }

    const id = generateSnowflake();
    const correlationId = ctx.correlationId || `auto-${id.toString()}`;
    const [row] = (await tx
      .insert(automationInvocations)
      .values({
        id,
        workspaceId: wsId,
        definitionId: defRow.id,
        revisionId: revision.id as bigint,
        automationKey: defRow.automationKey,
        revisionNo: revision.revisionNo,
        revisionHash: revision.revisionHash,
        idempotencyKey: key,
        triggerKind: cmd.triggerKind,
        triggerIdentity,
        callerPrincipal: `user:${ctx.userId}`,
        source: cmd.triggerKind,
        businessScopeJson: cmd.businessScope ?? {},
        validatedInputRef: cmd.validatedInputRef ?? null,
        fingerprintHash: fingerprint,
        state: "REQUESTED",
        correlationId,
      })
      .returning()) as unknown as InvocationRow[];

    await tx.insert(automationInvocationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      invocationId: row.id,
      seq: 1,
      eventType: "invocation.requested",
      payloadJson: { triggerKind: cmd.triggerKind },
    });

    const envelope = makeBusinessEvent({
      eventType: REQUESTED_EVENT_TYPE,
      workspaceId: ctx.workspaceId,
      aggregateType: "automation_invocation",
      aggregateId: row.id.toString(),
      correlationId,
      actor: { kind: "user", id: ctx.userId },
      classification: "internal",
      payload: {
        schema_version: 1,
        invocation_id: row.id.toString(),
        workspace_id: ctx.workspaceId,
        automation_key: defRow.automationKey,
        revision: revision.revisionNo,
        revision_hash: revision.revisionHash,
        trigger_kind: cmd.triggerKind,
        trigger_identity: triggerIdentity,
        correlation_id: correlationId,
        requested_at: new Date().toISOString(),
      },
    });
    await appendOutboxEvent(tx, envelope);

    return mvpItem(toView(row, false), [SOURCE_REF]);
  });
}

export async function getAutomationInvocation(
  params: GetAutomationInvocationParams
): Promise<MvpSuccess<AutomationInvocationView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const wsId = BigInt(ctx.workspaceId);
  const [row] = (await db
    .select()
    .from(automationInvocations)
    .where(and(eq(automationInvocations.id, BigInt(params.invocationId)), eq(automationInvocations.workspaceId, wsId)))
    .limit(1)) as unknown as InvocationRow[];
  if (!row) throw APIError.notFound("automation invocation not found");
  return mvpItem(toView(row, false), [SOURCE_REF]);
}

export async function cancelAutomationInvocation(
  params: CancelAutomationInvocationParams
): Promise<MvpSuccess<AutomationInvocationView>> {
  const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
  const wsId = BigInt(ctx.workspaceId);

  return db.transaction(async (tx) => {
    const [row] = (await tx
      .select()
      .from(automationInvocations)
      .where(and(eq(automationInvocations.id, BigInt(params.invocationId)), eq(automationInvocations.workspaceId, wsId)))
      .limit(1)) as unknown as InvocationRow[];
    if (!row) throw APIError.notFound("automation invocation not found");
    if (row.version !== params.expectedVersion) {
      throw APIError.aborted(`version conflict: expected ${params.expectedVersion}, found ${row.version}`);
    }
    if (["COMPLETED", "FAILED", "CANCELLED"].includes(row.state)) {
      return mvpItem(toView(row, false), [SOURCE_REF]);
    }

    const preDispatch = row.agentRunId == null && ["REQUESTED", "QUEUED"].includes(row.state);
    const nextState = preDispatch ? "CANCELLED" : "CANCEL_REQUESTED";

    const [updated] = (await tx
      .update(automationInvocations)
      .set({ state: nextState, version: row.version + 1, updatedAt: new Date() })
      .where(
        and(
          eq(automationInvocations.id, row.id),
          eq(automationInvocations.workspaceId, wsId),
          eq(automationInvocations.version, params.expectedVersion)
        )
      )
      .returning()) as unknown as InvocationRow[];
    if (!updated) throw APIError.aborted("version conflict during cancel");

    await tx.insert(automationInvocationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      invocationId: row.id,
      seq: row.version + 1,
      eventType: preDispatch ? "invocation.cancelled" : "invocation.cancel_requested",
      payloadJson: {},
    });

    if (!preDispatch) {
      const envelope = makeBusinessEvent({
        eventType: CANCEL_EVENT_TYPE,
        workspaceId: ctx.workspaceId,
        aggregateType: "automation_invocation",
        aggregateId: row.id.toString(),
        correlationId: row.correlationId,
        actor: { kind: "user", id: ctx.userId },
        classification: "internal",
        payload: {
          schema_version: 1,
          invocation_id: row.id.toString(),
          workspace_id: ctx.workspaceId,
          agent_run_ref: row.agentRunId ?? "",
          correlation_id: row.correlationId,
          requested_at: new Date().toISOString(),
        },
      });
      await appendOutboxEvent(tx, envelope);
    }

    return mvpItem(toView(updated, false), [SOURCE_REF]);
  });
}
