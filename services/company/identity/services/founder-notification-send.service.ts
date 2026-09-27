// Task 3 (B2) / ADR-FOUNDER-CHANNEL-001 Decision 4-7, 9 — capability
// `founder.notify.send` (T2-self). Gửi thông báo vào kênh nhận ĐÃ XÁC MINH của
// chính founder sở hữu run. Agent không chọn được người nhận:
//   - Founder sở hữu run = danh tính trong delegation (`ctx.workforceMemberId` +
//     `ctx.membershipRole`), không bao giờ lấy từ payload.
//   - Payload là allowlist chặt `{ content, channelKind? }`; mọi field khác
//     (chat_id, recipient, channelId, founderMemberId, …) -> invalidArgument.
// Tra kênh/gửi tái dùng code B1: `resolveUsableChannelForFounder`,
// `resolveFounderChannelSecret`, `getFounderChannelAdapter`.
import { APIError } from "encore.dev/api";
import log from "encore.dev/log";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  resolveUsableChannelForFounder,
  type FounderNotificationChannelKind,
} from "./founder-notification-channel.service";
import { resolveFounderChannelSecret } from "./founder-channel-secret";
import { getFounderChannelAdapter, type FounderChannelSendResult } from "./telegram-channel-adapter";

const { identityWorkforceMembers } = schema;

/** Giới hạn độ dài nội dung (ký tự Unicode, khớp `maxLength` của input_schema phía Python). */
export const FOUNDER_NOTIFICATION_MAX_CONTENT_LENGTH = 4000;

const ALLOWED_PAYLOAD_KEYS: ReadonlySet<string> = new Set(["content", "channelKind"]);
const SUPPORTED_KINDS: ReadonlySet<string> = new Set<FounderNotificationChannelKind>(["telegram"]);
const FOUNDER_ROLES: ReadonlySet<string> = new Set(["founder", "co-founder"]);
const KIND_DISPLAY_LABEL: Record<FounderNotificationChannelKind, string> = { telegram: "Telegram" };

export interface SendFounderNotificationInput {
  content: string;
  channelKind?: FounderNotificationChannelKind;
}

export interface SendFounderNotificationResult {
  readonly delivered: true;
  readonly channelKind: FounderNotificationChannelKind;
  /** Nhãn founder tự đặt cho kênh, hoặc tên loại kênh. KHÔNG phải chat id. */
  readonly channelLabel: string;
}

/**
 * Kiểm payload theo allowlist. Nhận `unknown` (JSON thô từ request) để chính hàm này là
 * cổng duy nhất quyết định field nào hợp lệ — không dựa vào decoder của Encore (decoder
 * typed API bỏ qua field lạ thay vì từ chối, xem task-3-report).
 */
export function parseFounderNotificationSendPayload(raw: unknown): SendFounderNotificationInput {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    throw APIError.invalidArgument("founder_notify_invalid_payload: body phải là object JSON");
  }
  const record = raw as Record<string, unknown>;
  const unknownKeys = Object.keys(record).filter((key) => !ALLOWED_PAYLOAD_KEYS.has(key));
  if (unknownKeys.length > 0) {
    const shown = unknownKeys
      .slice(0, 5)
      .map((key) => key.slice(0, 64))
      .join(", ");
    throw APIError.invalidArgument(
      `founder_notify_invalid_payload: field không được phép: ${shown} (chỉ nhận content, channelKind; người nhận do server tự xác định)`
    );
  }

  const content = record.content;
  if (typeof content !== "string") {
    throw APIError.invalidArgument("founder_notify_invalid_payload: content phải là chuỗi");
  }
  const trimmed = content.trim();
  if (trimmed.length === 0) {
    throw APIError.invalidArgument("founder_notify_invalid_payload: content không được rỗng");
  }
  // Đếm theo code point (như JSON Schema maxLength) chứ không theo UTF-16 unit.
  if ([...trimmed].length > FOUNDER_NOTIFICATION_MAX_CONTENT_LENGTH) {
    throw APIError.invalidArgument(
      `founder_notify_invalid_payload: content dài quá ${FOUNDER_NOTIFICATION_MAX_CONTENT_LENGTH} ký tự`
    );
  }

  if (!("channelKind" in record)) {
    return { content: trimmed };
  }
  const channelKind = record.channelKind;
  if (typeof channelKind !== "string" || !SUPPORTED_KINDS.has(channelKind)) {
    throw APIError.invalidArgument("founder_notify_invalid_payload: channelKind không được hỗ trợ");
  }
  return { content: trimmed, channelKind: channelKind as FounderNotificationChannelKind };
}

