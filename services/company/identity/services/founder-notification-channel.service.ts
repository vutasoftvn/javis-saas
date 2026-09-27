// Task 2 (B1) / ADR-FOUNDER-CHANNEL-001 — kênh nhận thông báo ngoài của
// founder. Chỉ CRUD + verify/revoke kênh (Decision 1/2/3). KHÔNG gọi sang
// services/cosa, KHÔNG đụng ScheduleExecutionState/blocked_reauth (Decision 8
// và Consequences B1 dành phần đó cho B5). `resolveUsableChannelForFounder`
// export ra để Task 3 (B2, `founder-notification-send.service.ts`) gọi trực
// tiếp — KHÔNG được đặt private hay đổi chữ ký mà không có ADR mới.
import { APIError } from "encore.dev/api";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { mvpItem, mvpList, type MvpSuccess } from "../../shared/contracts/mvp-response";
import { requireFounderCommand } from "./command-authority.service";
import { FOUNDER_CHANNEL_SECRET_NAMESPACE, resolveFounderChannelSecret } from "./founder-channel-secret";
import { getFounderChannelAdapter } from "./telegram-channel-adapter";

const { founderNotificationChannels } = schema;

export type FounderNotificationChannelKind = "telegram";

const SUPPORTED_KINDS: readonly FounderNotificationChannelKind[] = ["telegram"];

// Fix review (Task 2, "Needs fixes" #1) — `secretRef` KHÔNG còn nhận qua
// input. Client gửi secretRef tự chọn cho phép founder B trỏ vào secret của
// kênh founder A rồi verify bằng bot token của A (phá cô lập bí mật). Server
// tự sinh secretRef từ id snowflake vừa tạo, founder không bao giờ chọn được
// giá trị này.
export interface CreateFounderNotificationChannelInput {
  kind: FounderNotificationChannelKind;
  chatId: string;
  label?: string;
}

function isUniqueViolation(err: unknown): boolean {
  // Cùng mẫu `isUniqueViolation` ở slug-reservation.service.ts — dò cả chuỗi
  // `.cause` vì drizzle/pg có thể bọc lỗi qua nhiều lớp.
  let cur: unknown = err;
  for (let depth = 0; depth < 5 && cur; depth++) {
    if (typeof cur === "object" && cur !== null) {
      const obj = cur as { code?: string; message?: string; cause?: unknown };
      if (obj.code === "23505") return true;
      if (typeof obj.message === "string" && obj.message.includes("duplicate key value")) {
        return true;
      }
      cur = obj.cause;
    } else {
      break;
    }
  }
  return false;
}

function parseChannelId(channelId: string): bigint {
  if (!/^\d+$/.test(channelId)) {
    throw APIError.invalidArgument("channelId phải là số nguyên hợp lệ");
  }
  try {
    return BigInt(channelId);
  } catch {
    throw APIError.invalidArgument("channelId phải là số nguyên hợp lệ");
  }
}

/**
 * DTO trả ra ngoài — KHÔNG bao giờ chứa `secretRef` hay `chatId` nguyên vẹn
 * (Decision 1: "GET chỉ trả kênh của chính founder đang gọi, không bao giờ
 * trả secret_ref hay chat id đầy đủ"). `chatIdMasked` chỉ giữ vài ký tự cuối.
 */
export interface FounderNotificationChannelDto {
  readonly id: string;
  readonly kind: FounderNotificationChannelKind;
  readonly label: string | null;
  readonly chatIdMasked: string;
  readonly verified: boolean;
  readonly revoked: boolean;
  readonly createdAt: string;
  readonly verifiedAt: string | null;
  readonly revokedAt: string | null;
}

function maskChatId(chatId: string): string {
  if (chatId.length <= 4) return "***" + chatId;
  return "***" + chatId.slice(-4);
}

function toDto(row: typeof founderNotificationChannels.$inferSelect): FounderNotificationChannelDto {
  return {
    id: row.id.toString(),
    kind: row.kind as FounderNotificationChannelKind,
    label: row.label ?? null,
    chatIdMasked: maskChatId(row.chatId),
    verified: row.verifiedAt !== null,
    revoked: row.revokedAt !== null,
    createdAt: row.createdAt.toISOString(),
    verifiedAt: row.verifiedAt ? row.verifiedAt.toISOString() : null,
    revokedAt: row.revokedAt ? row.revokedAt.toISOString() : null,
  };
}

