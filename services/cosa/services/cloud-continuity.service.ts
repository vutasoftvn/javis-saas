// M6 §4 — Cloud Continuity promotion/demotion advisor (decision core).
//
// Hàm QUYẾT ĐỊNH thuần: nhận trạng thái đã resolve (presence local/cloud, lease
// hết hạn chưa, failover policy, sync freshness) ⇒ khuyến nghị hành động. Việc
// thực thi (`promoteCloudRuntime`, `acquireWriteLease` để demote) do caller làm
// sau khi nhận `PROMOTE_CLOUD` / `DEMOTE_CLOUD`.
//
// Split-brain: enforcement thật nằm ở fencing token (`assertFencingTokenCurrent`
// trong workspace-execution-lease.service) — advisor này chỉ quyết định ai NÊN
// giữ lease kế tiếp.
import type { PresenceStatus } from "./runtime-node-registry.service";
import type { FailoverPolicy, SyncFreshness } from "./workspace-execution-lease.service";

export type ContinuityAction =
  | "HOLD_LOCAL" // local đang giữ lease & còn sống — không đổi
  | "HOLD_LOCAL_LEASE" // local offline nhưng lease còn hạn — chờ
  | "HOLD_STALE" // đủ điều kiện promote nhưng sync chưa FRESH — chờ sync
  | "MANUAL_REQUIRED" // failover_policy=MANUAL (finance/legal) — cần người quyết
  | "PROMOTE_CLOUD" // promote cloud runtime
  | "DEMOTE_CLOUD" // local quay lại — cloud nhường, local acquire epoch mới
  | "NO_RUNTIME"; // không có runtime nào khả dụng

export interface ContinuityInput {
  runtimeMode: "LOCAL_ONLY" | "REMOTE_ACCESS" | "CLOUD_CONTINUITY";
  localPresence: PresenceStatus | "MISSING";
  cloudNodeAvailable: boolean;
  leaseHeldBy: "local" | "cloud" | "none";
  leaseExpired: boolean;
  failoverPolicy: FailoverPolicy;
  syncFreshness: SyncFreshness;
}

export interface ContinuityDecision {
  action: ContinuityAction;
  reason: string;
}

export function resolveContinuityAction(i: ContinuityInput): ContinuityDecision {
  // Cloud Continuity chỉ áp dụng cho mode CLOUD_CONTINUITY. Các mode khác:
  // không bao giờ promote cloud (guardrail 7).
  if (i.runtimeMode !== "CLOUD_CONTINUITY") {
    if (i.localPresence === "ONLINE") {
      return { action: "HOLD_LOCAL", reason: `${i.runtimeMode} — chỉ chạy local` };
    }
    return {
      action: "NO_RUNTIME",
      reason: `${i.runtimeMode} — local không sẵn sàng, KHÔNG failover cloud`,
    };
  }

  // Local quay lại trong khi cloud đang giữ lease ⇒ demote cloud.
  if (i.localPresence === "ONLINE" && i.leaseHeldBy === "cloud") {
    return {
      action: "DEMOTE_CLOUD",
      reason: "local runtime online trở lại — cloud nhường, local acquire epoch mới",
    };
  }

  if (i.localPresence === "ONLINE") {
    return { action: "HOLD_LOCAL", reason: "local runtime đang sống — ưu tiên local" };
  }

  // local không online từ đây.
  if (!i.leaseExpired && i.leaseHeldBy === "local") {
    return {
      action: "HOLD_LOCAL_LEASE",
      reason: "local offline nhưng write lease còn hạn — chờ, chưa promote",
    };
  }

  // local offline + lease hết hạn (hoặc không ai giữ).
  if (i.failoverPolicy === "MANUAL") {
    return {
      action: "MANUAL_REQUIRED",
      reason: "failover_policy=MANUAL (finance/legal) — promote cloud phải do người quyết định",
    };
  }
  if (i.syncFreshness !== "FRESH") {
    return {
      action: "HOLD_STALE",
      reason: `sync freshness '${i.syncFreshness}' chưa đạt policy — không promote trên state cũ`,
    };
  }
  if (i.cloudNodeAvailable) {
    return {
      action: "PROMOTE_CLOUD",
      reason: "local lease hết hạn + sync FRESH + AUTO — promote cloud runtime",
    };
  }
  return { action: "NO_RUNTIME", reason: "local offline và không có cloud runtime khả dụng" };
}
