import { api, Header } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../services/token.service";
import * as leaseSvc from "../services/control-plane-lease.service";
import * as schedulerSvc from "../services/control-plane-scheduler.service";
import * as missionSvc from "../services/control-plane-mission.service";
import * as workerSvc from "../services/control-plane-worker.service";
import * as watchSvc from "../services/control-plane-watch.service";
import * as deliverySvc from "../services/control-plane-delivery.service";

/**
 * Control Plane internal & worker RPC (ADR-CONTROLPLANE-001, P0.1 TEST_READINESS_ADJUSTMENT_PLAN_2026-08-26.md).
 * Toàn bộ `expose: true` qua Encore API Gateway nhưng được bảo vệ nghiêm ngặt bằng WorkerServiceTokenGuard
 * (`requireWorkerServiceAuth`), ngăn chặn client token thông thường hoặc anonymous truy cập trái phép.
 */

// --- Runtime leases (thay RunLeaseManager) ---

export interface AuthHeaderParam {
  authorization?: Header<"Authorization">;
}

export const acquireRuntimeLeaseEndpoint = api(
  { method: "POST", path: "/control-plane/internal/leases/acquire", expose: true },
  async (params: leaseSvc.AcquireLeaseParams & AuthHeaderParam): Promise<leaseSvc.LeaseResult> => {
    requireWorkerServiceAuth(params.authorization);
    return leaseSvc.acquireLease(params);
  }
);

export const renewRuntimeLeaseEndpoint = api(
  { method: "POST", path: "/control-plane/internal/leases/renew", expose: true },
  async (params: leaseSvc.RenewLeaseParams & AuthHeaderParam): Promise<{ success: boolean }> => {
    requireWorkerServiceAuth(params.authorization);
    const success = await leaseSvc.renewLease(params);
    return { success };
  }
);

export const releaseRuntimeLeaseEndpoint = api(
  { method: "POST", path: "/control-plane/internal/leases/release", expose: true },
  async (params: leaseSvc.ReleaseLeaseParams & AuthHeaderParam): Promise<{ success: boolean }> => {
    requireWorkerServiceAuth(params.authorization);
    const success = await leaseSvc.releaseLease(params);
    return { success };
  }
);

// --- Scheduled tasks (thay RunScheduler) ---

export const scheduleTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks", expose: true },
  async (params: schedulerSvc.ScheduleParams & AuthHeaderParam): Promise<schedulerSvc.ScheduledTaskRow> => {
    requireWorkerServiceAuth(params.authorization);
    return schedulerSvc.scheduleTask(params);
  }
);

export const pollDueScheduledTasksEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/poll", expose: true },
  async (params: schedulerSvc.ClaimParams & AuthHeaderParam): Promise<{ tasks: schedulerSvc.ScheduledTaskRow[] }> => {
    requireWorkerServiceAuth(params.authorization);
    const tasks = await schedulerSvc.pollDueTasks(params);
    return { tasks };
  }
);

export const heartbeatScheduledTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/:taskId/heartbeat", expose: true },
  async (params: schedulerSvc.HeartbeatTaskParams & AuthHeaderParam): Promise<{ ok: boolean }> => {
    requireWorkerServiceAuth(params.authorization);
    const ok = await schedulerSvc.heartbeatTask(params);
    return { ok };
  }
);

export const completeScheduledTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/:taskId/complete", expose: true },
  async (params: schedulerSvc.CompleteTaskParams & AuthHeaderParam): Promise<schedulerSvc.CompleteTaskResult> => {
    requireWorkerServiceAuth(params.authorization);
    return schedulerSvc.completeTask(params);
  }
);

/** Sweeper — gọi từ control-plane.cron.ts định kỳ, cũng expose để test/vận
 * hành thủ công có thể trigger ngay không cần đợi lịch cron. */
export const reclaimStuckScheduledTasksEndpoint = api(
  { method: "POST", path: "/control-plane/internal/scheduled-tasks/reclaim-stuck", expose: true },
  async (params: { limit?: number } & AuthHeaderParam): Promise<schedulerSvc.ReclaimResult> => {
    requireWorkerServiceAuth(params.authorization);
    return schedulerSvc.reclaimStuckTasks(params.limit);
  }
);

// --- Missions/Tasks/Assignments ---

