// M5 §3 — Runtime Router (decision core).
//
// Router resolve theo `workspace_id` + membership + `runtime_mode` + node presence
// + execution lease + sync freshness. Đây là HÀM QUYẾT ĐỊNH thuần (nhận input đã
// resolve): việc lấy runtime_mode (authoritative ở services/company), presence
// (runtime-node-registry), lease (control-plane-lease) là adapter mỏng bên ngoài.
//
// Guardrail 7 (audit §5.3): `REMOTE_ACCESS` + local offline ⇒ trả OFFLINE,
// TUYỆT ĐỐI KHÔNG thử cloud. Chỉ `CLOUD_CONTINUITY` (M6) mới được route cloud.
import type { PresenceStatus } from "./runtime-node-registry.service";

export type RuntimeMode = "LOCAL_ONLY" | "REMOTE_ACCESS" | "CLOUD_CONTINUITY";
export type SyncFreshness = "FRESH" | "STALE" | "UNKNOWN";

export type RouteTarget =
  | "LOCAL_DIRECT" // UI trên cùng thiết bị với runtime (LOCAL_ONLY)
  | "LOCAL_RELAY" // qua secure relay tới local node (REMOTE_ACCESS / CLOUD_CONTINUITY khi local up)
  | "CLOUD_ISOLATED" // isolated cloud workspace runtime (CLOUD_CONTINUITY — M6)
  | "OFFLINE" // không có runtime khả dụng theo đúng mode
  | "DENIED"; // không phải thành viên workspace

export interface NodeRouteInput {
  presence: PresenceStatus;
  hasValidLease: boolean;
}

export interface RuntimeRouteInput {
  runtimeMode: RuntimeMode;
  membershipValid: boolean;
  localNode: NodeRouteInput | null;
  cloudNode?: NodeRouteInput | null;
  syncFreshness?: SyncFreshness;
}

export interface RouteDecision {
  target: RouteTarget;
  reason: string;
  degraded: boolean; // node reachable nhưng heartbeat chớm cũ / sync stale
  cloudConsidered: boolean; // đã cân nhắc cloud chưa (REMOTE_ACCESS luôn = false)
}

function localUsable(n: NodeRouteInput | null): { ok: boolean; degraded: boolean } {
  if (!n) return { ok: false, degraded: false };
  if (n.presence === "OFFLINE" || !n.hasValidLease) return { ok: false, degraded: false };
  return { ok: true, degraded: n.presence === "DEGRADED" };
}

export function resolveRuntimeRoute(input: RuntimeRouteInput): RouteDecision {
  if (!input.membershipValid) {
    return {
      target: "DENIED",
      reason: "caller không phải thành viên workspace",
      degraded: false,
      cloudConsidered: false,
    };
  }

  const local = localUsable(input.localNode);

  if (input.runtimeMode === "LOCAL_ONLY") {
    if (local.ok) {
      return {
        target: "LOCAL_DIRECT",
        reason: "LOCAL_ONLY — runtime chạy cùng thiết bị",
        degraded: local.degraded,
        cloudConsidered: false,
      };
    }
    return {
      target: "OFFLINE",
      reason: input.localNode ? "local runtime offline / thiếu lease" : "chưa có local runtime node",
      degraded: false,
      cloudConsidered: false,
    };
  }

  if (input.runtimeMode === "REMOTE_ACCESS") {
    if (local.ok) {
      return {
        target: "LOCAL_RELAY",
        reason: "REMOTE_ACCESS — route qua relay tới local node đang chạy",
        degraded: local.degraded,
        cloudConsidered: false, // guardrail 7: KHÔNG cloud-failover
      };
    }
    return {
      target: "OFFLINE",
      reason: input.localNode
        ? "local node offline — REMOTE_ACCESS KHÔNG failover cloud"
        : "chưa có local runtime node đăng ký",
      degraded: false,
      cloudConsidered: false,
    };
  }

  // CLOUD_CONTINUITY (M6) — ưu tiên local khi còn sống, nếu không thì cloud isolated.
  if (local.ok) {
    return {
      target: "LOCAL_RELAY",
      reason: "CLOUD_CONTINUITY — local node còn sống, ưu tiên local",
      degraded: local.degraded,
      cloudConsidered: true,
    };
  }
  const cloud = localUsable(input.cloudNode ?? null);
  if (cloud.ok) {
    const stale = input.syncFreshness === "STALE";
    return {
      target: "CLOUD_ISOLATED",
      reason: stale
        ? "CLOUD_CONTINUITY — chạy cloud, sync stale (view read-only tới khi reconcile)"
        : "CLOUD_CONTINUITY — local offline, chạy isolated cloud runtime",
      degraded: cloud.degraded || stale,
      cloudConsidered: true,
    };
  }
  return {
    target: "OFFLINE",
    reason: "cả local lẫn cloud runtime đều không khả dụng",
    degraded: false,
    cloudConsidered: true,
  };
}
