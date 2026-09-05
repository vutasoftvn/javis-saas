import { api, Header } from "encore.dev/api";
import { receiveCasWebhookService } from "../services/cas-webhook.service";
import { reprocessOneCasInboxEventService } from "../services/cas-inbox-worker.service";

export interface CasWebhookHttpParams {
  casSignature?: Header<"X-Cas-Signature">;
  rawPayload: string;
}

// F3 — handler chỉ verify/parse/ghi durable inbox rồi ACK ngay. Xử lý
// nghiệp vụ (normalize + ghi bank_transaction) thuộc worker định kỳ
// (cas-inbox-worker.cron.ts), KHÔNG gọi inline trong request nữa — giữ
// request webhook nhanh và không phụ thuộc kết quả xử lý nghiệp vụ.
export const postCasWebhook = api(
  { method: "POST", path: "/finance-legal/cas/webhook", expose: true },
  async (
    params: CasWebhookHttpParams
  ): Promise<{ ok: boolean; inboxId: string; duplicate: boolean; quarantined: boolean }> => {
    const result = await receiveCasWebhookService({
      rawPayload: params.rawPayload,
      signatureHeader: params.casSignature,
    });

    return {
      ok: true,
      inboxId: result.inboxId,
      duplicate: result.isDuplicate,
      quarantined: result.quarantined,
    };
  }
);

export interface ReprocessInboxParams {
  id: string;
}

// M1 §4/§5 — reprocess là luồng nội bộ service/admin, KHÔNG public: payload
// tự khai workspace không được tin (bug cũ: chèn giao dịch giả vào workspace
// bất kỳ). expose:false — chỉ gọi được service-to-service.
export const postReprocessCasInbox = api(
  { method: "POST", path: "/finance-legal/cas/webhook/reprocess/:id", expose: false },
  async (params: ReprocessInboxParams): Promise<{ claimed: number; processed: number; failed: number; dlq: number }> => {
    return reprocessOneCasInboxEventService(BigInt(params.id));
  }
);
