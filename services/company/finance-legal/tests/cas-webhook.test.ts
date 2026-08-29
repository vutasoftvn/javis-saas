import { describe, it, expect, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  storeCasWebhookService,
  processCasInboxEntryService,
  verifyCasWebhookSignature,
} from "../services/cas-webhook.service";
import { createBankConnectionService } from "../services/bank-connection.service";
import { listBankTransactionsService } from "../services/bank-transaction.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createHmac } from "node:crypto";

describe("Cas.so Webhook Inbox & Ingestion", () => {
  const wsId = generateSnowflake();
  const secret = "test_cas_secret_123";

  it("verifies HMAC signatures correctly", () => {
    const payload = JSON.stringify({ eventId: "evt_101", eventType: "test" });
    const sig = createHmac("sha256", secret).update(payload).digest("hex");

    expect(verifyCasWebhookSignature(payload, sig, secret)).toBe(true);
    expect(verifyCasWebhookSignature(payload, `sha256=${sig}`, secret)).toBe(true);
    expect(verifyCasWebhookSignature(payload, "invalid_signature", secret)).toBe(false);
  });

  it("stores webhook payload in inbox and prevents duplicates", async () => {
    const payloadStr = JSON.stringify({
      eventId: `evt_${Date.now()}_dedup`,
      eventType: "ping",
      connectionId: "1",
      workspaceId: String(wsId),
      data: {},
    });

    const res1 = await storeCasWebhookService({
      rawPayload: payloadStr,
      skipSigVerify: true,
    });
    expect(res1.inboxId).toBeDefined();
    expect(res1.isDuplicate).toBe(false);

    // Second call with same eventId
    const res2 = await storeCasWebhookService({
      rawPayload: payloadStr,
      skipSigVerify: true,
    });
    expect(res2.isDuplicate).toBe(true);
    expect(res2.inboxId).toBe(res1.inboxId);
  });

  it("processes transaction.created webhook into bank_transactions", async () => {
    const conn = await createBankConnectionService({
      workspaceId: wsId,
      provider: "cas",
      secretRef: "secret://cosa-connectors/cas/ws_webhook_test",
    });

    const extTxnId = `cas_txn_${Date.now()}`;
    const payloadStr = JSON.stringify({
      eventId: `evt_${Date.now()}_txn`,
      eventType: "transaction.created",
      connectionId: conn.id,
      workspaceId: String(wsId),
      data: {
        transactionId: extTxnId,
        postedAt: "2026-08-29T11:00:00Z",
        amount: "15000000",
        currency: "VND",
        direction: "IN",
        description: "Khach hang chuyen khoan tien coc du an",
        counterpartyName: "Cong ty XYZ",
      },
    });

    const storeRes = await storeCasWebhookService({
      rawPayload: payloadStr,
      skipSigVerify: true,
    });
    expect(storeRes.isDuplicate).toBe(false);

    const procRes = await processCasInboxEntryService(BigInt(storeRes.inboxId));
    expect(procRes.success).toBe(true);
    expect(procRes.transactionId).toBeDefined();

    // Verify transaction exists in bank_transactions
    const txns = await listBankTransactionsService(wsId);
    const found = txns.find((t) => t.externalTransactionId === extTxnId);
    expect(found).toBeDefined();
    expect(parseFloat(found!.amount)).toBe(15000000);
    expect(found?.direction).toBe("IN");
  });

  // M1 §5 — payload tự khai workspace không được tin.
  it("rejects a webhook whose connectionId belongs to another workspace", async () => {
    const victimWs = generateSnowflake();
    const conn = await createBankConnectionService({
      workspaceId: victimWs,
      provider: "cas",
      secretRef: "secret://cosa-connectors/cas/victim",
    });

    // Kẻ tấn công khai workspaceId của mình nhưng dùng connectionId của nạn nhân.
    const attackerWs = generateSnowflake();
    const payloadStr = JSON.stringify({
      eventId: `evt_${Date.now()}_xtenant`,
      eventType: "transaction.created",
      connectionId: conn.id,
      workspaceId: String(attackerWs),
      data: {
        transactionId: `fake_${Date.now()}`,
        amount: "99999999",
        direction: "IN",
        description: "injected",
      },
    });

    const storeRes = await storeCasWebhookService({ rawPayload: payloadStr, skipSigVerify: true });
    await expect(
      processCasInboxEntryService(BigInt(storeRes.inboxId))
    ).rejects.toThrow(/does not belong to the workspace/i);

    // Không có giao dịch nào được ghi cho workspace kẻ tấn công.
    const txns = await listBankTransactionsService(attackerWs);
    expect(txns.length).toBe(0);

    // Inbox entry đánh dấu SECURITY.
    const [entry] = await db
      .select()
      .from(schema.casWebhookInbox)
      .where(eq(schema.casWebhookInbox.id, BigInt(storeRes.inboxId)));
    expect(entry.status).toBe("FAILED");
    expect(entry.errorMsg?.startsWith("SECURITY:")).toBe(true);
  });

  // M1 §5 — fail-closed ở staging/prod.
  it("fails closed in production when CAS_WEBHOOK_SECRET is missing", async () => {
    const prevEnv = process.env.ENVIRONMENT;
    const prevSecret = process.env.CAS_WEBHOOK_SECRET;
    process.env.ENVIRONMENT = "production";
    delete process.env.CAS_WEBHOOK_SECRET;
    try {
      await expect(
        storeCasWebhookService({
          rawPayload: JSON.stringify({ eventId: "evt_noSecret", eventType: "ping" }),
        })
      ).rejects.toThrow(/not configured/i);
    } finally {
      if (prevEnv === undefined) delete process.env.ENVIRONMENT;
      else process.env.ENVIRONMENT = prevEnv;
      if (prevSecret === undefined) delete process.env.CAS_WEBHOOK_SECRET;
      else process.env.CAS_WEBHOOK_SECRET = prevSecret;
    }
  });

  it("rejects an unsigned webhook in production even when a secret is configured", async () => {
    const prevEnv = process.env.ENVIRONMENT;
    const prevSecret = process.env.CAS_WEBHOOK_SECRET;
    process.env.ENVIRONMENT = "production";
    process.env.CAS_WEBHOOK_SECRET = secret;
    try {
      await expect(
        storeCasWebhookService({
          rawPayload: JSON.stringify({ eventId: "evt_unsigned", eventType: "ping" }),
          // không truyền signatureHeader, không skipSigVerify
        })
      ).rejects.toThrow(/signature/i);
    } finally {
      if (prevEnv === undefined) delete process.env.ENVIRONMENT;
      else process.env.ENVIRONMENT = prevEnv;
      if (prevSecret === undefined) delete process.env.CAS_WEBHOOK_SECRET;
      else process.env.CAS_WEBHOOK_SECRET = prevSecret;
    }
  });
});
