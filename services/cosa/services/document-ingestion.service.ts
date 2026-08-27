import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { db, schema } from "../models/db";
import { scheduleTask } from "./control-plane-scheduler.service";

const { documentIngestions, documentIngestionAuditEvents } = schema;

export type DocumentIngestionState = "UPLOADING" | "QUARANTINED" | "QUEUED" | "VALIDATING" | "CONVERTING" | "REVIEW_PENDING" | "PUBLISHED" | "REJECTED" | "FAILED" | "EXPIRED";

export interface DocumentIngestionRecord {
  id: string;
  workspaceId: string;
  createdBy: string;
  originalFilename: string;
  declaredMediaType: string;
  detectedMediaType: string | null;
  sizeBytes: bigint | null;
  sourceSha256: string | null;
  originalObjectKey: string | null;
  state: DocumentIngestionState;
  idempotencyKey: string;
  knowledgeSourceId: string | null;
  converterSpecId: string | null;
  manifestJson: unknown | null;
  failureCode: string | null;
  claimToken: string | null;
  createdAt: Date;
  updatedAt: Date;
}

// Transition table: defines allowed state transitions
// Each key is the current state, value is array of allowed next states
const STATE_TRANSITIONS: Record<DocumentIngestionState, DocumentIngestionState[]> = {
  UPLOADING: ["QUARANTINED"],
  QUARANTINED: ["QUEUED"],
  QUEUED: ["VALIDATING", "FAILED", "EXPIRED"],
  VALIDATING: ["CONVERTING", "FAILED", "EXPIRED"],
  CONVERTING: ["REVIEW_PENDING", "FAILED", "EXPIRED"],
  REVIEW_PENDING: ["PUBLISHED", "REJECTED"],
  PUBLISHED: [],
  REJECTED: [],
  FAILED: [],
  EXPIRED: [],
};

// Validate state transition against the single source of truth (STATE_TRANSITIONS table)
// Ensures both completeUpload and transitionDocumentIngestionForWorker defer to the same rules
function assertValidTransition(from: DocumentIngestionState, to: DocumentIngestionState): void {
  const allowed = STATE_TRANSITIONS[from];
  if (!allowed || !allowed.includes(to)) {
    throw APIError.invalidArgument(
      `invalid state transition: ${from} → ${to}. Allowed: ${allowed?.join(", ") || "none"}`
    );
  }
}

