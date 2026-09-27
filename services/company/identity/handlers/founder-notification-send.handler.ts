// Task 3 (B2) / ADR-FOUNDER-CHANNEL-001 Decision 4 — endpoint của capability
// `founder.notify.send`.
//
// `expose: true` (không phải expose:false như bản ADR đầu): apps/cosa (Python) gọi company
// qua HTTP (`CompanyServiceClient`), không gọi được endpoint nội bộ của Encore. Cổng quyền
// là delegation của agent mang đúng capability `founder.notify.send`
// (`requireWorkspaceAccess(..., { agentCapabilities: [AGENT_CAP.FOUNDER_NOTIFY_SEND] })`).
//
// Dùng `api.raw` thay vì typed `api()`: decoder typed API của Encore BỎ QUA field lạ trong
// body (không trả lỗi, handler không thấy field đó), nên không thể từ chối `chat_id` /
// `recipient` bằng `invalidArgument` như ADR yêu cầu. Raw handler tự đọc JSON và đưa nguyên
// object cho allowlist ở service (`parseFounderNotificationSendPayload`).
//
// Lỗi trả đúng khuôn lỗi của Encore `{ code, message, details }` + HTTP status tương ứng,
// để `CompanyServiceClient` (đọc `message`) và client khác xử lý như mọi endpoint company.
import type { IncomingMessage, ServerResponse } from "node:http";
import { api, APIError, ErrCode } from "encore.dev/api";
import log from "encore.dev/log";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import {
  sendFounderNotification,
  type SendFounderNotificationInput,
} from "../services/founder-notification-send.service";

// Nội dung tối đa 4000 ký tự (≤ 16 KB UTF-8) + khung JSON; quá mức này là payload bất thường.
const MAX_BODY_BYTES = 32 * 1024;

const HTTP_STATUS_BY_ERR_CODE: Record<ErrCode, number> = {
  [ErrCode.OK]: 200,
  [ErrCode.Canceled]: 499,
  [ErrCode.Unknown]: 500,
  [ErrCode.InvalidArgument]: 400,
  [ErrCode.DeadlineExceeded]: 504,
  [ErrCode.NotFound]: 404,
  [ErrCode.AlreadyExists]: 409,
  [ErrCode.PermissionDenied]: 403,
  [ErrCode.ResourceExhausted]: 429,
  [ErrCode.FailedPrecondition]: 400,
  [ErrCode.Aborted]: 409,
  [ErrCode.OutOfRange]: 400,
  [ErrCode.Unimplemented]: 501,
  [ErrCode.Internal]: 500,
  [ErrCode.Unavailable]: 503,
  [ErrCode.DataLoss]: 500,
  [ErrCode.Unauthenticated]: 401,
};

function singleHeader(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value.length === 1 ? value[0] : undefined;
  return value;
}

async function readJsonBody(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buf = typeof chunk === "string" ? Buffer.from(chunk) : (chunk as Buffer);
    size += buf.length;
    if (size > MAX_BODY_BYTES) {
      throw APIError.invalidArgument("founder_notify_invalid_payload: body quá lớn");
    }
    chunks.push(buf);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw APIError.invalidArgument("founder_notify_invalid_payload: body không phải JSON hợp lệ");
  }
}

function writeJson(resp: ServerResponse, status: number, body: unknown): void {
  resp.statusCode = status;
  resp.setHeader("Content-Type", "application/json");
  resp.end(JSON.stringify(body));
}

export const sendFounderNotificationApi = api.raw(
  { expose: true, method: "POST", path: "/identity/founder-notifications/send" },
  async (req, resp) => {
    try {
      // Xác thực trước khi đọc body: caller không có quyền không nhận được phản hồi validate.
      const ctx = await requireWorkspaceAccess(
        singleHeader(req.headers["authorization"]),
        singleHeader(req.headers["x-workspace-id"]) ?? "",
        { agentCapabilities: [AGENT_CAP.FOUNDER_NOTIFY_SEND] }
      );
      const payload = await readJsonBody(req);
      // Service chạy allowlist trên object thô — ép kiểu ở đây không bỏ qua bước kiểm nào.
      const result = await sendFounderNotification(ctx, payload as SendFounderNotificationInput);
      writeJson(resp, 200, result);
    } catch (err) {
      if (err instanceof APIError) {
        writeJson(resp, HTTP_STATUS_BY_ERR_CODE[err.code] ?? 500, {
          code: err.code,
          message: err.message,
          details: null,
        });
        return;
      }
      log.error(err, "founder notification send failed unexpectedly");
      writeJson(resp, 500, { code: ErrCode.Internal, message: "internal error", details: null });
    }
  }
);
