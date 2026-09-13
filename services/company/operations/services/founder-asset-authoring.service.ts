import { eq, and, desc, sql } from "drizzle-orm";
import { db } from "../models/db";
import { founderAssetEvents } from "../../shared/db/schema/operations";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { makeBusinessEvent, type BusinessEventEnvelope } from "../../shared/events/envelope";

export type AssetKind = "AGENT" | "SKILL" | "WORKFLOW";
export type AssetOperation = "CREATE" | "CLONE" | "EDIT_DRAFT" | "EVALUATE" | "PUBLISH" | "RETIRE";

export interface AssetRef {
  assetId: string;
  version?: string;
  definitionHash?: string;
}

export interface FounderAssetCommandInput {
  projectId?: string;
  assetKind: AssetKind;
  operation: AssetOperation;
  assetRef: AssetRef;
  expectedVersion?: number;
  idempotencyKey: string;
  reason: string;
  metadata?: Record<string, any>;
}

export interface FounderAssetCommandResult {
  commandId: string;
  workspaceId: string;
  projectId?: string;
  assetKind: AssetKind;
  operation: AssetOperation;
  status: "PENDING" | "SUCCESS" | "FAILED";
  idempotencyKey: string;
}

export interface AssetStatusCallbackPayload {
  commandId: string;
  workspaceId: string;
  projectId?: string;
  assetKind: AssetKind;
  operation: AssetOperation;
  status: "SUCCESS" | "FAILED" | "REJECTED";
  assetRef?: AssetRef;
  evaluationSummary?: Record<string, any>;
  safeReasonCode?: string;
}

function assertHumanFounder(context: TenantContext): void {
  if (context.isAiAgent) {
    throw new Error("Only a HUMAN founder can perform asset authoring operations");
  }
  if (context.membershipRole !== "founder") {
    throw new Error("Forbidden: requires founder membership role");
  }
}

export async function commandFounderAsset(
  context: TenantContext,
  input: FounderAssetCommandInput
): Promise<FounderAssetCommandResult> {
  assertHumanFounder(context);

  const wsIdBigInt = BigInt(context.workspaceId);

  // 1. Idempotency check in existing founder_asset_events
  const existingRows = await db
    .select()
    .from(founderAssetEvents)
    .where(eq(founderAssetEvents.workspaceId, wsIdBigInt));

  const existing = existingRows.find(
    (r) => (r.metadata as any)?.idempotencyKey === input.idempotencyKey
  );

  if (existing) {
    const meta = (existing.metadata as any) || {};
    return {
      commandId: existing.id.toString(),
      workspaceId: context.workspaceId,
      projectId: existing.projectId?.toString(),
      assetKind: existing.targetKind as AssetKind,
      operation: existing.command as AssetOperation,
      status: meta.status || "PENDING",
      idempotencyKey: input.idempotencyKey,
    };
  }

  // 2. Generate command ID and build signed outbox event
  const commandId = generateSnowflake().toString();
  const wsIdStr = context.workspaceId.toString();
  const projIdStr = input.projectId ? input.projectId.toString() : null;

  const envelope = makeBusinessEvent({
    eventType: "founder.asset.commanded.v1",
    workspaceId: wsIdStr,
    projectId: projIdStr || undefined,
    aggregateType: "founder_asset",
    aggregateId: commandId,
    correlationId: context.correlationId || commandId,
    actor: {
      kind: "user",
      id: context.userId.toString(),
    },
    classification: "internal",
    payload: {
      commandId,
      workspaceId: wsIdStr,
      projectId: projIdStr,
      assetKind: input.assetKind,
      operation: input.operation,
      assetRef: input.assetRef,
      expectedVersion: input.expectedVersion ?? 1,
      idempotencyKey: input.idempotencyKey,
      reason: input.reason,
      metadata: input.metadata || {},
    },
  });

  // 3. Atomically persist command event and outbox row
  await db.transaction(async (tx) => {
    await tx.insert(founderAssetEvents).values({
      id: BigInt(commandId),
      workspaceId: wsIdBigInt,
      projectId: input.projectId ? BigInt(input.projectId) : null,
      actorId: BigInt(context.userId),
      command: input.operation,
      targetKind: input.assetKind,
      targetRef: input.assetRef,
      beforeHash: input.assetRef.definitionHash,
      reason: input.reason,
      correlationId: context.correlationId || commandId,
      metadata: {
        idempotencyKey: input.idempotencyKey,
        status: "PENDING",
        expectedVersion: input.expectedVersion ?? 1,
        ...(input.metadata || {}),
      },
    });

    await appendOutboxEvent(tx, envelope);
  });

  return {
    commandId,
    workspaceId: context.workspaceId,
    projectId: input.projectId,
    assetKind: input.assetKind,
    operation: input.operation,
    status: "PENDING",
    idempotencyKey: input.idempotencyKey,
  };
}