function ownerNotAuthorized(reason: string): APIError {
  return APIError.permissionDenied(`founder_owner_not_authorized: ${reason}`);
}

/**
 * Decision 5: founder sở hữu run phải có role founder/co-founder còn hiệu lực và workforce
 * member HUMAN còn active. Membership active đã được `resolveTenantContext` kiểm; ở đây kiểm
 * lại role + workforce member ngay lúc gửi (hàng rào cuối, kể cả khi lịch nền dùng snapshot).
 */
async function requireNotificationOwner(ctx: TenantContext): Promise<string> {
  const role = (ctx.membershipRole || "").toLowerCase();
  if (!FOUNDER_ROLES.has(role)) {
    throw ownerNotAuthorized("chỉ founder/co-founder mới nhận được thông báo qua kênh riêng");
  }
  if (!ctx.workforceMemberId) {
    throw ownerNotAuthorized("không xác định được workforce member của founder sở hữu run");
  }

  const [member] = await db
    .select({ status: identityWorkforceMembers.status, memberType: identityWorkforceMembers.memberType })
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, BigInt(ctx.workforceMemberId)),
        eq(identityWorkforceMembers.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .limit(1);
  if (!member || member.memberType !== "HUMAN" || member.status !== "active") {
    throw ownerNotAuthorized("workforce member của founder không còn hoạt động");
  }
  return ctx.workforceMemberId;
}

/**
 * Gửi `content` vào kênh đã xác minh của founder sở hữu run. Lỗi (message mở đầu bằng mã
 * máy-đọc-được, cùng convention B1):
 * - `invalid_argument` `founder_notify_invalid_payload:` — payload sai/field lạ.
 * - `permission_denied` `founder_owner_not_authorized:` — không phải founder còn hiệu lực.
 * - `failed_precondition` `founder_channel_unavailable:` / `founder_channel_ambiguous:` — từ B1.
 * - `unavailable` `founder_channel_delivery_failed:` — Telegram lỗi/timeout; thử lại được,
 *   KHÔNG đổi `verified_at` của kênh.
 */
export async function sendFounderNotification(
  ctx: TenantContext,
  input: SendFounderNotificationInput
): Promise<SendFounderNotificationResult> {
  // Chạy lại allowlist kể cả khi gọi trực tiếp (B5/worker): ép kiểu không lách được.
  const payload = parseFounderNotificationSendPayload(input);
  const founderMemberId = await requireNotificationOwner(ctx);

  const channel = await resolveUsableChannelForFounder(ctx.workspaceId, founderMemberId, payload.channelKind);
  const channelKind = channel.kind as FounderNotificationChannelKind;
  // Audit/log (Decision 9): chỉ channel id, kind, độ dài nội dung. Không token, không chat
  // id, không toàn văn, không lý do lỗi thô của Telegram (có thể chứa dữ liệu nhạy cảm).
  const logFields = {
    channelId: channel.id.toString(),
    channelKind,
    contentLength: [...payload.content].length,
  };

  const token = await resolveFounderChannelSecret(channel.secretRef);
  let result: FounderChannelSendResult;
  try {
    result = await getFounderChannelAdapter().sendMessage(channel.chatId, token, payload.content);
  } catch {
    result = { ok: false, reason: "adapter_threw" };
  }
  if (!result.ok) {
    log.warn("founder notification delivery failed", logFields);
    throw APIError.unavailable(
      "founder_channel_delivery_failed: không gửi được tới kênh nhận lúc này, thử lại sau"
    );
  }

  log.info("founder notification delivered", logFields);
  return {
    delivered: true,
    channelKind,
    channelLabel: channel.label?.trim() || KIND_DISPLAY_LABEL[channelKind] || channelKind,
  };
}
