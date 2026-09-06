import { api, APIError, ErrCode } from "encore.dev/api";
import { CAS_CONTRACT } from "../services/cas-contract";
import { receiveCasWebhookService } from "../services/cas-webhook.service";
import { reprocessOneCasInboxEventService } from "../services/cas-inbox-worker.service";

// IA09 — trước đây khai báo `rawPayload: string` như 1 field JSON body
// thường (Encore parse request theo shape `{"rawPayload": "..."}`), nghĩa
// là webhook POST THẬT từ Cas.so (body là envelope JSON trực tiếp, ví dụ
// `{"webhookType": "TRANSACTIONS", ...}`) không bao giờ khớp shape này —
// `rawPayload` sẽ luôn undefined/parse lỗi. Dùng api.raw() để nhận đúng raw
// bytes của HTTP POST body thật, cùng pattern đã có ở
// commercial/.../channels/zalo.handler.ts.
const HTTP_STATUS_BY_ERR_CODE: Partial<Record<ErrCode, number>> = {
  [ErrCode.InvalidArgument]: 400,
  [ErrCode.Unauthenticated]: 401,
  [ErrCode.PermissionDenied]: 403,
  [ErrCode.NotFound]: 404,
  [ErrCode.AlreadyExists]: 409,
  [ErrCode.FailedPrecondition]: 400,
  [ErrCode.ResourceExhausted]: 429,
  [ErrCode.Unavailable]: 503,
  [ErrCode.DeadlineExceeded]: 504,
  [ErrCode.Internal]: 500,
};

export const postCasWebhook = api.raw(
  { method: "POST", path: "/finance-legal/cas/webhook", expose: true },
  async (req, resp) => {
    const chunks: Buffer[] = [];
    for await (const chunk of req) {
      chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
    }
    const rawBody = Buffer.concat(chunks).toString("utf8");
    const headers = (req.headers || {}) as Record<string, string | undefined>;
    // Tên header chữ ký CHƯA xác nhận được với tài liệu công khai (trang
    // docs webhook của cas.so trả 404 khi kiểm tra) — dùng CAS_CONTRACT làm
    // NGUỒN DUY NHẤT thay vì 2 tên khác nhau rải rác trong code (trước đây
    // handler đọc "X-Cas-Signature" còn contract khai
    // "x-cas-webhook-secret-key") để ít nhất nhất quán nội bộ.
    const signatureHeader = headers[CAS_CONTRACT.webhook.signatureHeader.toLowerCase()];

    try {
      const result = await receiveCasWebhookService({
        rawPayload: rawBody,
        signatureHeader,
      });
      resp.statusCode = 200;
      resp.setHeader("Content-Type", "application/json");
      resp.end(
        JSON.stringify({
          ok: true,
          inboxId: result.inboxId,
          duplicate: result.isDuplicate,
          quarantined: result.quarantined,
        })
      );
    } catch (err: any) {
      const status =
        err instanceof APIError ? HTTP_STATUS_BY_ERR_CODE[err.code] ?? 400 : 500;
      resp.statusCode = status;
      resp.setHeader("Content-Type", "application/json");
      resp.end(JSON.stringify({ ok: false, error: err?.message ? String(err.message) : "invalid webhook" }));
    }
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