export async function requestAssetClone(
  context: TenantContext,
  input: Omit<FounderAssetCommandInput, "operation"> & { operation?: "CLONE" }
): Promise<FounderAssetCommandResult> {
  return commandFounderAsset(context, { ...input, operation: "CLONE" });
}

export async function requestAssetCreate(
  context: TenantContext,
  input: Omit<FounderAssetCommandInput, "operation"> & { operation?: "CREATE" }
): Promise<FounderAssetCommandResult> {
  return commandFounderAsset(context, { ...input, operation: "CREATE" });
}

export async function requestAssetEditDraft(
  context: TenantContext,
  input: Omit<FounderAssetCommandInput, "operation"> & { operation?: "EDIT_DRAFT" }
): Promise<FounderAssetCommandResult> {
  return commandFounderAsset(context, { ...input, operation: "EDIT_DRAFT" });
}

export async function requestAssetEvaluate(
  context: TenantContext,
  input: Omit<FounderAssetCommandInput, "operation"> & { operation?: "EVALUATE" }
): Promise<FounderAssetCommandResult> {
  return commandFounderAsset(context, { ...input, operation: "EVALUATE" });
}

export async function requestAssetPublish(
  context: TenantContext,
  input: Omit<FounderAssetCommandInput, "operation"> & { operation?: "PUBLISH" }
): Promise<FounderAssetCommandResult> {
  return commandFounderAsset(context, { ...input, operation: "PUBLISH" });
}

export async function handleAssetStatusCallback(
  payload: AssetStatusCallbackPayload
): Promise<void> {
  const wsIdBigInt = BigInt(payload.workspaceId);
  const cmdIdBigInt = BigInt(payload.commandId);

  const existing = await db
    .select()
    .from(founderAssetEvents)
    .where(
      and(
        eq(founderAssetEvents.id, cmdIdBigInt),
        eq(founderAssetEvents.workspaceId, wsIdBigInt)
      )
    );

  if (!existing.length) {
    return;
  }

  const current = existing[0];
  const currentMeta = (current.metadata as any) || {};

  const updatedMeta = {
    ...currentMeta,
    status: payload.status,
    safeReasonCode: payload.safeReasonCode,
    evaluationSummary: payload.evaluationSummary,
    updatedAssetRef: payload.assetRef,
    resolvedAt: new Date().toISOString(),
  };

  await db
    .update(founderAssetEvents)
    .set({
      afterHash: payload.assetRef?.definitionHash || current.afterHash,
      metadata: updatedMeta,
    })
    .where(
      and(
        eq(founderAssetEvents.id, cmdIdBigInt),
        eq(founderAssetEvents.workspaceId, wsIdBigInt)
      )
    );
}

export async function getFounderAssetEvents(
  workspaceId: string,
  commandId?: string
): Promise<any[]> {
  const wsIdBigInt = BigInt(workspaceId);
  if (commandId) {
    const cmdIdBigInt = BigInt(commandId);
    return db
      .select()
      .from(founderAssetEvents)
      .where(
        and(
          eq(founderAssetEvents.workspaceId, wsIdBigInt),
          eq(founderAssetEvents.id, cmdIdBigInt)
        )
      )
      .orderBy(desc(founderAssetEvents.occurredAt));
  }
  return db
    .select()
    .from(founderAssetEvents)
    .where(eq(founderAssetEvents.workspaceId, wsIdBigInt))
    .orderBy(desc(founderAssetEvents.occurredAt));
}
