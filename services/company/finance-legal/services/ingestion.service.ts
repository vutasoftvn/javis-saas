import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createHash } from "node:crypto";

const { ingestionEvents, bankConnections } = schema;

export interface IngestionEventView {
  id: string;
  bankConnectionId: string;
  providerEventId: string;
  receivedAt: string;
  status: "RECEIVED" | "PROCESSING" | "PROCESSED" | "FAILED" | "DLQ";
  errorMsg: string | null;
  processedAt: string | null;
}

export async function recordIngestionEventService(p: {
  bankConnectionId: bigint;
  providerEventId: string;
  rawPayloadRef?: string;
  payloadStr?: string;
}): Promise<{ event: IngestionEventView; isDuplicate: boolean }> {
  // Check connection
  const [conn] = await db
    .select()
    .from(bankConnections)
    .where(eq(bankConnections.id, p.bankConnectionId));
  if (!conn) {
    throw APIError.notFound(`Bank connection '${p.bankConnectionId}' not found`);
  }

  // Check duplicate
  const [existing] = await db
    .select()
    .from(ingestionEvents)
    .where(
      and(
        eq(ingestionEvents.bankConnectionId, p.bankConnectionId),
        eq(ingestionEvents.providerEventId, p.providerEventId)
      )
    );

  if (existing) {
    return {
      event: {
        id: String(existing.id),
        bankConnectionId: String(existing.bankConnectionId),
        providerEventId: existing.providerEventId,
        receivedAt: existing.receivedAt.toISOString(),
        status: existing.status as any,
        errorMsg: existing.errorMsg,
        processedAt: existing.processedAt ? existing.processedAt.toISOString() : null,
      },
      isDuplicate: true,
    };
  }

  const checksum = p.payloadStr
    ? createHash("sha256").update(p.payloadStr).digest("hex")
    : null;

  const newId = generateSnowflake();
  const [created] = await db
    .insert(ingestionEvents)
    .values({
      id: newId,
      bankConnectionId: p.bankConnectionId,
      providerEventId: p.providerEventId,
      rawPayloadRef: p.rawPayloadRef ?? null,
      checksum,
      status: "RECEIVED",
    })
    .returning();

  return {
    event: {
      id: String(created.id),
      bankConnectionId: String(created.bankConnectionId),
      providerEventId: created.providerEventId,
      receivedAt: created.receivedAt.toISOString(),
      status: created.status as any,
      errorMsg: null,
      processedAt: null,
    },
    isDuplicate: false,
  };
}
