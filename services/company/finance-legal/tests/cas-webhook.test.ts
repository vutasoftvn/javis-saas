import { describe, it, expect, beforeEach } from "vitest";
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
});
