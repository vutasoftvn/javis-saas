import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";

const { deliveryPolicies, deliveryAttempts, costLedger } = schema;

export interface CreateDeliveryPolicyParams {
  tenantId: bigint;
  channel: "flutter" | "email" | "slack" | "webhook";
  config?: Record<string, unknown>;
}

export async function createDeliveryPolicy(params: CreateDeliveryPolicyParams) {
  const id = generateSnowflake();
  await db.insert(deliveryPolicies).values({
    id,
    tenantId: params.tenantId,
    channel: params.channel,
    config: params.config ?? {},
  });
  return { id };
}

export interface RecordDeliveryAttemptParams {
  deliveryPolicyId: bigint;
  artifactRef: string;
  status: "pending" | "sent" | "failed";
  errorMessage?: string;
}

export async function recordDeliveryAttempt(params: RecordDeliveryAttemptParams) {
  const id = generateSnowflake();
  await db.insert(deliveryAttempts).values({
    id,
    deliveryPolicyId: params.deliveryPolicyId,
    artifactRef: params.artifactRef,
    status: params.status,
    errorMessage: params.errorMessage,
  });
  return { id };
}

export interface RecordCostParams {
  tenantId: bigint;
  missionId?: bigint;
  runId?: string;
  provider: string;
  model: string;
  inputTokens: bigint;
  outputTokens: bigint;
  costCents: bigint;
}

export async function recordCost(params: RecordCostParams) {
  const id = generateSnowflake();
  await db.insert(costLedger).values({
    id,
    tenantId: params.tenantId,
    missionId: params.missionId,
    runId: params.runId,
    provider: params.provider,
    model: params.model,
    inputTokens: params.inputTokens,
    outputTokens: params.outputTokens,
    costCents: params.costCents,
  });
  return { id };
}