export const createMissionEndpoint = api(
  { method: "POST", path: "/control-plane/internal/missions", expose: true },
  async (params: missionSvc.CreateMissionParams & AuthHeaderParam): Promise<{ id: string }> => {
    requireWorkerServiceAuth(params.authorization);
    const { id } = await missionSvc.createMission(params);
    return { id: id.toString() };
  }
);

export const getMissionEndpoint = api(
  { method: "GET", path: "/control-plane/internal/missions/:id", expose: true },
  async (params: { id: string } & AuthHeaderParam) => {
    requireWorkerServiceAuth(params.authorization);
    return missionSvc.getMission(BigInt(params.id));
  }
);

export const createTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/tasks", expose: true },
  async (params: missionSvc.CreateTaskParams & AuthHeaderParam): Promise<{ id: string }> => {
    requireWorkerServiceAuth(params.authorization);
    const { id } = await missionSvc.createTask(params);
    return { id: id.toString() };
  }
);

export const checkoutTaskEndpoint = api(
  { method: "POST", path: "/control-plane/internal/tasks/:taskId/checkout", expose: true },
  async (params: { taskId: string; workerId: string; leaseSec?: number } & AuthHeaderParam) => {
    requireWorkerServiceAuth(params.authorization);
    return missionSvc.checkoutTask({
      taskId: BigInt(params.taskId),
      workerId: params.workerId,
      leaseSec: params.leaseSec,
    });
  }
);

// --- Workers ---

export const registerWorkerEndpoint = api(
  { method: "POST", path: "/control-plane/internal/workers", expose: true },
  async (params: workerSvc.RegisterWorkerParams & AuthHeaderParam): Promise<{ ok: boolean }> => {
    requireWorkerServiceAuth(params.authorization);
    await workerSvc.registerWorker(params);
    return { ok: true };
  }
);

export const heartbeatWorkerEndpoint = api(
  { method: "POST", path: "/control-plane/internal/workers/:id/heartbeat", expose: true },
  async (params: { id: string } & AuthHeaderParam): Promise<{ ok: boolean }> => {
    requireWorkerServiceAuth(params.authorization);
    await workerSvc.heartbeatWorker(params.id);
    return { ok: true };
  }
);

// --- Watch/Signal ---

export const createWatchEndpoint = api(
  { method: "POST", path: "/control-plane/internal/watches", expose: true },
  async (params: watchSvc.CreateWatchParams & AuthHeaderParam): Promise<{ id: string }> => {
    requireWorkerServiceAuth(params.authorization);
    const { id } = await watchSvc.createWatch(params);
    return { id: id.toString() };
  }
);

export const recordSignalObservationEndpoint = api(
  { method: "POST", path: "/control-plane/internal/signals", expose: true },
  async (params: watchSvc.RecordSignalParams & AuthHeaderParam): Promise<watchSvc.RecordSignalResult> => {
    requireWorkerServiceAuth(params.authorization);
    return watchSvc.recordSignalObservation(params);
  }
);

// --- Delivery/Cost ---

export const createDeliveryPolicyEndpoint = api(
  { method: "POST", path: "/control-plane/internal/delivery-policies", expose: true },
  async (params: deliverySvc.CreateDeliveryPolicyParams & AuthHeaderParam): Promise<{ id: string }> => {
    requireWorkerServiceAuth(params.authorization);
    const { id } = await deliverySvc.createDeliveryPolicy(params);
    return { id: id.toString() };
  }
);

export const recordDeliveryAttemptEndpoint = api(
  { method: "POST", path: "/control-plane/internal/delivery-attempts", expose: true },
  async (params: deliverySvc.RecordDeliveryAttemptParams & AuthHeaderParam): Promise<{ id: string }> => {
    requireWorkerServiceAuth(params.authorization);
    const { id } = await deliverySvc.recordDeliveryAttempt(params);
    return { id: id.toString() };
  }
);

export const recordCostEndpoint = api(
  { method: "POST", path: "/control-plane/internal/cost-ledger", expose: true },
  async (params: deliverySvc.RecordCostParams & AuthHeaderParam): Promise<{ id: string }> => {
    requireWorkerServiceAuth(params.authorization);
    const { id } = await deliverySvc.recordCost(params);
    return { id: id.toString() };
  }
);
