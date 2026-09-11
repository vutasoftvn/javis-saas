import { randomUUID } from "node:crypto";
import { APIError } from "encore.dev/api";

export const CURRENT_SCHEMA_VERSION = 1;
export const MAX_PAYLOAD_BYTES = 16 * 1024;

const PRODUCER_SERVICE = "company.operations";
const PRODUCER_VERSION = process.env.COMPANY_SERVICE_VERSION || "0.0.0-dev";

const EVENT_TYPE_RE = /^[a-z]+\.[a-z_]+\.[a-z_]+\.v[0-9]+$/;
const FORBIDDEN_PAYLOAD_KEYS = /(access_token|secret|password|api[_-]?key|authorization|private[_-]?key)/i;
const RESTRICTED_REFERENCE_KEY_RE = /^[a-z0-9_]*(id|ref|hash|count)$/i;

// Hub-visible event types that REQUIRE projectId (Founder Activity Feed)
const PROJECT_SCOPED_EVENT_TYPES = new Set([
  "operations.task.created.v1",
  "operations.task.completed.v1",
  "operations.work_package.created.v1",
  "operations.decision.recorded.v1",
  "operations.evidence.linked.v1",
  "operations.risk.raised.v1",
  "operations.risk.resolved.v1",
]);

export interface BusinessEventEnvelope<TPayload extends Record<string, any>> {
  eventId: string;
  eventType: string;
  schemaVersion: number;
  occurredAt: string;
  workspaceId: string;
  projectId?: string;
  aggregateType: string;
  aggregateId: string;
  correlationId: string;
  causationId?: string;
  actor: { kind: "user" | "agent" | "system"; id: string };
  producer: { service: string; version: string };
  classification: "internal" | "confidential" | "restricted";
  payload: TPayload;
}

export interface BusinessEventInput<T extends Record<string, any>> {
  eventType: string;
  workspaceId: string;
  projectId?: string;
  aggregateType: string;
  aggregateId: string;
  correlationId: string;
  causationId?: string;
  actor: BusinessEventEnvelope<T>["actor"];
  classification: BusinessEventEnvelope<T>["classification"];
  payload: T;
  // Cho phép producer khác domain (vd. company.commercial cho Customer Engagement).
  // Mặc định giữ nguyên company.operations để call site cũ không đổi hành vi.
  producer?: { service: string; version: string };
}

function assertNoForbiddenKeys(value: unknown, path = "payload"): void {
  if (value === null || typeof value !== "object") return;
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (FORBIDDEN_PAYLOAD_KEYS.test(k)) {
      throw APIError.invalidArgument(`forbidden credential-shaped key in ${path}.${k}`);
    }
    assertNoForbiddenKeys(v, `${path}.${k}`);
  }
}

export function validateEnvelope(
  e: unknown
): asserts e is BusinessEventEnvelope<Record<string, unknown>> {
  const env = e as Partial<BusinessEventEnvelope<Record<string, unknown>>>;
  const required = [
    "eventId", "eventType", "schemaVersion", "occurredAt", "workspaceId",
    "aggregateType", "aggregateId", "correlationId", "actor", "producer",
    "classification", "payload",
  ] as const;
  for (const field of required) {
    if (env[field] === undefined || env[field] === null) {
      throw APIError.invalidArgument(`business event missing field: ${field}`);
    }
  }
  if (!EVENT_TYPE_RE.test(env.eventType as string)) {
    throw APIError.invalidArgument(`eventType must match ${EVENT_TYPE_RE} (past tense, versioned)`);
  }
  if (typeof env.schemaVersion !== "number" || env.schemaVersion < 1) {
    throw APIError.invalidArgument("schemaVersion must be a positive integer");
  }
  if (Number.isNaN(new Date(env.occurredAt as string).getTime())) {
    throw APIError.invalidArgument("occurredAt must be an ISO-8601 timestamp");
  }

  // Project-scoped event types (Founder Activity Feed) REQUIRE projectId
  const eventType = env.eventType as string;
  if (PROJECT_SCOPED_EVENT_TYPES.has(eventType)) {
    if (!env.projectId || env.projectId === "") {
      throw APIError.invalidArgument(
        `event type ${eventType} requires projectId for Founder Activity Feed`
      );
    }
  }

  const payload = env.payload as Record<string, unknown>;
  if (Buffer.byteLength(JSON.stringify(payload), "utf8") > MAX_PAYLOAD_BYTES) {
    throw APIError.invalidArgument(`payload exceeds ${MAX_PAYLOAD_BYTES} bytes`);
  }
  assertNoForbiddenKeys(payload);

  // Validate payload projectId matches envelope projectId if both exist
  if (env.projectId && payload.project_id !== undefined && payload.project_id !== env.projectId) {
    throw APIError.invalidArgument(
      `payload project_id must match envelope projectId (payload: ${payload.project_id}, envelope: ${env.projectId})`
    );
  }

  if (env.classification === "restricted") {
    const offending = Object.keys(payload).filter((k) => !RESTRICTED_REFERENCE_KEY_RE.test(k));
    if (offending.length > 0) {
      throw APIError.invalidArgument(
        `restricted classification requires reference-only payload; offending keys: ${offending.join(", ")}`
      );
    }
  }
}

export function makeBusinessEvent<T extends Record<string, unknown>>(
  input: BusinessEventInput<T>
): BusinessEventEnvelope<T> {
  const envelope: BusinessEventEnvelope<T> = {
    eventId: randomUUID(),
    eventType: input.eventType,
    schemaVersion: CURRENT_SCHEMA_VERSION,
    occurredAt: new Date().toISOString(),
    workspaceId: input.workspaceId,
    ...(input.projectId ? { projectId: input.projectId } : {}),
    aggregateType: input.aggregateType,
    aggregateId: input.aggregateId,
    correlationId: input.correlationId,
    ...(input.causationId ? { causationId: input.causationId } : {}),
    actor: input.actor,
    producer: input.producer ?? { service: PRODUCER_SERVICE, version: PRODUCER_VERSION },
    classification: input.classification,
    payload: input.payload,
  };
  validateEnvelope(envelope);
  return envelope;
}
