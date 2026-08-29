import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { isStagingOrProd } from "../../shared/env";
import { ingestBankTransactionService } from "./bank-transaction.service";
import { createHmac } from "node:crypto";

const { casWebhookInbox, bankConnections } = schema;

export interface CasWebhookPayload {
  eventId: string;
  eventType: string; // e.g. "transaction.created" | "balance.updated"
  connectionId: string;
  workspaceId: string;
  data: {
    transactionId?: string;
    postedAt?: string;
    amount?: number | string;
    currency?: string;
    direction?: "IN" | "OUT";
    description?: string;
    counterpartyName?: string;
    counterpartyAccount?: string;
  };
}

export function verifyCasWebhookSignature(
  rawPayload: string,
  signatureHeader: string | undefined,
  secret: string
): boolean {
  if (!signatureHeader || !secret) return false;
  const expected = createHmac("sha256", secret).update(rawPayload).digest("hex");
  return signatureHeader === expected || signatureHeader === `sha256=${expected}`;
}

export async function storeCasWebhookService(p: {
  rawPayload: string;
  signatureHeader?: string;
  skipSigVerify?: boolean;
}): Promise<{ inboxId: string; isDuplicate: boolean }> {
  const webhookSecret = process.env.CAS_WEBHOOK_SECRET;

  // Fail-closed: ở staging/prod thiếu secret là lỗi cấu hình, KHÔNG được chấp nhận
  // webhook unsigned. `skipSigVerify` chỉ dành cho test/dev.
  if (isStagingOrProd()) {
    if (!webhookSecret) {
      throw APIError.internal(
        "CAS_WEBHOOK_SECRET is not configured — refusing to accept unsigned webhooks"
      );
    }
    const isValid = verifyCasWebhookSignature(p.rawPayload, p.signatureHeader, webhookSecret);
    if (!isValid) {
      throw APIError.unauthenticated("Invalid Cas webhook signature");
    }
  } else if (webhookSecret && !p.skipSigVerify) {
    const isValid = verifyCasWebhookSignature(p.rawPayload, p.signatureHeader, webhookSecret);
    if (!isValid) {
      throw APIError.unauthenticated("Invalid Cas webhook signature");
    }
  }

  let parsed: CasWebhookPayload;
  try {
    parsed = JSON.parse(p.rawPayload);
  } catch (err) {
    throw APIError.invalidArgument("Malformed JSON in webhook payload");
  }

  if (!parsed.eventId) {
    throw APIError.invalidArgument("Missing eventId in Cas webhook payload");
  }

  // Deduplication check
  const [existing] = await db
    .select()
    .from(casWebhookInbox)
    .where(eq(casWebhookInbox.providerEventId, parsed.eventId));

  if (existing) {
    return { inboxId: String(existing.id), isDuplicate: true };
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(casWebhookInbox)
    .values({
      id: newId,
      providerEventId: parsed.eventId,
      rawPayload: p.rawPayload,
      signatureHeader: p.signatureHeader ?? null,
      status: "RECEIVED",
    })
    .returning();

  return { inboxId: String(created.id), isDuplicate: false };
}

export async function processCasInboxEntryService(inboxId: bigint): Promise<{ success: boolean; transactionId?: string }> {
  const [entry] = await db
    .select()
    .from(casWebhookInbox)
    .where(eq(casWebhookInbox.id, inboxId));

  if (!entry) {
    throw APIError.notFound(`Inbox entry '${inboxId}' not found`);
  }

  if (entry.status === "PROCESSED") {
    return { success: true };
  }

  await db
    .update(casWebhookInbox)
    .set({ status: "PROCESSING" })
    .where(eq(casWebhookInbox.id, inboxId));

  try {
    const payload: CasWebhookPayload = JSON.parse(entry.rawPayload);

    if (payload.eventType === "transaction.created" && payload.data.transactionId) {
      // Payload tự khai workspaceId/connectionId — KHÔNG tin. Chứng minh bank
      // connection thật sự thuộc workspace được khai trước khi ghi giao dịch.
      if (!payload.connectionId || !payload.workspaceId) {
        throw APIError.invalidArgument("Webhook payload missing connectionId/workspaceId");
      }
      const [connection] = await db
        .select()
        .from(bankConnections)
        .where(eq(bankConnections.id, BigInt(payload.connectionId)));
      if (!connection) {
        throw APIError.notFound(`Bank connection '${payload.connectionId}' not found`);
      }
      if (connection.workspaceId !== BigInt(payload.workspaceId)) {
        // Cross-tenant injection attempt — chặn + đánh dấu SECURITY.
        await db
          .update(casWebhookInbox)
          .set({
            status: "FAILED",
            errorMsg: `SECURITY: connection ${payload.connectionId} belongs to workspace ${connection.workspaceId}, not ${payload.workspaceId}`,
          })
          .where(eq(casWebhookInbox.id, inboxId));
        throw APIError.permissionDenied(
          "Bank connection does not belong to the workspace declared in the payload"
        );
      }

      const txn = await ingestBankTransactionService({
        workspaceId: BigInt(payload.workspaceId),
        bankConnectionId: BigInt(payload.connectionId),
        externalTransactionId: payload.data.transactionId,
        postedAt: payload.data.postedAt || new Date().toISOString(),
        amount: payload.data.amount || 0,
        currency: payload.data.currency || "VND",
        direction: payload.data.direction || "IN",
        description: payload.data.description || "Cas transaction",
        counterpartyName: payload.data.counterpartyName,
        counterpartyAccount: payload.data.counterpartyAccount,
        rawPayload: payload.data,
      });

      await db
        .update(casWebhookInbox)
        .set({ status: "PROCESSED", processedAt: new Date() })
        .where(eq(casWebhookInbox.id, inboxId));

      return { success: true, transactionId: txn.id };
    }

    await db
      .update(casWebhookInbox)
      .set({ status: "PROCESSED", processedAt: new Date() })
      .where(eq(casWebhookInbox.id, inboxId));

    return { success: true };
  } catch (err: any) {
    // Không ghi đè dòng SECURITY chi tiết đã set trước khi throw.
    const [cur] = await db
      .select({ errorMsg: casWebhookInbox.errorMsg })
      .from(casWebhookInbox)
      .where(eq(casWebhookInbox.id, inboxId));
    if (!cur?.errorMsg?.startsWith("SECURITY:")) {
      await db
        .update(casWebhookInbox)
        .set({ status: "FAILED", errorMsg: err.message || String(err) })
        .where(eq(casWebhookInbox.id, inboxId));
    }
    throw err;
  }
}