function requireFounderMemberId(ctx: TenantContext): bigint {
  if (!ctx.workforceMemberId) {
    throw APIError.failedPrecondition("Thiếu workforceMemberId trong ctx — founder phải có workforce member");
  }
  return BigInt(ctx.workforceMemberId);
}

async function loadOwnedChannel(
  ctx: TenantContext,
  channelId: string
): Promise<typeof founderNotificationChannels.$inferSelect> {
  const founderMemberId = requireFounderMemberId(ctx);
  const workspaceId = BigInt(ctx.workspaceId);

  const [row] = await db
    .select()
    .from(founderNotificationChannels)
    .where(
      and(
        eq(founderNotificationChannels.id, parseChannelId(channelId)),
        eq(founderNotificationChannels.workspaceId, workspaceId)
      )
    );

  if (!row) {
    throw APIError.notFound("founder notification channel not found");
  }
  // Founder A không được đụng kênh của founder B — kể cả khi cùng workspace.
  if (row.founderMemberId !== founderMemberId) {
    throw APIError.notFound("founder notification channel not found");
  }
  return row;
}

export async function createFounderNotificationChannel(
  ctx: TenantContext,
  input: CreateFounderNotificationChannelInput
): Promise<MvpSuccess<FounderNotificationChannelDto>> {
  requireFounderCommand(ctx, "create_founder_notification_channel");

  if (!SUPPORTED_KINDS.includes(input.kind)) {
    throw APIError.invalidArgument(`unsupported channel kind: ${input.kind}`);
  }
  if (!input.chatId) {
    throw APIError.invalidArgument("chatId is required");
  }

  const founderMemberId = requireFounderMemberId(ctx);
  const workspaceId = BigInt(ctx.workspaceId);
  const id = generateSnowflake();
  // Fix review #1 — secretRef LUÔN do server sinh từ id snowflake vừa tạo,
  // không bao giờ nhận từ client. Founder không thể trỏ secretRef tới kênh
  // của người khác vì không còn tham số nào cho phép chọn giá trị này.
  const secretRef = `${FOUNDER_CHANNEL_SECRET_NAMESPACE}${input.kind}/${id.toString()}`;

  let row: typeof founderNotificationChannels.$inferSelect;
  try {
    [row] = await db
      .insert(founderNotificationChannels)
      .values({
        id,
        workspaceId,
        founderMemberId,
        kind: input.kind,
        secretRef,
        chatId: input.chatId,
        label: input.label ?? null,
        verifiedAt: null,
        revokedAt: null,
      })
      .returning();
  } catch (err) {
    // Fix review #2 — vi phạm unique index một phần (còn kênh cùng kind chưa
    // thu hồi) trước đây rơi thẳng lỗi Postgres 23505 thô ra ngoài (500).
    if (isUniqueViolation(err)) {
      throw APIError.alreadyExists(
        "founder_channel_exists: đã có kênh cùng loại chưa thu hồi — thu hồi kênh hiện tại trước khi tạo kênh mới"
      );
    }
    throw err;
  }

  return mvpItem(toDto(row), [{ kind: "company_db", ref: "core.founder_notification_channels" }]);
}

export async function verifyFounderNotificationChannel(
  ctx: TenantContext,
  channelId: string
): Promise<MvpSuccess<FounderNotificationChannelDto>> {
  requireFounderCommand(ctx, "verify_founder_notification_channel");

  const row = await loadOwnedChannel(ctx, channelId);

  // Fix review #3 — kênh đã thu hồi không verify lại được im lặng.
  if (row.revokedAt !== null) {
    throw APIError.failedPrecondition(
      "founder_channel_revoked: kênh đã thu hồi, không thể xác minh — tạo kênh mới"
    );
  }

  const secret = await resolveFounderChannelSecret(row.secretRef);
  const adapter = getFounderChannelAdapter();
  const result = await adapter.sendVerificationProbe(row.chatId, secret, row.label ?? undefined);

  if (!result.ok) {
    throw APIError.failedPrecondition(
      `founder_channel_verification_failed: không xác minh được kênh (${result.reason})`
    );
  }

  // isNull(revokedAt) trong WHERE để tránh race: nếu kênh bị revoke ngay giữa
  // lúc gọi adapter và lúc UPDATE này, verify không được "thắng" thầm lặng.
  const [updated] = await db
    .update(founderNotificationChannels)
    .set({ verifiedAt: new Date() })
    .where(and(eq(founderNotificationChannels.id, row.id), isNull(founderNotificationChannels.revokedAt)))
    .returning();

  if (!updated) {
    throw APIError.failedPrecondition(
      "founder_channel_revoked: kênh đã thu hồi, không thể xác minh — tạo kênh mới"
    );
  }

  return mvpItem(toDto(updated), [{ kind: "company_db", ref: "core.founder_notification_channels" }]);
}

