import { api, Header } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../services/token.service";
import * as workerSvc from "../services/control-plane-worker.service";

export interface WorkerIngressParams {
  workerId: string;
  workerType?: string;
  labels?: Record<string, string>;
  authorization?: Header<"Authorization">;
}

export interface WorkerIngressResponse {
  ok: boolean;
  workerId: string;
  authenticated: boolean;
}

/**
 * Worker-facing Ingress Service (P0.1, TEST_READINESS_ADJUSTMENT_PLAN_2026-08-26.md).
 * Expose: true qua Encore gateway nhưng được bảo vệ nghiêm ngặt bởi WorkerServiceTokenGuard.
 */
export const workerIngressEndpoint = api(
  { method: "POST", path: "/cosa/workers/ingress", expose: true },
  async (params: WorkerIngressParams): Promise<WorkerIngressResponse> => {
    const payload = requireWorkerServiceAuth(params.authorization, params.workerId);
    await workerSvc.registerWorker({
      id: params.workerId,
      runtimeKind: params.workerType || "openai_agents",
    });
    return {
      ok: true,
      workerId: params.workerId,
      authenticated: true,
    };
  }
);
