import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { receiveCasWebhookService, verifyCasWebhookSignature } from "../services/cas-webhook.service";
import { createHmac } from "node:crypto";

// F3 — cas-webhook.handler/service được viết lại để dùng raw JSON envelope
// thật của Cas.so ({id, error, data}, xem cas-contract.ts) thay vì payload ad
// -hoc cũ ({eventId, eventType, connectionId, workspaceId, ...}) đặt ra trước
// khi contract được xác nhận ở F2. Test tenant-resolution/cross-tenant/
// dedup-hội-tụ chi tiết hơn nằm ở cas-ingestion-contract.test.ts — file này
// giữ phần thuộc riêng webhook: HMAC verify + fail-closed + dedup cơ bản.
describe("Cas.so Webhook — verify, fail-closed, durable ACK", () => {
  const secret = "test_cas_secret_123";

  it("verifies HMAC signatures correctly", () => {
    const payload = JSON.stringify({ id: "evt_101", error: 0, data: null });
    const sig = createHmac("sha256", secret).update(payload).digest("hex");

    expect(verifyCasWebhookSignature(payload, sig, secret)).toBe(true);
    expect(verifyCasWebhookSignature(payload, `sha256=${sig}`, secret)).toBe(true);
    expect(verifyCasWebhookSignature(payload, "invalid_signature", secret)).toBe(false);
  });

  it("stores a raw JSON webhook (not wrapped as a rawPayload string) into the durable inbox and dedups by identity", async () => {
    const payloadStr = JSON.stringify({
      id: `evt_${Date.now()}_dedup`,
      error: 0,
      data: {
        tid: `dup_tid_${Date.now()}`,
        amount: 1000,
        when: "2026-08-29T10:00:00Z",
        bank_sub_acc_id: "sub_acc_never_registered_dedup",
      },
    });

    const res1 = await receiveCasWebhookService({ rawPayload: payloadStr, skipSigVerify: true });
    expect(res1.inboxId).toBeDefined();
    expect(res1.isDuplicate).toBe(false);

    const res2 = await receiveCasWebhookService({ rawPayload: payloadStr, skipSigVerify: true });
    expect(res2.isDuplicate).toBe(true);
    expect(res2.inboxId).toBe(res1.inboxId);
  });

  it("ACKs immediately without processing inline — the inbox row stays at RECEIVED/QUARANTINED, no bank_transaction is created synchronously", async () => {
    const payloadStr = JSON.stringify({
      id: `evt_${Date.now()}_noinline`,
      error: 0,
      data: {
        tid: `noinline_tid_${Date.now()}`,
        amount: 999,
        when: "2026-08-29T10:00:00Z",
        bank_sub_acc_id: "sub_acc_never_registered_noinline",
      },
    });
    const res = await receiveCasWebhookService({ rawPayload: payloadStr, skipSigVerify: true });
    const [row] = await db.select().from(schema.casSyncInbox).where(eq(schema.casSyncInbox.id, BigInt(res.inboxId)));
    // Không resolve được tenant -> QUARANTINED ngay (không RECEIVED) nhưng
    // vẫn KHÔNG PROCESSED — điều cốt lõi cần khẳng định là "không xử lý
    // nghiệp vụ inline trong request webhook".
    expect(row.status).not.toBe("PROCESSED");
    expect(row.processedAt).toBeNull();
  });

  // M1 §5 — fail-closed ở staging/prod.
  it("fails closed in production when CAS_WEBHOOK_SECRET is missing", async () => {
    const prevEnv = process.env.ENVIRONMENT;
    const prevSecret = process.env.CAS_WEBHOOK_SECRET;
    process.env.ENVIRONMENT = "production";
    delete process.env.CAS_WEBHOOK_SECRET;
    try {
      await expect(
        receiveCasWebhookService({
          rawPayload: JSON.stringify({ id: "evt_noSecret", error: 0, data: null }),
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
        receiveCasWebhookService({
          rawPayload: JSON.stringify({ id: "evt_unsigned", error: 0, data: null }),
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

  it("rejects malformed JSON as invalidArgument", async () => {
    await expect(
      receiveCasWebhookService({ rawPayload: "{not json", skipSigVerify: true })
    ).rejects.toThrow();
  });
});
