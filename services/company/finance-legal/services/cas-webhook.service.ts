// F3 — webhook Cas.so là 1 trong 2 "producer" của pipeline ingestion hợp
// nhất: verify raw bytes -> parse -> resolve tenant PHÍA SERVER (không tin
// field tự khai trong payload) -> ghi durable vào cas_sync_inbox -> ACK
// ngay. Xử lý nghiệp vụ (normalize + ghi bank_transaction) hoàn toàn thuộc
// worker (cas-inbox-worker.service.ts qua cas-inbox-worker.cron.ts), KHÔNG
// còn gọi inline trong request handler như thiết kế cũ trước F3.
import { APIError } from "encore.dev/api";
import { createHmac } from "node:crypto";
import { isStagingOrProd } from "../../shared/env";
import { CAS_CONTRACT, type CasWebhookEnvelope } from "./cas-contract";
import { computeCasEventIdentity } from "./cas-normalizer";
import { enqueueCasInboxEvent } from "./ingestion.service";
import { resolveBankConnectionForCasAccount } from "./cas-sync.service";

export function verifyCasWebhookSignature(
  rawPayload: string,
  signatureHeader: string | undefined,
  secret: string
): boolean {
  if (!signatureHeader || !secret) return false;
  const expected = createHmac("sha256", secret).update(rawPayload).digest("hex");
  return signatureHeader === expected || signatureHeader === `sha256=${expected}`;
}

export interface ReceiveCasWebhookResult {
  inboxId: string;
  isDuplicate: boolean;
  quarantined: boolean;
}

export async function receiveCasWebhookService(p: {
  rawPayload: string;
  signatureHeader?: string;
  skipSigVerify?: boolean;
  environment?: string;
}): Promise<ReceiveCasWebhookResult> {
  const webhookSecret = process.env.CAS_WEBHOOK_SECRET;

  // Fail-closed: ở staging/prod thiếu secret là lỗi cấu hình, KHÔNG được
  // chấp nhận webhook unsigned. `skipSigVerify` chỉ dành cho test/dev.
  if (isStagingOrProd()) {
    if (!webhookSecret) {
      throw APIError.internal(
        "CAS_WEBHOOK_SECRET is not configured — refusing to accept unsigned webhooks"
      );
    }
    if (!verifyCasWebhookSignature(p.rawPayload, p.signatureHeader, webhookSecret)) {
      throw APIError.unauthenticated("Invalid Cas webhook signature");
    }
  } else if (webhookSecret && !p.skipSigVerify) {
    if (!verifyCasWebhookSignature(p.rawPayload, p.signatureHeader, webhookSecret)) {
      throw APIError.unauthenticated("Invalid Cas webhook signature");
    }
  }

  let envelope: CasWebhookEnvelope;
  try {
    envelope = JSON.parse(p.rawPayload);
  } catch (err) {
    throw APIError.invalidArgument("Malformed JSON in Cas webhook payload");
  }

  const environment = p.environment ?? "sandbox";

  // error != 0 hoặc data null: không phải sự kiện giao dịch (vd. grant.revoked/
  // grant.expired theo CAS_CONTRACT.webhook.eventTypes). F3 chỉ ingest giao
  // dịch ngân hàng — ghi nhận để có audit trail (durable, không mất sự kiện)
  // nhưng đánh dấu IGNORED ngay, không đưa qua normalizer/worker retry.
  if (envelope.error !== 0 || !envelope.data) {
    const identity = computeCasEventIdentity({
      bankConnectionId: null,
      bankSubAccId: null,
      externalTransactionId: envelope.id || "unknown",
      eventKind: "not_a_transaction",
      contractVersion: CAS_CONTRACT.contractVersion,
    });
    const enq = await enqueueCasInboxEvent({
      bankConnectionId: null,
      provider: "cas",
      environment,
      source: "webhook",
      eventIdentity: identity,
      rawPayload: envelope,
      initialStatus: "IGNORED",
    });
    return { inboxId: enq.id, isDuplicate: enq.isDuplicate, quarantined: false };
  }

  const raw = envelope.data;
  const bankSubAccId = typeof raw.bank_sub_acc_id === "string" ? raw.bank_sub_acc_id : null;

  // Resolve tenant PHÍA SERVER qua grant/account mapping đã lưu — payload
  // Cas.so không mang workspaceId của chúng ta nên không có gì để "tin" ở
  // đây; chỉ tra bảng bank_connections theo bank_sub_acc_id + environment.
  const resolved = bankSubAccId
    ? await resolveBankConnectionForCasAccount({ bankSubAccId, environment })
    : null;

  const externalTransactionId =
    typeof raw.tid === "string" && raw.tid.trim() ? raw.tid : raw.id !== undefined ? String(raw.id) : "unknown";

  const identity = computeCasEventIdentity({
    bankConnectionId: resolved?.id ?? null,
    bankSubAccId,
    externalTransactionId,
    eventKind: "transaction",
    contractVersion: CAS_CONTRACT.contractVersion,
  });

  const enq = await enqueueCasInboxEvent({
    bankConnectionId: resolved ? BigInt(resolved.id) : null,
    provider: "cas",
    environment,
    source: "webhook",
    eventIdentity: identity,
    rawPayload: raw,
    // Không resolve được tenant (unknown grant/account, hoặc connection đã
    // REVOKED) -> quarantine, không tự gán nhầm workspace nào.
    initialStatus: resolved ? undefined : "QUARANTINED",
  });

  return { inboxId: enq.id, isDuplicate: enq.isDuplicate, quarantined: !resolved };
}