export async function revokeFounderNotificationChannel(
  ctx: TenantContext,
  channelId: string
): Promise<MvpSuccess<FounderNotificationChannelDto>> {
  requireFounderCommand(ctx, "revoke_founder_notification_channel");

  const row = await loadOwnedChannel(ctx, channelId);

  // Fix review #3 — kênh đã thu hồi rồi thì revoke lại là no-op báo lỗi rõ,
  // không âm thầm trả "thành công" lần hai.
  if (row.revokedAt !== null) {
    throw APIError.failedPrecondition("founder_channel_revoked: kênh đã thu hồi trước đó");
  }

  const [updated] = await db
    .update(founderNotificationChannels)
    .set({ revokedAt: new Date() })
    .where(and(eq(founderNotificationChannels.id, row.id), isNull(founderNotificationChannels.revokedAt)))
    .returning();

  if (!updated) {
    throw APIError.failedPrecondition("founder_channel_revoked: kênh đã thu hồi trước đó");
  }

  // Decision 8 — chỉ set revoked_at. KHÔNG gọi sang services/cosa, KHÔNG ghi
  // ScheduleExecutionState (B5 làm việc đó).
  return mvpItem(toDto(updated), [{ kind: "company_db", ref: "core.founder_notification_channels" }]);
}

export async function listFounderNotificationChannels(
  ctx: TenantContext
): Promise<MvpSuccess<readonly FounderNotificationChannelDto[]>> {
  requireFounderCommand(ctx, "list_founder_notification_channels");

  const founderMemberId = requireFounderMemberId(ctx);
  const workspaceId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(founderNotificationChannels)
    .where(
      and(
        eq(founderNotificationChannels.workspaceId, workspaceId),
        eq(founderNotificationChannels.founderMemberId, founderMemberId)
      )
    );

  return mvpList(rows.map(toDto), [{ kind: "company_db", ref: "core.founder_notification_channels" }]);
}

/**
 * Tra kênh dùng được (verifiedAt IS NOT NULL AND revokedAt IS NULL) của một
 * founder. Dùng ở B2 (`founder.notify.send`) và B5 (preflight lịch) — gọi
 * TRỰC TIẾP hàm này (không qua HTTP nội bộ). KHÔNG guard bằng
 * `requireFounderCommand` vì hàm này được gọi server-side (từ endpoint nội
 * bộ hoặc worker), không phải bởi request của founder.
 *
 * - Có `kind`: trả đúng kênh khớp kind đó, hoặc `founder_channel_unavailable`.
 * - Không có `kind`: đúng 1 kênh dùng được -> trả nó; >1 -> throw
 *   `failedPrecondition` mã `founder_channel_ambiguous`; 0 -> throw
 *   `failedPrecondition` mã `founder_channel_unavailable`.
 */
export async function resolveUsableChannelForFounder(
  workspaceId: string,
  founderMemberId: string,
  kind?: FounderNotificationChannelKind
): Promise<typeof founderNotificationChannels.$inferSelect> {
  const conditions = [
    eq(founderNotificationChannels.workspaceId, BigInt(workspaceId)),
    eq(founderNotificationChannels.founderMemberId, BigInt(founderMemberId)),
    isNull(founderNotificationChannels.revokedAt),
  ];
  if (kind) {
    conditions.push(eq(founderNotificationChannels.kind, kind));
  }

  const rows = await db
    .select()
    .from(founderNotificationChannels)
    .where(and(...conditions));

  const usable = rows.filter((r) => r.verifiedAt !== null);

  if (usable.length === 0) {
    throw APIError.failedPrecondition(
      "founder_channel_unavailable: founder chưa có kênh nhận thông báo đã xác minh"
    );
  }
  if (!kind && usable.length > 1) {
    throw APIError.failedPrecondition(
      "founder_channel_ambiguous: founder có nhiều kênh dùng được, cần chỉ rõ channel_kind"
    );
  }
  return usable[0];
}
