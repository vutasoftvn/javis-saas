import { api, Header } from "encore.dev/api";
import {
  storeCasWebhookService,
  processCasInboxEntryService,
} from "../services/cas-webhook.service";

export interface CasWebhookHttpParams {
  casSignature?: Header<"X-Cas-Signature">;
  rawPayload: string;
}

export const postCasWebhook = api(
  { method: "POST", path: "/finance-legal/cas/webhook", expose: true },
  async (params: CasWebhookHttpParams): Promise<{ ok: boolean; inboxId: string; duplicate: boolean }> => {
    const result = await storeCasWebhookService({
      rawPayload: params.rawPayload,
      signatureHeader: params.casSignature,
    });

    if (!result.isDuplicate) {
      // Process asynchronously (or inline in standard synchronous context)
      try {
        await processCasInboxEntryService(BigInt(result.inboxId));
      } catch (_) {
        // Any failure stays in inbox table as FAILED/DLQ
      }
    }

    return { ok: true, inboxId: result.inboxId, duplicate: result.isDuplicate };
  }
);

export interface ReprocessInboxParams {
  id: string;
}

// M1 §4/§5 — reprocess là luồng nội bộ service/admin, KHÔNG public: trước đây
// `expose:true` không auth ⇒ kết hợp payload tự khai workspace ⇒ chèn giao dịch
// giả vào workspace bất kỳ. Đổi `expose:false` (chỉ gọi được service-to-service).
export const postReprocessCasInbox = api(
  { method: "POST", path: "/finance-legal/cas/webhook/reprocess/:id", expose: false },
  async (params: ReprocessInboxParams): Promise<{ success: boolean; transactionId?: string }> => {
    return processCasInboxEntryService(BigInt(params.id));
  }
);
