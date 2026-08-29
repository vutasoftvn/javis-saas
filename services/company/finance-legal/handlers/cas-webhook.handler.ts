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

export const postReprocessCasInbox = api(
  { method: "POST", path: "/finance-legal/cas/webhook/reprocess/:id", expose: true },
  async (params: ReprocessInboxParams): Promise<{ success: boolean; transactionId?: string }> => {
    return processCasInboxEntryService(BigInt(params.id));
  }
);
