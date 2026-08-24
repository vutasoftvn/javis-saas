import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";

const { watches, triggerPolicies, signalObservations } = schema;

export interface CreateWatchParams {
  tenantId: bigint;
  kind: string;
  config?: Record<string, unknown>;
}

export async function createWatch(params: CreateWatchParams) {
  const id = generateSnowflake();
  await db.insert(watches).values({
    id,
    tenantId: params.tenantId,
    kind: params.kind,
    config: params.config ?? {},
  });
  return { id };
}

export async function listActiveWatches(tenantId: bigint) {
  return db.select().from(watches).where(eq(watches.tenantId, tenantId));
}

export interface CreateTriggerPolicyParams {
  watchId: bigint;
  condition: Record<string, unknown>;
  targetAgentSpecId: string;
}

export async function createTriggerPolicy(params: CreateTriggerPolicyParams) {
  const id = generateSnowflake();
  await db.insert(triggerPolicies).values({
    id,
    watchId: params.watchId,
    condition: params.condition,
    targetAgentSpecId: params.targetAgentSpecId,
  });
  return { id };
}

export interface RecordSignalParams {
  watchId: bigint;
  dedupeKey: string;
  payload?: Record<string, unknown>;
}

export interface RecordSignalResult {
  isDuplicate: boolean;
  observationId?: bigint;
}

/**
 * Chống duplicate proactive Run cho cùng 1 signal (Blueprint V2 Scenario G) —
 * dựa vào unique index `idx_control_plane_signal_observations_dedupe`
 * (watch_id, dedupe_key). Duplicate INSERT bị DB chặn, coi là tín hiệu đã xử
 * lý, không phải lỗi.
 */
export async function recordSignalObservation(params: RecordSignalParams): Promise<RecordSignalResult> {
  const id = generateSnowflake();
  try {
    await db.insert(signalObservations).values({
      id,
      watchId: params.watchId,
      dedupeKey: params.dedupeKey,
      payload: params.payload ?? {},
    });
    return { isDuplicate: false, observationId: id };
  } catch (err) {
    return { isDuplicate: true };
  }
}

export async function markSignalTriggeredRun(observationId: bigint, runId: string) {
  await db.update(signalObservations).set({ triggeredRunId: runId }).where(eq(signalObservations.id, observationId));
}
