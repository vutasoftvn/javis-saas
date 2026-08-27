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

export async function createDocumentIngestion(input: {
  workspaceId: string;
  createdBy: string;
  originalFilename: string;
  declaredMediaType: string;
  idempotencyKey: string;
}): Promise<DocumentIngestionRecord> {
  // Check if same idempotency key already exists for this workspace+creator
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

  const id = `ing_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
  const now = new Date();

  const [created] = await db
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
    .returning();

  // Audit event for creation
  await db
    .insert(documentIngestionAuditEvents)
    .values({
      ingestionId: id,
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

    // Transition UPLOADING → QUARANTINED → QUEUED atomically
    const [updated] = await tx
      .update(documentIngestions)
      .set({
        originalObjectKey: input.objectKey,
        detectedMediaType: input.detectedMediaType,
        sizeBytes: BigInt(input.sizeBytes),
        sourceSha256: input.sourceSha256,
        state: "QUEUED",
        updatedAt: now,
      })
      .where(eq(documentIngestions.id, input.ingestionId))
      .returning();

    // Audit event: UPLOADING → QUARANTINED → QUEUED (single event for the composite transition)
    await tx
      .insert(documentIngestionAuditEvents)
      .values({
        ingestionId: input.ingestionId,
        actorKind: "system",
        actorId: input.actorId,
        oldState: current.state,
        newState: "QUEUED",
        reason: `completeUpload: detected ${input.detectedMediaType}, size ${input.sizeBytes}, sha256 ${input.sourceSha256}`,
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

    // Verify transition is allowed
    const allowedNextStates = STATE_TRANSITIONS[current.state as DocumentIngestionState];
    if (!allowedNextStates.includes(nextState)) {
      throw APIError.invalidArgument(
        `invalid state transition: ${current.state} → ${nextState}. Allowed: ${allowedNextStates.join(", ")}`
      );
    }

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