export async function createDocumentIngestion(input: {
  workspaceId: string;
  createdBy: string;
  originalFilename: string;
  declaredMediaType: string;
  idempotencyKey: string;
}): Promise<DocumentIngestionRecord> {
  const id = `ing_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
  const now = new Date();

  // Atomic INSERT with conflict detection: if (workspace_id, created_by, idempotency_key) exists,
  // skip the insert and fetch the existing row. Prevents TOCTOU race on concurrent creates.
  const insertResult = await db
    .insert(documentIngestions)
    .values({
      id,
      workspaceId: input.workspaceId,
      createdBy: input.createdBy,
      originalFilename: input.originalFilename,
      declaredMediaType: input.declaredMediaType,
      state: "UPLOADING",
      idempotencyKey: input.idempotencyKey,
      createdAt: now,
      updatedAt: now,
    })
    .onConflictDoNothing({
      target: [documentIngestions.workspaceId, documentIngestions.createdBy, documentIngestions.idempotencyKey],
    })
    .returning();

  // If insert was skipped (conflict), fetch the existing row
  if (insertResult.length === 0) {
    const existing = await db
      .select()
      .from(documentIngestions)
      .where(
        and(
          eq(documentIngestions.workspaceId, input.workspaceId),
          eq(documentIngestions.createdBy, input.createdBy),
          eq(documentIngestions.idempotencyKey, input.idempotencyKey)
        )
      );
    if (existing.length > 0) {
      return existing[0] as DocumentIngestionRecord;
    }
    throw APIError.internal("idempotent create conflict resolution failed");
  }

  const created = insertResult[0];

  // Audit event for creation
  await db
    .insert(documentIngestionAuditEvents)
    .values({
      ingestionId: created.id,
      actorKind: "system",
      actorId: input.createdBy,
      oldState: null,
      newState: "UPLOADING",
      reason: "Document ingestion created",
    });

  return created as DocumentIngestionRecord;
}

export async function completeUpload(input: {
  ingestionId: string;
  actorId: string;
  detectedMediaType: string;
  sizeBytes: number;
  sourceSha256: string;
  objectKey: string;
}): Promise<DocumentIngestionRecord> {
  return db.transaction(async (tx) => {
    // Fetch current record with lock
    const rows = await tx
      .select()
      .from(documentIngestions)
      .where(eq(documentIngestions.id, input.ingestionId))
      .for("update");

    if (rows.length === 0) {
      throw APIError.notFound("ingestion not found");
    }

    const current = rows[0] as DocumentIngestionRecord;

    // Verify state is UPLOADING
    if (current.state !== "UPLOADING") {
      throw APIError.invalidArgument(`cannot complete upload: ingestion is in state ${current.state}, not UPLOADING`);
    }

    const now = new Date();

    // Step 1: UPLOADING → QUARANTINED (store object details)
    // Validate transition against STATE_TRANSITIONS table (single source of truth)
    assertValidTransition("UPLOADING", "QUARANTINED");

    let intermediate = await tx
      .update(documentIngestions)
      .set({
        originalObjectKey: input.objectKey,
        detectedMediaType: input.detectedMediaType,
        sizeBytes: BigInt(input.sizeBytes),
        sourceSha256: input.sourceSha256,
        state: "QUARANTINED",
        updatedAt: now,
      })
      .where(eq(documentIngestions.id, input.ingestionId))
      .returning();

    // Audit: UPLOADING → QUARANTINED
    await tx
      .insert(documentIngestionAuditEvents)
      .values({
        ingestionId: input.ingestionId,
        actorKind: "system",
        actorId: input.actorId,
        oldState: "UPLOADING",
        newState: "QUARANTINED",
        reason: `File stored: ${input.detectedMediaType}, ${input.sizeBytes} bytes`,
      });

    // Step 2: QUARANTINED → QUEUED (ready for processing)
    // Validate transition against STATE_TRANSITIONS table (single source of truth)
    assertValidTransition("QUARANTINED", "QUEUED");

    const [updated] = await tx
      .update(documentIngestions)
      .set({
        state: "QUEUED",
        updatedAt: now,
      })
      .where(eq(documentIngestions.id, input.ingestionId))
      .returning();

    // Audit: QUARANTINED → QUEUED
    await tx
      .insert(documentIngestionAuditEvents)
      .values({
        ingestionId: input.ingestionId,
        actorKind: "system",
        actorId: input.actorId,
        oldState: "QUARANTINED",
        newState: "QUEUED",
        reason: "Upload complete, queued for validation",
      });

    // Schedule exactly one scheduler task with coalescing key
    await scheduleTask({
      targetSpecId: "cosa.schedule-execution",
      targetSpecKind: "agent",
      coalescingKey: `knowledge-ingestion:${input.ingestionId}`,
      inputPayload: {
        task_type: "knowledge_ingestion",
        ingestion_id: input.ingestionId,
      },
    });

    return updated as DocumentIngestionRecord;
  });
}

export async function transitionDocumentIngestionForWorker(
  ingestionId: string,
  claimToken: string,
  expectedStates: DocumentIngestionState[],
  nextState: DocumentIngestionState,
  patch: Record<string, unknown>
): Promise<DocumentIngestionRecord> {
  return db.transaction(async (tx) => {
    // Fetch with lock
    const rows = await tx
      .select()
      .from(documentIngestions)
      .where(eq(documentIngestions.id, ingestionId))
      .for("update");

    if (rows.length === 0) {
      throw APIError.notFound("ingestion not found");
    }

    const current = rows[0] as DocumentIngestionRecord;

    // Verify current state is in expected states (if provided)
    if (expectedStates.length > 0 && !expectedStates.includes(current.state as DocumentIngestionState)) {
      throw APIError.invalidArgument(
        `cannot transition: ingestion is in state ${current.state}, expected one of [${expectedStates.join(", ")}]`
      );
    }

    // Verify transition is allowed via single source of truth (STATE_TRANSITIONS table)
    assertValidTransition(current.state as DocumentIngestionState, nextState);

    const now = new Date();
    const updateData: any = {
      state: nextState,
      claimToken,
      updatedAt: now,
      ...patch,
    };

    const [updated] = await tx
      .update(documentIngestions)
      .set(updateData)
      .where(eq(documentIngestions.id, ingestionId))
      .returning();

    // Audit event
    await tx
      .insert(documentIngestionAuditEvents)
      .values({
        ingestionId: ingestionId,
        actorKind: "worker",
        actorId: "worker-service",
        oldState: current.state,
        newState: nextState,
        reason: `Transitioned to ${nextState}`,
      });

    return updated as DocumentIngestionRecord;
  });
}

export async function reviewDocumentIngestion(input: {
  ingestionId: string;
  reviewerId: string;
  decision: "PUBLISHED" | "REJECTED";
  reason: string;
}): Promise<DocumentIngestionRecord> {
  return db.transaction(async (tx) => {
    // Fetch with lock
    const rows = await tx
      .select()
      .from(documentIngestions)
      .where(eq(documentIngestions.id, input.ingestionId))
      .for("update");

    if (rows.length === 0) {
      throw APIError.notFound("ingestion not found");
    }

    const current = rows[0] as DocumentIngestionRecord;

    // Verify state is REVIEW_PENDING
    if (current.state !== "REVIEW_PENDING") {
      throw APIError.invalidArgument(
        `cannot review: ingestion is in state ${current.state}, not REVIEW_PENDING`
      );
    }

    const now = new Date();
    const [updated] = await tx
      .update(documentIngestions)
      .set({
        state: input.decision,
        updatedAt: now,
      })
      .where(eq(documentIngestions.id, input.ingestionId))
      .returning();

    // Audit event with reason
    await tx
      .insert(documentIngestionAuditEvents)
      .values({
        ingestionId: input.ingestionId,
        actorKind: "user",
        actorId: input.reviewerId,
        oldState: current.state,
        newState: input.decision,
        reason: `Review decision: ${input.reason}`,
      });

    return updated as DocumentIngestionRecord;
  });
}

export async function getDocumentIngestion(ingestionId: string): Promise<DocumentIngestionRecord | null> {
  const rows = await db
    .select()
    .from(documentIngestions)
    .where(eq(documentIngestions.id, ingestionId));

  if (rows.length === 0) {
    return null;
  }

  return rows[0] as DocumentIngestionRecord;
}

export async function getAuditEventsForIngestion(ingestionId: string) {
  const rows = await db
    .select()
    .from(documentIngestionAuditEvents)
    .where(eq(documentIngestionAuditEvents.ingestionId, ingestionId));

  return rows;
}
