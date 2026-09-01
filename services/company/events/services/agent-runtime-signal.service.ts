import { APIError, Header } from "encore.dev/api";
import { db, schema } from "../../operations/models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { runtimeSourceSignals } = schema;

export interface AgentRuntimeSignalPayload {
  workspaceId: string;
  sourceKind: string;
  sourceId: string;
  sequence: number | string;
  state: string;
  observedAt: string;
  correlationId: string;
  payloadHash: string;
}

export interface IngestAgentRuntimeSignalRequest {
  signal: AgentRuntimeSignalPayload;
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
}

export async function ingestAgentRuntimeSignalService(
  req: IngestAgentRuntimeSignalRequest,
  expectedToken: string = process.env.COSA_WORKER_SERVICE_TOKEN ?? "dev-worker-service-token"
): Promise<{ stored: boolean }> {
  const token = req.serviceToken || (req.authorization ? req.authorization.replace(/^Bearer\s+/i, "") : "");
  if (!token || (expectedToken && token !== expectedToken)) {
    throw APIError.unauthenticated("Invalid or missing service authentication token");
  }

  const { signal } = req;
  if (!signal || !signal.workspaceId || !signal.sourceKind || !signal.sourceId || signal.sequence === undefined) {
    throw APIError.invalidArgument("Missing required fields in runtime signal payload");
  }

  const wsId = BigInt(signal.workspaceId);
  const sequence = BigInt(signal.sequence);
  const observedAt = new Date(signal.observedAt);
  const now = new Date();
  const id = generateSnowflake();

  await db
    .insert(runtimeSourceSignals)
    .values({
      id,
      workspaceId: wsId,
      sourceKind: signal.sourceKind,
      sourceId: signal.sourceId,
      sequence,
      state: signal.state,
      observedAt,
      correlationId: signal.correlationId || "",
      payloadHash: signal.payloadHash || "",
      receivedAt: now,
    })
    .onConflictDoNothing({
      target: [
        runtimeSourceSignals.workspaceId,
        runtimeSourceSignals.sourceKind,
        runtimeSourceSignals.sourceId,
        runtimeSourceSignals.sequence,
      ],
    });

  return { stored: true };
}
