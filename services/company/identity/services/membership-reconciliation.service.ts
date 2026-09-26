import { APIError } from "encore.dev/api";

// Plan 2026-09-25 core-auth Task 4 — thu hồi membership phải chặn local session và
// không để session cũ "sống lại"; bản chiếu membership phải được đối soát lại với
// Core khi quan sát đã cũ.
//
// Company không giữ credential dịch vụ nào để hỏi Core trạng thái membership (Core
// chỉ trả lời theo token của chính người dùng, xem ADR-COSA-DELEGATION-002), nên
// đối soát là có giới hạn và do client khởi động: /identity/me báo membership đã
// quá tuổi quan sát, Flutter chạy lại /identity/sync-from-platform bằng token Core
// của người dùng. Sync chỉ dùng danh sách Core hiện tại (tombstone membership không
// còn trong đó); lỗi mạng giữ nguyên trạng thái, không suy ra "vẫn active".

const DEFAULT_OBSERVATION_MAX_AGE_SECONDS = 12 * 60 * 60;

export function getMembershipObservationMaxAgeSeconds(): number {
  const raw = Number(process.env.COMPANY_MEMBERSHIP_OBSERVATION_MAX_AGE_SECONDS);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_OBSERVATION_MAX_AGE_SECONDS;
}

/**
 * Giá trị ghi khi tombstone 1 membership. `sessionNotBefore` là session epoch: mọi
 * local session có auth_time trước mốc này mất quyền với membership đó, kể cả khi
 * membership được cấp lại sau này (cấp lại không xoá mốc).
 */
export function revocationValues(now: Date): {
  membershipState: "revoked";
  revokedAt: Date;
  sessionNotBefore: Date;
  updatedAt: Date;
} {
  return { membershipState: "revoked", revokedAt: now, sessionNotBefore: now, updatedAt: now };
}

/**
 * true khi local session (auth_time tính bằng giây epoch) được cấp trước lần thu
 * hồi gần nhất của membership. Token cũ không có auth_time bị coi là quá hạn nếu
 * membership từng bị thu hồi.
 */
export function sessionPredatesRevocation(
  authTimeSeconds: number | undefined,
  sessionNotBefore: Date | null | undefined
): boolean {
  if (!sessionNotBefore) return false;
  if (authTimeSeconds === undefined || !Number.isFinite(authTimeSeconds)) return true;
  // auth_time có độ phân giải giây: session cấp cùng giây với lần thu hồi là mơ hồ
  // ⇒ coi là cấp trước (an toàn), người dùng đồng bộ lại để có session mới.
  return authTimeSeconds <= Math.floor(sessionNotBefore.getTime() / 1000);
}

export function assertSessionAfterRevocation(
  authTimeSeconds: number | undefined,
  sessionNotBefore: Date | null | undefined,
  workspaceId: string
): void {
  if (sessionPredatesRevocation(authTimeSeconds, sessionNotBefore)) {
    throw APIError.permissionDenied(
      `local session được cấp trước lần thu hồi membership tại workspace ${workspaceId} — cần đăng nhập lại`
    );
  }
}

export interface MembershipObservation {
  /** Lần gần nhất bản chiếu được xác nhận với Core (sync hoặc event); null nếu chưa từng. */
  observedAt: string | null;
  /** Quá tuổi quan sát ⇒ client nên chạy lại sync với Core. */
  stale: boolean;
}

export function membershipObservation(
  syncedAt: Date | null | undefined,
  nowMs: number = Date.now()
): MembershipObservation {
  if (!syncedAt) return { observedAt: null, stale: true };
  const ageSeconds = (nowMs - syncedAt.getTime()) / 1000;
  return {
    observedAt: syncedAt.toISOString(),
    stale: ageSeconds > getMembershipObservationMaxAgeSeconds(),
  };
}
