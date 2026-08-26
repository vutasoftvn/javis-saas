import { api } from "encore.dev/api";
import * as leaseSvc from "../services/control-plane-lease.service";
import * as schedulerSvc from "../services/control-plane-scheduler.service";
import * as missionSvc from "../services/control-plane-mission.service";
import * as workerSvc from "../services/control-plane-worker.service";
import * as watchSvc from "../services/control-plane-watch.service";
import * as deliverySvc from "../services/control-plane-delivery.service";

/**
 * Wave 7 — Control Plane internal RPC (ADR-CONTROLPLANE-001, ACCEPTED). Toàn
 * bộ `expose: false` — chỉ `packages/agent_core`/`apps/cosa` (Python, qua HTTP
 * internal service-to-service, Wave 7 H.3) mới gọi các endpoint này.
 *
 * Trạng thái consumer (2026-08-25, COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_
 * PLAN_2026-08-25.md §29.6 Phase 4/6):
 * - leases (`acquireRuntimeLeaseEndpoint`/`renewRuntimeLeaseEndpoint`/
 *   `releaseRuntimeLeaseEndpoint`) + scheduled-tasks
 *   (`scheduleTaskEndpoint`/`pollDueScheduledTasksEndpoint`/
 *   `heartbeatScheduledTaskEndpoint`/`completeScheduledTaskEndpoint`/
 *   `reclaimStuckScheduledTasksEndpoint`, xem control-plane.cron.ts cho
 *   sweeper định kỳ — Phase 3 Durable Queue Recovery): CÓ consumer production
 *   thật lần đầu —
 *   `apps/cosa/worker/main.py` qua `HttpControlPlaneLeaseClient`/
 *   `HttpControlPlaneSchedulerClient`, wired làm default trong
 *   `build_cosa_agent_plane()`.
 * - missions/tasks/workers/watches/delivery: VẪN chưa có consumer production
 *   nào — hạ tầng đón đầu.
 * CHƯA runtime-verify bất kỳ endpoint nào bằng Encore CLI/Postgres thật (chỉ
 * `tsc --noEmit` sạch) — môi trường viết code phiên này không có Docker/
 * Encore CLI.
 *
 * Đặt tên export ở đây khác tên hàm service tương ứng (hậu tố `Endpoint`) —
 * tránh trùng symbol khi `api.ts` gộp `export * from "./handlers"` và
 * `export * from "./services"` (đúng convention `getTenantPolicy` (handler) vs
 * `getTenantPolicyForTool` (service) đã dùng ở agent-policy.handler.ts).
 */

// --- Runtime leases (thay RunLeaseManager) ---

export const acquireRuntimeLeaseEndpoint = api(
  { method: "POST", path: "/control-plane/internal/leases/acquire", expose: false },
  async (params: leaseSvc.AcquireLeaseParams): Promise<leaseSvc.LeaseResult> => {
    return leaseSvc.acquireLease(params);
  }
);

export const renewRuntimeLeaseEndpoint = api(
  { method: "POST", path: "/control-plane/internal/leases/renew", expose: false },
  async (params: leaseSvc.RenewLeaseParams): Promise<{ success: boolean }> => {
    const success = await leaseSvc.renewLease(params);
    return { success };
  }
);

export const releaseRuntimeLeaseEndpoint = api(
  { method: "POST", path: "/control-plane/internal/leases/release", expose: false },
  async (params: leaseSvc.ReleaseLeaseParams): Promise<{ success: boolean }> => {
    const success = await leaseSvc.releaseLease(params);
    return { success };
  }
);

// --- Scheduled tasks (thay RunScheduler) ---

export const scheduleTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks", expose: false },
  async (params: schedulerSvc.ScheduleParams): Promise<schedulerSvc.ScheduledTaskRow> => {
    return schedulerSvc.scheduleTask(params);
  }
);

export const pollDueScheduledTasksEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/poll", expose: false },
  async (params: schedulerSvc.ClaimParams): Promise<{ tasks: schedulerSvc.ScheduledTaskRow[] }> => {
    const tasks = await schedulerSvc.pollDueTasks(params);
    return { tasks };
  }
);

