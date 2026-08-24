import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { workers } = schema;

export interface RegisterWorkerParams {
  id: string;
  runtimeKind: string;
  endpoint?: string;
  capabilities?: string[];
  concurrencyLimit?: number;
  trustTier?: string;
}

export async function registerWorker(params: RegisterWorkerParams) {
  const now = new Date();
  await db
    .insert(workers)
    .values({
      id: params.id,
      runtimeKind: params.runtimeKind,
      endpoint: params.endpoint,
      capabilities: params.capabilities ?? [],
      concurrencyLimit: params.concurrencyLimit ?? 1,
      trustTier: params.trustTier ?? "T0",
      lastHeartbeatAt: now,
      status: "online",
    })
    .onConflictDoUpdate({
      target: workers.id,
      set: {
        runtimeKind: params.runtimeKind,
        endpoint: params.endpoint,
        capabilities: params.capabilities ?? [],
        concurrencyLimit: params.concurrencyLimit ?? 1,
        trustTier: params.trustTier ?? "T0",
        lastHeartbeatAt: now,
        status: "online",
      },
    });
}

export async function heartbeatWorker(id: string) {
  await db.update(workers).set({ lastHeartbeatAt: new Date(), status: "online" }).where(eq(workers.id, id));
}

export async function listWorkers() {
  return db.select().from(workers);
}