export const heartbeatScheduledTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/:taskId/heartbeat", expose: false },
  async (params: schedulerSvc.HeartbeatTaskParams): Promise<{ ok: boolean }> => {
    const ok = await schedulerSvc.heartbeatTask(params);
    return { ok };
  }
);

export const completeScheduledTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/:taskId/complete", expose: false },
  async (params: schedulerSvc.CompleteTaskParams): Promise<schedulerSvc.CompleteTaskResult> => {
    return schedulerSvc.completeTask(params);
  }
);

/** Sweeper — gọi từ control-plane.cron.ts định kỳ, cũng expose để test/vận
 * hành thủ công có thể trigger ngay không cần đợi lịch cron. */
export const reclaimStuckScheduledTasksEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/reclaim-stuck", expose: false },
  async (params: { limit?: number }): Promise<schedulerSvc.ReclaimResult> => {
    return schedulerSvc.reclaimStuckTasks(params.limit);
  }
);

// --- Missions/Tasks/Assignments ---

export const createMissionEndpoint = api(
  { method: "POST", path: "/control-plane/internal/missions", expose: false },
  async (params: missionSvc.CreateMissionParams): Promise<{ id: string }> => {
    const { id } = await missionSvc.createMission(params);
    return { id: id.toString() };
  }
);

export const getMissionEndpoint = api(
  { method: "GET", path: "/control-plane/internal/missions/:id", expose: false },
  async (params: { id: string }) => {
    return missionSvc.getMission(BigInt(params.id));
  }
);

export const createTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/tasks", expose: false },
  async (params: missionSvc.CreateTaskParams): Promise<{ id: string }> => {
    const { id } = await missionSvc.createTask(params);
    return { id: id.toString() };
  }
);

export const checkoutTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/tasks/:taskId/checkout", expose: false },
  async (params: { taskId: string; workerId: string; leaseSec?: number }) => {
    return missionSvc.checkoutTask({
      taskId: BigInt(params.taskId),
      workerId: params.workerId,
      leaseSec: params.leaseSec,
    });
  }
);

// --- Workers ---

export const registerWorkerEndpoint = api(
  { method: "POST", path: "/control-plane/internal/workers", expose: false },
  async (params: workerSvc.RegisterWorkerParams): Promise<{ ok: boolean }> => {
    await workerSvc.registerWorker(params);
    return { ok: true };
  }
);

export const heartbeatWorkerEndpoint = api(
  { method: "POST", path: "/control-plane/internal/workers/:id/heartbeat", expose: false },
  async (params: { id: string }): Promise<{ ok: boolean }> => {
    await workerSvc.heartbeatWorker(params.id);
    return { ok: true };
  }
);

// --- Watch/Signal ---

export const createWatchEndpoint = api(
  { method: "POST", path: "/control-plane/internal/watches", expose: false },
  async (params: watchSvc.CreateWatchParams): Promise<{ id: string }> => {
    const { id } = await watchSvc.createWatch(params);
    return { id: id.toString() };
  }
);

export const recordSignalObservationEndpoint = api(
  { method: "POST", path: "/control-plane/internal/signals", expose: false },
  async (params: watchSvc.RecordSignalParams): Promise<watchSvc.RecordSignalResult> => {
    return watchSvc.recordSignalObservation(params);
  }
);

// --- Delivery/Cost ---

export const createDeliveryPolicyEndpoint = api(
  { method: "POST", path: "/control-plane/internal/delivery-policies", expose: false },
  async (params: deliverySvc.CreateDeliveryPolicyParams): Promise<{ id: string }> => {
    const { id } = await deliverySvc.createDeliveryPolicy(params);
    return { id: id.toString() };
  }
);

export const recordDeliveryAttemptEndpoint = api(
  { method: "POST", path: "/control-plane/internal/delivery-attempts", expose: false },
  async (params: deliverySvc.RecordDeliveryAttemptParams): Promise<{ id: string }> => {
    const { id } = await deliverySvc.recordDeliveryAttempt(params);
    return { id: id.toString() };
  }
);

export const recordCostEndpoint = api(
  { method: "POST", path: "/control-plane/internal/cost-ledger", expose: false },
  async (params: deliverySvc.RecordCostParams): Promise<{ id: string }> => {
    const { id } = await deliverySvc.recordCost(params);
    return { id: id.toString() };
  }
);
